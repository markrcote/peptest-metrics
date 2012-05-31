# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging
import os
import pytz
import re
import tempfile
import traceback
import urllib
import urllib2

import logparser

MAX_DOWNLOAD_ATTEMPTS = 3

def find_logs(start_time, end_time):
    if not start_time.tzinfo:
        start_time = start_time.replace(tzinfo=pytz.timezone('US/Pacific'))
    if not end_time.tzinfo:
        end_time = end_time.replace(tzinfo=pytz.timezone('US/Pacific'))
    peptest_log_regex = re.compile("([^_]+)_([^_]+)_test-peptest")
    ftpdirs = []

    for branch in ('mozilla-central', 'mozilla-inbound'):
        for platform in ('linux', 'linux64', 'macosx', 'macosx64', 'win32',
                         'win64'):
            ftpdirs.append('ftp://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/%s-%s/' % (branch, platform))

    for d in ftpdirs:
        logging.info('Searching %s...' % d)
        try:
            f = urllib2.urlopen(d)
        except urllib2.URLError:
            print 'Bad directory.'
            continue
        for line in f:
            build_time = None
            srcdir = line.split()[8].strip()
            try:
                build_time = datetime.datetime.fromtimestamp(int(srcdir), pytz.timezone('US/Pacific'))
            except ValueError:
                continue

            if build_time and (build_time < start_time or
                               build_time > end_time):
                continue

            newurl = d + srcdir
            logging.info('Checking build dir %s...' % newurl)
            f2 = urllib.urlopen(newurl)
            for l2 in f2:
                filename = l2.split(' ')[-1].strip()
                if peptest_log_regex.match(filename):
                    fileurl = newurl + "/" + filename
                    yield fileurl


def from_iso_date_or_datetime(s):
    datefmt = '%Y-%m-%d'
    datetimefmt = datefmt + 'T%H:%M:%S'
    try:
        d = datetime.datetime.strptime(s, datetimefmt)
    except ValueError:
        d = datetime.datetime.strptime(s, datefmt)
    return d


def main(args, opts):
    logs_dir = tempfile.mkdtemp()
    lp = logparser.LogParser(opts.db_name, opts.db_user, opts.db_passwd)

    m = re.match('(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', args[0])
    if re.match('\d{14}', args[0]):
        # build id
        build_time = datetime.datetime.strptime(args[0], '%Y%m%d%H%M%S')
        start_time = build_time
        end_time = build_time
    else:
        start_time = from_iso_date_or_datetime(args[0])
        if len(args) > 1:
            end_time = from_iso_date_or_datetime(args[1])
        else:
            end_time = datetime.datetime.now()
    logging.info('Looking for logs...')
    for url in find_logs(start_time, end_time):
        logging.info('found peptest log: %s' % url)
        logging.debug('downloading...')
        filename = os.path.basename(url)
        log_path = os.path.join(logs_dir, os.path.basename(url))
        attempts = 0
        while attempts < MAX_DOWNLOAD_ATTEMPTS:
            if attempts > 0:
                logging.info('Retrying download')
            try:
                urllib.urlretrieve(url, log_path)
            except IOError:
                logging.error('Couldn\'t download file: %s' % traceback.format_exc())
            else:
                break
            attempts += 1
        if attempts == MAX_DOWNLOAD_ATTEMPTS:
            logging.error('Couldn\'t download file after %d attempts.' %
                          attempts)
            continue
        logging.debug('parsing...')
        lp.parse_log(log_path, clobber=True)
        logging.debug('cleaning up...')
        os.unlink(log_path)
    os.rmdir(logs_dir)
    return 0

            
if __name__ == '__main__':
    import errno
    import sys
    from optparse import OptionParser

    usage = '''%prog [options] <datetime, date/datetime, or date/datetime range>
Analyze peptest logs.

The argument(s) should be one of the following:
- a build ID, e.g. 20120403063158
- a date/datetime, e.g. 2012-04-03 or 2012-04-03T06:31:58
- a date/datetime range, e.g. 2012-04-03T06:31:58 2012-04-05

If a build ID is given, the log for that, and only that, particular build is
analyzed.

If a single date or datetime is given, the logs for all builds with build IDs
between the given date/datetime and now are analyzed.

If a date/datetime range is given, test runs are initiated for all builds
with build IDs in the given range.'''
    parser = OptionParser(usage=usage)
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
    if len(args) > 2:
        parser.print_help()
        sys.exit(errno.EINVAL)
    sys.exit(main(args, opts))
