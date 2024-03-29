# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import gzip
import json
import logging
import os
import re
import time
import MySQLdb
from collections import defaultdict

class LogParser(object):

    def __init__(self, db_name, db_user, db_passwd):
        self.db = MySQLdb.connect(user=db_user, passwd=db_passwd, db=db_name)

    def timestamp_from_buildid(self, buildid):
        return int(time.mktime(datetime.datetime.strptime(buildid, '%Y%m%d%H%M%S').timetuple()))

    def cache_ids(self, branch, platform, test):
        c = self.db.cursor()
        if branch and branch not in self.branches:
            c.execute('insert into branch (name) values (%s)', [branch])
            self.branches[branch] = c.lastrowid
        if platform and platform not in self.platforms:
            c.execute('insert into platform (name) values (%s)', [platform])
            self.platforms[platform] = c.lastrowid
        if test and test not in self.tests:
            c.execute('insert into test (name) values (%s)', [test])
            self.tests[test] = c.lastrowid

    def add_results(self, branch, platform, test, buildid, revision, periods):
        self.cache_ids(branch, platform, test)
        c = self.db.cursor()

        # HACK: Saw a buildid with seconds of 61; check and adjust for this
        # FIXME: Figure out why this is... the timestamp (1338338641) 
        # corresponded to the "normalized" time (2012-05-29 17:44:01), but
        # the build id was 20120529174361.
        # For now we are only normalizing the seconds and minutes...
        m = re.match('(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', buildid)
        parts = [int(x) for x in m.groups()]
        for x in range(5, 3, -1):
            while parts[x] > 59:
                parts[x-1] += 1
                parts[x] -= 60
        builddate = datetime.datetime(*parts)

        for p in periods:
            c.execute('insert into result (branch_id, platform_id, test_id, builddate, revision, run, unresponsive_period, action) values (%s, %s, %s, %s, %s, %s, %s, %s)',
                      (self.branches[branch],
                       self.platforms[platform],
                       self.tests[test],
                       builddate,
                       revision,
                       p['run'],
                       p['period'],
                       p.get('action', '')))
        self.db.commit()

    def build_cache(self):
        c = self.db.cursor()
        self.tests = {}
        self.platforms = {}
        self.branches = {}
        for table, d in (('test', self.tests),
                         ('platform', self.platforms),
                         ('branch', self.branches)):
            c.execute('select id, name from %s' % table)
            for id, name in c.fetchall():
                d[name] = id

    def parse_log(self, filename, buildid='', revision='', clobber=False):
        logging.debug('parsing %s' % filename)
        periods = {}
        runs = defaultdict(int)
        self.build_cache()
        m = re.match('([^_]+)_(.+)_test', os.path.basename(filename))
        branch = m.group(1)
        platform = m.group(2)
        f = gzip.GzipFile(filename, 'r')
        for line in f:
            if not buildid:
                m = re.match('buildid: ([\d]+)', line)
                if m:
                    buildid = m.group(1)
                    logging.debug('build id %s on %s, os %s' %
                                  (buildid, branch, platform))
            if not revision:
                m = re.match('revision: ([\w]+)', line)
                if m:
                    revision = m.group(1)
                    logging.debug('revision %s on %s, os %s' %
                                  (revision, branch, platform))
                    if clobber:
                        self.cache_ids(branch, platform, None)
                        c = self.db.cursor()
                        c.execute('delete from result where branch_id=%s and platform_id=%s and revision=%s',
                                  (self.branches[branch],
                                   self.platforms[platform],
                                   revision))
            if not 'PEP ' in line:
                continue
            parts = [x.strip() for x in line.split('|')]
            test = parts[1]
            if 'PEP TEST-START' in line:
                if test in periods:
                    logging.error('Did not receive PEP TEST-END for test %s, run %d.' % (test, runs[test]))
                runs[test] += 1
                periods[test] = []
            elif 'PEP TEST-END' in line:
                if not test in periods:
                    logging.error('Got PEP TEST-END but no PEP TEST-START '
                                  'for test %s.' % test)
                elif not periods[test]:
                    logging.error('No results for test %s.' % test)
                    del periods[test]
                else:
                    self.add_results(branch, platform, test, buildid, revision,
                                     periods[test])
                    del periods[test]
            elif 'PEP TEST-PASS' in line:
                if not len(periods[test]):
                    periods[test].append({'period': 0, 'run': runs[test]})
            elif 'PEP WARNING' in line:
                if len(parts) < 4:
                    continue
                m = re.match('unresponsive time: (\d+) ms', parts[3])
                if m:
                    periods[test].append({'period': int(m.group(1)),
                                          'run': runs[test],
                                          'action': parts[2]})


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logs_dir = 'logs'
    lp = LogParser('peptest', 'peptest', 'peptest')
    for f in os.listdir(logs_dir):
        filename = os.path.join(logs_dir, f) 
        lp.parse_log(filename, clobber=True)
