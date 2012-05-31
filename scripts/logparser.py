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

    def add_result(self, branch, platform, test, buildid, revision, is_pass,
                   metric=0):
        self.cache_ids(branch, platform, test)
        c = self.db.cursor()
        c.execute('insert into result (branch_id, platform_id, test_id, builddate, revision, pass, metric) values (%s, %s, %s, %s, %s, %s, %s)',
                  (self.branches[branch],
                   self.platforms[platform],
                   self.tests[test],
                   datetime.datetime.strptime(buildid, '%Y%m%d%H%M%S'),
                   revision,
                   int(is_pass),
                   metric))
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
                        
            if 'PEP TEST-UNEXPECTED-FAIL' in line:
                parts = [x.strip() for x in line.split('|')]
                test = parts[1]
                m = re.search('metric: ([\d\.]*)', parts[2])
                if m:
                    metric = float(m.group(1))
                    self.add_result(branch, platform, test, buildid, revision,
                                    False, metric)
                    logging.debug('failure in test %s: %0.1f' % (test, metric))
                else:
                    logging.error('Bad failure message: %s' % line)
            elif 'PEP TEST-PASS' in line:
                parts = [x.strip() for x in line.split('|')]
                test = parts[1]
                self.add_result(branch, platform, test, buildid, revision, True)
                logging.debug('pass in test %s' % test)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logs_dir = 'logs'
    lp = LogParser('peptest', 'peptest', 'peptest')
    for f in os.listdir(logs_dir):
        filename = os.path.join(logs_dir, f) 
        lp.parse_log(filename)
