/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

function dateStr(d) {
  function pad(n) { return n < 10 ? '0' + n : n; }  
  return d.getUTCFullYear() +
    '-' + pad(d.getUTCMonth() + 1) +
    '-' + pad(d.getUTCDate()) +
    ' ' + pad(d.getUTCHours()) +
    ':' + pad(d.getUTCMinutes()) +
    ':' + pad(d.getUTCSeconds());
}


function showLineTooltip(x, y, timestamp, branch, revision, value) {
  var params = {
    date: dateStr(new Date(timestamp)),
    value: value
  };
  var content;
  if (revision) {
    params.revision = revision;
    if (branch == 'mozilla-inbound') {
      params.url = 'https://hg.mozilla.org/integration/mozilla-inbound/rev/';
    } else if (branch == 'mozilla-central') {
      params.url = 'https://hg.mozilla.org/mozilla-central/rev/';
    } else if (branch == 'try') {
      params.url = 'https://hg.mozilla.org/try/rev/';
    }
    params.url += revision;
    content = ich.flot_tooltip(params);
  } else {
    content = ich.flot_tooltip_norev(params);
  }
  $(content).css({
    top: y + 5,
    left: x + 5
  }).appendTo('body');
}


// calls toolTipFn when we detect that the current selection has changed
function plotHover(selector, toolTipFn) {
  return function(event, pos, item) {
    var previousPoint = null;
    var prevX = 0;
    var prevY = 0;
    selector.bind('plothover', function (event, pos, item) {
      if (item) {
        if (previousPoint != item.datapoint) {
          previousPoint = item.datapoint;
          prevX = pos.pageX;
          prevY = pos.pageY;
          $('.tooltip').remove();
          toolTipFn(item);
        }
      } else {
        if (previousPoint) {
          if (pos.pageX < (prevX - 5) || pos.pageX > (prevX + 10 + $('.tooltip').width()) ||
              pos.pageY < (prevY - 5) || pos.pageY > (prevY + 10 + $('.tooltip').height())) {
            $('.tooltip').remove();
            previousPoint = null;
          }
        }
      }
    });
  };
}
