/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

function loadOptions(data) {
  var i;
  for (option in data) {
    $('#controls select[name=' + option + ']').html('');
    data[option].sort();
    for (i = 0; i < data[option].length; i++) {
      $('#controls select[name=' + option + ']').append(
        ich.controlopt({ value: data[option][i], text: data[option][i] }));
    }
  }
}

function onlineVariance(times) {
  if (times === undefined) {
    return {};
  }
  var mean = 0.0;
  var M2 = 0.0;
  var delta, variance;

  for (var i = 0; i < times.length; i++) {
    delta = times[i][1] - mean;
    mean = mean + delta/(i+1);
    if (i > 0) {
      M2 = M2 + delta*(times[i][1] - mean);
    }

    variance = M2/(i+1);
  }
  return { mean: mean, stddev: Math.sqrt(variance) };
}

function getDataPoints(data) {
  // set end date ahead one day so that we get all results from the given
  // day (since no time implies midnight, the very beginning of the day).
  var points = data.map(function(x) {
    x.builddate = new Date(x.builddate).getTime();
    return x;
  });
  var revisions = {};
  data.forEach(function(x) {
    revisions[x.builddate] = x.revision;
  });
  points.sort(function(a, b) { return a.builddate - b.builddate; });
  var firstPoint = points.length ? points[0].date : null;
  var lastPoint = points.length ? points[points.length-1].date : null;
  var failurePoints = points.filter(function(x) { return !x.pass; })
                            .map(function(x) { return [x.builddate, x.metric]; });
  var passPoints = points.filter(function(x) { return x.pass; })
                         .map(function(x) { return [x.builddate, 0]; });
  return { failures: failurePoints,
           passes: passPoints,
           firstPoint: firstPoint,
           lastPoint: lastPoint,
           revisions: revisions };
}

function makePlot(params, data) {
  $('#plot').html();
  var points = getDataPoints(data);
  if (!points.failures.length && !points.passes.length) {
    $('#plot').html(ich.nodata());
    return;
  }
  
  var colour = 0;
  var failSeriesIndex = null, passSeriesIndex = null;
  var series = [];
  if (points.failures.length) {
    series.push({ data: points.failures,
                  label: 'failures',
                  color: colour,
                  points: { show: true } });
    failSeriesIndex = series.length - 1;
  }
  colour++;
  if (points.passes.length) {
    series.push({ data: points.passes,
                  label: 'passes',
                  color: colour,
                  points: { show: true } });
    passSeriesIndex = series.length - 1;
  }
  colour++;
  if (points.failures.length > 1) {
    var windowLength = parseInt($('#meanwindow').attr('value'));
    var mean = [], stddev_pos = [], stddev_neg = [], window = [], faildata;
    if (!windowLength) {
      faildata = onlineVariance(points.failures);
      mean = [[points.failures[0][0], faildata.mean],
              [points.failures[points.failures.length-1][0], faildata.mean]];
      stddev_pos = [[points.failures[0][0], faildata.mean + faildata.stddev],
                    [points.failures[points.failures.length-1][0],
                     faildata.mean + faildata.stddev]];
      stddev_neg = [[points.failures[0][0], faildata.mean - faildata.stddev],
                    [points.failures[points.failures.length-1][0],
                     faildata.mean - faildata.stddev]];
    } else {
      for (var i = 0; i < points.failures.length; i++) {
        window.push(points.failures[i]);
        if (window[window.length-1][0] - points.failures[0][0] <
            1000*60*60*24*windowLength) {
          continue;
        }
        while (window[window.length-1][0] - window[0][0] >
               1000*60*60*24*windowLength) {
          window.shift();
        }
        faildata = onlineVariance(window);
        mean.push([window[window.length-1][0], faildata.mean]);
        stddev_pos.push([window[window.length-1][0],
                         faildata.mean + faildata.stddev]);
        stddev_neg.push([window[window.length-1][0],
                         faildata.mean - faildata.stddev]);
      }
    }
    series.push({ data: mean,
                  label: 'mean failure',
                  color: colour,
                  points: { show: false },
                  lines: { show: true },
                  hoverable: false });
    series.push({ data: stddev_pos,
                  label: 'failure std dev',
                  color: ++colour,
                  points: { show: false },
                  lines: { show: true },
                  hoverable: false });
    series.push({ data: stddev_neg,
                  color: colour,
                  points: { show: false },
                  lines: { show: true },
                  hoverable: false });
  }
  var yaxisLabel = 'sum of squares of unresponsive times in ms / 1000';
  $.plot($('#plot'), series, {
    grid: { hoverable: true },
    xaxis: { mode: 'time', axisLabel: 'build date' },
    yaxis: { min: 0,  axisLabel: yaxisLabel },
    legend: { position: 'ne' }
  });

  $('#plot').bind('plothover',
    plotHover($('#plot'), function (item) {
      var y;
      if (item.seriesIndex === failSeriesIndex) {
        y = item.datapoint[1];
      } else if (item.seriesIndex === passSeriesIndex) {
        y = 'pass';
      }
      showLineTooltip(item.pageX,
                      item.pageY,
                      item.datapoint[0],
                      params.branch,
                      points.revisions[item.datapoint[0]],
                      y);
    })
  );
}

function loadGraph() {
  var params = {};
  $.makeArray($('#controls select').each(function(i, e) { params[e.name] = e.value; }));
  var hash = '#/' + params.branch + '/' + params.platform + '/' + params.test +
        '/' + $('#startdate').attr('value') + '/' + $('#enddate').attr('value');
  if (hash != document.location.hash) {
    document.location.hash = hash;
  }
  $.getJSON('api/results/?branch=' + params.branch + '&platform=' + params.platform + '&test=' + params.test + '&start=' + $('#startdate').attr('value') + '&end=' + $('#enddate').attr('value'), function(data) {
    makePlot(params, data);
  });
}

function setControls(branch, platform, test, startdate, enddate) {
  if (branch) {
    $('#branch option[value="' + branch + '"]').attr('selected', true);
  }
  if (platform) {
    $('#platform option[value="' + platform + '"]').attr('selected', true);
  }
  if (test) {
    $('#test option[value="' + test + '"]').attr('selected', true);
  }
  if (!startdate) {
    $('#period option[value="7"]').attr('selected', true);
    periodChanged();
  } else {
    $('#startdate').attr('value', startdate);
    if (enddate) {
      $('#enddate').attr('value', enddate);
    } else {
      $('#enddate').attr('value', ISODateString(new Date()));
    }
    dateChanged();
  }
  loadGraph();
}

function ISODateString(d) {
  function pad(n) { return n < 10 ? '0' + n : n; }
  return d.getUTCFullYear() + '-'
         + pad(d.getUTCMonth() + 1) + '-'
         + pad(d.getUTCDate());
}

function periodChanged() {
  var endDate = new Date();
  $('#enddate').attr('value', ISODateString(endDate));
  var startDate = new Date(endDate);
  startDate.setDate(startDate.getDate() - parseInt($('#period').attr('value')));
  $('#startdate').attr('value', ISODateString(startDate));
}

function dateChanged() {
  $('#period option[value="0"]').attr('selected', true);
  if (ISODateString(new Date()) == $('#enddate').attr('value')) {
    var period = $('#period option[value="' + (new Date($('#enddate').attr('value')) - new Date($('#startdate').attr('value')))/(24*60*60*1000) + '"]');
    if (period.length) {
      period.attr('selected', true);
    }
  }
}

function main() {
  // Configure date controls.
  $.datepicker.setDefaults({
    showOn: "button",
    buttonImage: "images/calendar.png",
    buttonImageOnly: true,
    dateFormat: 'yy-mm-dd'
  });
  $('#startdate').datepicker();
  $('#enddate').datepicker();

  $('#period').change(function() { periodChanged(); loadGraph(); return false; });

  $('#startdate').change(function() { dateChanged(); loadGraph(); return false; });
  $('#enddate').change(function() { dateChanged(); loadGraph(); return false; });

  $('#meanwindow').change(function() { loadGraph(); return false; });

  $.getJSON('api/info/', function(data) {
    loadOptions(data);
    $('#controls').change(function() { loadGraph(); return false; });
    $('#controls').submit(function() { return false; });
    // FIXME: is there a better way to set up routes with generic arguments?
    var router = Router({
      '/([^/]*)': {
        '/([^/]*)': {
          '/([^/]*)': {
            '/([^/]*)': {
              '/([^/]*)': {
                on: setControls
              },
              on: setControls
            },
            on: setControls
          },
          on: setControls
        },
        on: setControls
      },
      on: setControls
    }).init('/');
    setControls();
  });
}
