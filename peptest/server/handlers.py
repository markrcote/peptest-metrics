import ConfigParser
import datetime
import templeton.handlers
import web
from collections import defaultdict

class DefaultConfigParser(ConfigParser.ConfigParser):

    def get_default(self, section, option, default, func='get'):
        try:
            return getattr(cfg, func)(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

DEFAULT_CONF_FILE = 'peptest_server.conf'
cfg = DefaultConfigParser()

cfg.read(DEFAULT_CONF_FILE)
DB_HOST = cfg.get_default('peptest', 'db_host', 'localhost')
DB_NAME = cfg.get_default('peptest', 'db_name', 'peptest')
DB_USER = cfg.get_default('peptest', 'db_user', 'peptest')
DB_PASSWD = cfg.get_default('peptest', 'db_passwd', 'peptest')

db = web.database(dbn='mysql', host=DB_HOST, db=DB_NAME, user=DB_USER,
                  pw=DB_PASSWD)

urls = (
    '/results/', 'Results',
    '/info/', 'Info'
)

class Results(object):

    @templeton.handlers.json_response
    def GET(self):
        args, body = templeton.handlers.get_request_parms()
        vars = {}
        wheres = []
        for arg_name in ('test', 'platform', 'branch'):
            arg_wheres = []
            for i, arg_val in enumerate(args.get(arg_name, [])):
                vars['%s%d' % (arg_name, i)] = arg_val
                arg_wheres.append('%s.name=$%s%d' % (arg_name, arg_name, i))
            if arg_wheres:
                wheres.append('(%s)' % ' or '.join(arg_wheres))
        if 'start' in args:
            wheres.append('builddate >= $start')
            vars['start'] = args['start'][0]
        if 'end' in args:
            wheres.append('builddate < $end')
            # add one to the end date so we capture the full end day
            # e.g. if the user gives an end day of 2012-01-01, we want
            # everything on that day, so really we want everything before
            # 2012-01-02.
            vars['end'] = datetime.datetime.strptime(args['end'][0], '%Y-%m-%d').date() + datetime.timedelta(days=1)

        query = 'select builddate, revision, run, unresponsive_period, test.name as test_name, platform.name as platform_name, branch.name as branch_name from result inner join test on result.test_id = test.id inner join branch on result.branch_id = branch.id inner join platform on result.platform_id = platform.id'
        if wheres:
            query += ' where %s' % ' and '.join(wheres)
        results = db.query(query, vars=vars)

        by_revision = defaultdict(dict)

        # average results for each revision
        # all results are for just one test/platform/branch, so we can keep
        # this simple

        # d['abcdef'][1]['periods'] = [230, 66, 43]
        # d['abcdef'][1]['metric'] = 59.105

        periods = defaultdict(lambda: defaultdict(list))
        metrics = defaultdict(lambda: defaultdict(int))
        revisions = {}

        for r in results:
            if not r['revision'] in revisions:
                revisions[r['revision']] = { 
                    'builddate': r['builddate'].isoformat(),
                    'revision': r['revision'],
                    'test': r['test_name'],
                    'platform': r['platform_name'],
                    'branch': r['branch_name'] }
            periods[r['revision']][r['run']].append(r['unresponsive_period'])

        for revision, runs in periods.iteritems():
            for run, period_times in runs.iteritems():
                metrics[revision][run] = sum([x*x / 1000.0 for x in period_times])

        response = []
        for results in revisions.values():
            # copy first element to preserve all the other metadata
            d = results.copy()
            d['metric'] = float(sum([x for x in metrics[results['revision']].values()])) / len(metrics[results['revision']].keys())
            response.append(d)
        return response


class Info(object):

    @templeton.handlers.json_response
    def GET(self):
        response = {}
        for table in ('test', 'platform', 'branch'):
            response[table] = [x['name'] for x in db.select(table)]
        return response
