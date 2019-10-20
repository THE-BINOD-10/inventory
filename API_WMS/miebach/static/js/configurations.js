$(document).ready(function(){
$("#batch-conf-switch").bootstrapSwitch();
$("#fifo-conf-switch").bootstrapSwitch();
$("#loc-serial-mapping-switch").bootstrapSwitch();
$("#message-switch").bootstrapSwitch();
$("#show-image-switch").bootstrapSwitch();
$("#show-sync-switch").bootstrapSwitch();
$("#use-imei-switch").bootstrapSwitch();
$("#show-backorder-switch").bootstrapSwitch();
$("#pallet-switch").bootstrapSwitch();
$("#production-switch").bootstrapSwitch();
$("#pos-switch").bootstrapSwitch();
$("#conf-table td").css({'padding':'20px'})
$("body").find(".bootstrap-switch").addClass("bootstrap-switch-mini")
$("body").find(".bootstrap-switch-handle-off").removeClass("bootstrap-switch-default").addClass("bootstrap-switch-warning")
$("body").find(".bootstrap-switch-handle-on").removeClass("bootstrap-switch-primary").addClass("bootstrap-switch-success")

$(".bootstrap-switch .bootstrap-switch-handle-off").css({"color":"#fff","background":"grey"});

$("#batch-conf-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true"
        }
    else{
        state = "false"
    }
    $.ajax({url: '/switches?batch_switch=' + state,
        'success': function(response) {
      if(state == true) {
          $("#batch-conf-switch").attr("checked", true);
      }
      else {
          $("#batch-conf-switch").attr("checked", false);
      }
    }});
  });

 $("#fifo-conf-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true"
        }
    else{
        state = "false"
    }
    $.ajax({url: '/switches?fifo_switch=' + state,
        'success': function(response) {
      if(state == true) {
          $("#fifo-conf-switch").attr("checked", true);
      }
      else {
          $("#fifo-conf-switch").attr("checked", false);
      }
    }});
  });

  $("#loc-serial-mapping-switch").on('switchChange.bootstrapSwitch', function(event, state) {
     var state = state;
     if(state == true) {
         state = "true"
         }
     else{
         state = "false"
     }
     $.ajax({url: '/switches?fifo_switch=' + state,
         'success': function(response) {
       if(state == true) {
           $("#loc-serial-mapping-switch").attr("checked", true);
       }
       else {
           $("#loc-serial-mapping-switch").attr("checked", false);
       }
     }});
   });

 $("#show-sync-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true"
        }
    else{
        state = "false"
    }
    $.ajax({url: '/switches?sync_switch=' + state,
        'success': function(response) {
      if(state == true) {
          $("#show-sync-switch").attr("checked", true);
      }
      else {
          $("#show-sync-switch").attr("checked", false);
      }
    }});
  });

 $("#show-backorder-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true"
        }
    else{
        state = "false"
    }
    $.ajax({url: '/switches?back_order=' + state,
        'success': function(response) {
      if(state == true) {
          $("#show-backorder-switch").attr("checked", true);
      }
      else {
          $("#show-backorder-switch").attr("checked", false);
      }
    }});
  });

 $("#show-image-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true"
        }
    else{
        state = "false"
    }
    $.ajax({url: '/switches?show_image=' + state,
        'success': function(response) {
      if(state == true) {
          $("#show-image-switch").attr("checked", true);
      }
      else {
          $("#show-image-switch").attr("checked", false);
      }
    }});
  });

  $('.online-input').on('input', function(event) {
     $('.save-percentage').removeClass('display-none');
  });

  $('.save-percentage').on('click', function() {
    var value = $('.online-input').val();
    if (!value ) {
        value = "0";
    }
    $.ajax({url: '/switches?online_percentage=' + value,
        'success': function(response) {
        var online_percentage = $('.online-percentage').find('strong').text();
        $('.online-percentage').find('strong').text(online_percentage.replace(/\( (.*?) \)/g, '( ' + value + '% )'));
      }
    });
  });

  $('.alerts-input').on('input', function(event) {
     $('.save-mail-alerts').removeClass('display-none');
  });

  $('.save-mail-alerts').on('click', function() {
    var value = $('.alerts-input').val();
    if (!value ) {
        value = "0";
    }
    $.ajax({url: '/switches?mail_alerts=' + value,
        'success': function(response) {
      }
    });
  });

 $("#use-imei-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true"
        }
    else{
        state = "false"
    }
    $.ajax({url: '/switches?use_imei=' + state,
        'success': function(response) {
      if(state == true) {
          $("#use-imei-switch").attr("checked", true);
      }
      else {
          $("#use-imei-switch").attr("checked", false);
      }
    }});
  });

  $('.invoice-prefix').on('input', function(event) {
     $('.save-prefix').removeClass('display-none');
  });

  $('.save-prefix').on('click', function() {
    var value = $('.invoice-prefix').val();
    if (!value ) {
        value = "0";
    }
    $.ajax({url: '/switches?invoice_prefix=' + value,
        'success': function(response) {
        var po_prefix = $('.po-prefix').find('strong').text();
        $('.invoice-prefix').find('strong').text(po_prefix.replace(/\( (.*?) \)/g, '( ' + value + ' )'));
      }
    });
  });

 $("#pallet-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true"
        }
    else{
        state = "false"
    }
    $.ajax({url: '/switches?pallet_switch=' + state,
        'success': function(response) {
      if(state == true) {
          $("#pallet-switch").attr("checked", true);
      }
      else {
          $("#pallet-switch").attr("checked", false);
      }
    }});
  });

 $("#production-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true";
         $("ul.links-section").find("div:contains('Production')").parent().parent().attr("style", "display: block;");
         $(".production").addClass("display-none");
        }
    else{
        state = "false";
         $("ul.links-section").find("div:contains('Production')").parent().parent().attr("style", "display: none;");
         $(".production").addClass("display-none");
         $(".production").attr("style", "display: none");
    }
    $.ajax({url: '/switches?production_switch=' + state,
        'success': function(response) {
      if(state == true) {
          $("#production-switch").attr("checked", true);
      }
      else {
          $("#production-switch").attr("checked", false);
      }
    }});
  });

 $("#pos-switch").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    if(state == true) {
        state = "true";
         $("ul.links-section").find("div:contains('POS')").parent().parent().attr("style", "display: block;");
         $(".pos").addClass("display-none");
        }
    else{
        state = "false";
         $("ul.links-section").find("div:contains('POS')").parent().parent().attr("style", "display: none;");
         $(".pos").addClass("display-none");
         $(".pos").attr("style", "display: none");
    }
    $.ajax({url: '/switches?pos_switch=' + state,
        'success': function(response) {
      if(state == true) {
          $("#pos-switch").attr("checked", true);
      }
      else {
          $("#pos-switch").attr("checked", false);
      }
    }});
  });


  $('#mail_alerts').on('click', function() {
    var value = $('#mail_alerts').val();
    if (!value ) {
        value = "0";
    }
    $.ajax({url: '/switches?mail_alerts=' + value,
        'success': function(response) {
        var po_prefix = $('#mail_alerts').find('strong').text();
        $('#mail_alerts').find('strong').text(po_prefix.replace(/\( (.*?) \)/g, '( ' + value + ' )'));
      }
    });
  });

  $('#mail-now').on('click', function() {
    var value = $('.alerts-input').val();
    if (!value ) {
        value = "0";
    }
    $.ajax({url: '/send_mail_reports/',
        'success': function(response) {
              $('.top-right').notify({
                message: { text: "Mail Sent Successfully" },
                type: 'success',
                fadeOut: { enabled: true, delay: 6000 },
              }).show();
      }
    });
  });

  $('#group_input').prev().find("input").on('input', function(event) {
     $('.save-group').removeClass('display-none');
  });

  $('#group_input').on('itemRemoved', function(event) {
    $('.save-group').removeClass('display-none');
  });

  $('.save-group').on('click', function() {
    var value = $('#group_input').tagsinput('items');
    $.ajax({url: '/save_groups?sku_groups=' + value,
        'success': function(response) {
              $('.top-right').notify({
                message: { text: "Updated Successfully" },
                type: 'success',
                fadeOut: { enabled: true, delay: 6000 },
              }).show();

      }
    });
  });

});
