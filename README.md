peptest-metrics is a companion to the [peptest](https://github.com/mozilla/peptest)
responsiveness test framework. peptest-metrics provides a results collector
script and a [templeton](https://github.com/markrcote/templeton)-based web app
for displaying the results.

To collect results, simply run scripts/collector.py. You'll need the
pulsebuildmonitor installed ("pip install pulsebuildmonitor"). By default, it
will use the 'peptest' MySQL database on localhost with user 'peptest' and
password 'peptest'. Use the peptest.sql script to create your db.

To display results, run server.py in the peptest/server/ directory for a
development server, or use the templeton app to serve it through nginx.
