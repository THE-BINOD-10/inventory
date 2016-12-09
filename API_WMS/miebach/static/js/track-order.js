$(document).ready(function() {

  $(window).scroll(function scrollHandler(e) {
      e.stopImmediatePropagation();
      active_div = $(".panel.container").find(".active");
      temp = active_div.find(".order_index:last").attr("id").split(":")
      data = temp[0] + "=" + temp[1];
      data += "&search=true"
        if($(window).scrollTop() + $(window).height() > $(document).height() - 100) {
            $('body').find("#img-load").removeClass("display-none");
            $(window).off("scroll", scrollHandler);
            $.ajax({url: '/track_orders/',
                   'async': true,
                   'method': 'GET',
                   'data': data,
                   'success': function(response) {
                     active_div.append(response);
                     active_div.find(".stage").each(function(ind,obj){
                       $(obj).css("height", $(obj).parent().parent().height() + "px");
                       $(obj).KKTimeline(JSON.parse($(obj).attr('id')));
                     });

                     $('body').find("#img-load").addClass("display-none");
                     $(window).scroll(scrollHandler);
            }});
        }
  });

 
$(window).load(function () {
  $("#orders").find(".stage").each(function(ind,obj){
    $(obj).css("height", $(obj).parent().parent().height() + "px");
    $(obj).KKTimeline(JSON.parse($(obj).attr('id')));
  });
  $("#purchase-orders").find(".stage").each(function(ind,obj){
    $("#purchase-orders").addClass("active");
    $(obj).css("height", $(obj).parent().parent().height() + "px");
    $("#purchase-orders").removeClass("active");
    $(obj).KKTimeline(JSON.parse($(obj).attr('id')));
  });

});

$(window).load(function (e) {
  e.preventDefault();
  tab_url = window.location['href']
  tab_url1 = tab_url.split('/#')[1]
  $('a[href="#' + tab_url1 + '"]').tab('show');
  if(tab_url.search('po_order_id') > 0)
  {
    $('a[href="#purchase-orders"]').tab('show');
  }

});


});
