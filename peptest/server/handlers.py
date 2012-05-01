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

        query = 'select builddate, revision, pass, metric, test.name as test_name, platform.name as platform_name, branch.name as branch_name from result inner join test on result.test_id = test.id inner join branch on result.branch_id = branch.id inner join platform on result.platform_id = platform.id'
        if wheres:
            query += ' where %s' % ' and '.join(wheres)
        results = db.query(query, vars=vars)
        
        # average results for each revision
        # all results are for just one test/platform/branch, so we can keep
        # this simple
        by_revision = defaultdict(list)
        for r in results:
            d = {}
            for k, v in r.iteritems():
                if isinstance(v, datetime.datetime):
                    d[k] = v.isoformat()
                else:
                    d[k] = v
            by_revision[d['revision']].append(d)

        response = []
        for results in by_revision.values():
            # copy first element to preserve all the other metadata
            d = results[0].copy()
            d['metric'] = float(sum([x['metric'] for x in results])) / len(results)
            d['pass'] = all([x['pass'] for x in results])
            response.append(d)
        return response


class Info(object):

    @templeton.handlers.json_response
    def GET(self):
        response = {}
        for table in ('test', 'platform', 'branch'):
            response[table] = [x['name'] for x in db.select(table)]
        return response
