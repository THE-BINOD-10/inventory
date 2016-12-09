
(function( $ ) {
  $.fn.KKTimeline = function(data) {
    timeline = "<div class='prod-timline' style='height: 100%'><table style='height: 100%;max-height:400px;'>";
    for(dat in data) {
      stage = '<tr class="' + data[dat] + '" style="vertical-align:top;"><td><div class="line"></div><div class="round"><span class="glyphicon glyphicon-ok" aria-hidden="true"></span><span class="glyphicon glyphicon-refresh" aria-hidden="true"></span></div><div style="margin-top: 10px;">' + dat + '</div></td></tr>';
      timeline += stage;
    }
    timeline += "</table></div>"
    $(this).html(timeline);
    $(this).find("tr:last .line").hide()
  }
}( jQuery ));
