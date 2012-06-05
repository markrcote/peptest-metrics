# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import gzip
import json
import logging
import os
import re
import threading
import urllib

from collections import defaultdict

import logparser
from pulsebuildmonitor import start_pulse_monitor


class Collector(object):

    def __init__(self, db_name, db_user, db_passwd):
        self.db_name = db_name
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.logs_dir = 'logs'
        self.l = threading.RLock()
        try:
            os.mkdir(self.logs_dir)
        except OSError:
            pass

    def cb(self, data):
        self.l.acquire()
        buildid = data['buildid']
        buildos = data['os']
        test = data['test']
        branch = data['tree']
        logging.debug('test completed: %s on build %s, branch %s, os %s' %
                      (test, buildid, branch, buildos))
        if test == 'peptest':
            url = data['logurl']
            logging.info('found peptest log: %s' % url)
            logging.debug('downloading...')
            filename = os.path.basename(url)
            log_path = os.path.join(self.logs_dir, os.path.basename(url))
            urllib.urlretrieve(url, log_path)
            logging.debug('parsing...')
            # had a problem with the MySQL connection going away, so create
            # a new log parser each time, which creates a new connection.
            lp = logparser.LogParser(self.db_name, self.db_user, self.db_passwd)
            lp.parse_log(log_path, buildid, data['revision'])
            logging.debug('cleaning up...')
            os.unlink(log_path)
        self.l.release()


def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='count', dest='verbosity',
                      default=0,
                      help='verbosity level; can be given multiple times')
    parser.add_option('--db-name', type='string', dest='db_name',
                      default='peptest',
                      help='database name (default: "peptest")')
    parser.add_option('--db-user', type='string', dest='db_user',
                      default='peptest',
                      help='database user (default: "peptest")')
    parser.add_option('--db-passwd', type='string', dest='db_passwd',
                      default='peptest',
                      help='database password (default: "peptest")')
    opts, args = parser.parse_args()
    if opts.verbosity == 0:
        loglvl = logging.INFO
    else:
        loglvl = logging.DEBUG
    logging.basicConfig(level=loglvl)
    
    logging.info('Starting collector.')
    collector = Collector(opts.db_name, opts.db_user, opts.db_passwd)
    m = start_pulse_monitor(testCallback=collector.cb,
                            trees=['try', 'mozilla-central', 'mozilla-inbound'],
                            logger=logging.getLogger(), buildtypes=['opt'])
    while True:
        try:
            i = raw_input()
        except KeyboardInterrupt:
            break
        

if __name__ == '__main__':
    main()
