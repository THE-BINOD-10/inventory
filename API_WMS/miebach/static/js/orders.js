$(document).ready(function() {
  $("[name='fifo-switch']").bootstrapSwitch();
  $("[name='fifo-switch']").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    $.ajax({url: '/switches?fifo_switch=' + state,
        'success': function(response) {
      if(state == true) {
          $("[name='fifo-switch']").attr("checked", true);
      }
      else {
          $("[name='fifo-switch']").attr("checked", false);
      }
    }});
  });

  $("[name='batch-process']").bootstrapSwitch();

  $("[name='send-message']").bootstrapSwitch();
  $("[name='send-message']").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    $.ajax({url: '/switches?send_message=' + state,
        'success': function(response) {
      if(state == true) {
          $("[name='send-message']").attr("checked", true);
      }
      else {
          $("[name='send-message']").attr("checked", false);
      }
    }});
  });



});
