$(document).ready(function() {
  $('.switch_view').lc_switch();
  $('.switch_view').lcs_off();
  $('switch_view_order').lc_switch();
  $("body").find(".process-toggle").attr("style","");
  $(window).scroll(function scrollHandler(e) {
      e.stopImmediatePropagation();
      if(!$("div.append-data1").hasClass("display-none"))
      {
        index = $(".grid-sku").find("[name=index]").val();
        last_index = $(".grid-sku").find("[name=last_index]").val();

        if(Number(last_index) < Number(index.split(':')[1]))
        {
            index = index.split(':')[0] + ':' + last_index;
        }

        if(($(window).scrollTop() + $(window).height() > $(document).height() - 100) && !($(".grid-sku").hasClass("display-none")) && (Number(last_index) >= Number(index.split(':')[1]))) {
            $('body').find("#img-load").removeClass("display-none");
            $(window).off("scroll", scrollHandler);
            search = $(".grid-sku").find("[name=search-name]").val();
            category = $("[name=category]").find(":selected").val();
            data = 'index=' + index + '&search=' + search + "&category=" + category
            $(".grid-sku").find("[name=index]").remove();
            $.ajax({url: '/get_sku_grid/',
                   'method': 'POST',
                   'data': data,
                   'success': function(response) {
                     $('body').find(".append-data1").append(response);
                     $('body').find(".append-data").addClass("display-none");
                     $('body').find("#img-load").addClass("display-none");
                     $(window).scroll(scrollHandler);
            }});
        }
      }
  });

  $.fn.get_sku_grid = function(category) {
    index = $(".grid-sku").find("[name=index]").val();
    last = $(".grid-sku").find("[name=last_index]").val();
    $('body').find("#img-load").removeClass("display-none");

    search = $(".grid-sku").find("[name=search-name]").val();
    if(!category)
    {
      category = $("[name=category]").find(":selected").val();
    }
    data = 'index= 0:20' + '&search=' + search + "&category=" + category
    if(selected_images.length > 0){
      data = data + "&sku_codes=" + selected_images.join();
    }
    $.ajax({url: '/get_sku_grid/',
                 'method': 'POST',
                 'data': data,
                 'success': function(response) {
                 $(".grid-sku").find("[name=index], [name=last_index]").remove();
                 $('body').find("#img-load").addClass("display-none");
                 $('body').find(".append-data1").html(response);
                 $('body').find(".append-data").addClass("display-none");
                 if(selected_images.length > 0){
                   for(i=0;i<selected_images.length;i++){
                   var span_tag = $("span.dis_sku:contains('" + selected_images[i] + "')");
                   span_tag.parent().find("img:last").addClass("img-selected");
                   span_tag.parent().find("img:last").before('<img style="position:absolute; margin-top:58px;width:49px;margin-left: 60px" src="/static/img/img-tick.png" class="img-tick">');
                 } }
    }});
  }

  $.fn.get_category = function() {
    $('body').find("#img-load").removeClass("display-none");
    search = $(".grid-sku").find("[name=search-name]").val();
    data = 'search=' + search + "&category=" + $("[name=category]").find(":selected").val()
    $.ajax({url: '/get_category_view/',
                 'method': 'POST',
                 'data': data,
                 'success': function(response) {
                 $('body').find("#img-load").addClass("display-none");
                 $('body').find(".append-data").html(response);
                 $('.liquid').liquidcarousel({height:300, duration: 600,});
    }});
}

  $('body').on("keyup", "[name=search-name]", function(e){
    e.preventDefault();
    if($("div").hasClass('liquid'))
    {
     $.fn.get_category(); 
    }
    else{
    $.fn.get_sku_grid();
    }
  });

  $("body").on("change", "[name=category]", function(e){
    e.preventDefault();
    if($("div").hasClass('liquid'))
    {
     $.fn.get_category();
    }
    else{
    $.fn.get_sku_grid();
    }
  });

  toggle_count = 0
  $('body').delegate('.switch_view', 'lcs-on', function() {
      if(toggle_count == 0)
      {
          $.fn.get_category();
          toggle_count += 1
      }
      $(".sku-list-view").addClass("display-none");
      $(".grid-sku").removeClass("display-none");
      $('.liquid').liquidcarousel({height:300, duration: 600,});
  });


  $('body').delegate('.switch_view', 'lcs-off', function() {
    $(".sku-list-view").removeClass("display-none");
    $(".grid-sku").addClass("display-none");
    $("#sortingTable").resize();
  });

  $("body").on("click", ".view-cat", function(e){
    var cat = $(this).attr("id");
    $.fn.get_sku_grid(cat);
    $(".back-cat").removeClass("display-none");
    $('body').find(".append-data1").removeClass("display-none");
    $("body").find("[name=category]").val(cat);
  });

  $("#sku-master").on("click", ".back-cat", function(e){
    $('body').find(".append-data").removeClass("display-none");
    $('body').find(".append-data1").empty();
    $('body').find(".append-data1").addClass("display-none");
    $(".back-cat").addClass("display-none");
    $('.liquid').liquidcarousel({height:300, duration: 600,});
  });

  $('body').delegate('.switch_view_order', 'lcs-on', function() {
    $.fn.get_sku_grid();
    $("#order-create").addClass("display-none");
    $(".grid-sku").removeClass("display-none");
    
});

  $('body').delegate('.switch_view_order', 'lcs-off', function() {
    $("#order-create").removeClass("display-none");
    $(".grid-sku").addClass("display-none");
  });

  $('#create-orders').parent().find("#myTab").on( 'shown.bs.tab', 'a[data-toggle="tab"]', function (e) {
    if($(this).attr('href').search('create-st-order') > 0)
    {
      $(".grid-sku").addClass("display-none");
    }
    else if($("input.switch_view_order").is(":checked") == true)
    {
      $(".grid-sku").removeClass("display-none");
    }
  });

  selected_images = []
  $("#create-orders .append-data1").on("click", "img", function(e){
    var sku_code = $(this).parent().find('span.dis_sku').text();
    if($(this).parent().find("img").length < 2 ) {
      selected_images.push(sku_code)
      $(this).addClass("img-selected");
      $(this).before('<img style="position:absolute; margin-top:58px;width:49px;margin-left: 60px" src="/static/img/img-tick.png" class="img-tick">');
    }
    else{
      selected_images.pop(sku_code);
      $(this).removeClass("img-selected");
      $(this).parent().find('.img-tick').remove();
    }
    if($(".img-selected").length > 0){
      $(".place-order").removeClass("display-none");
    }
    else {
      $(".place-order").addClass("display-none");
    }

  });

});
