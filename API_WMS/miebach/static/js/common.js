$(document).ready(function() {


  $('.links-section').perfectScrollbar();

  $("li").on("click", function() {
    $(this).next("ul").toggle()
  });

  $("ul ul li").on("click", function() {
    $(this).next("ul").css("display", "block")
  });


$("body").on("keypress",".numvalid",function (e) {
     if (e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57)) {
        $(".insert-status").html("Type Numbers Only").show().fadeOut(2000);
        return false;
        }
   });

$("body").on("keyup","[name=price]",function()
    {
       this.value = this.value.replace(/[^\d\.]/g, "").replace(/\./, "x").replace(/\./g, "").replace(/x/, ".");
    });

//To validate Email Id on blur
  $("[name=email_id]").on("blur",function() {
    var email = $(this).val();
    var reg = /^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
    if (reg.test(email)){
      $(".insert-status").html("<p style='color:green;'>Valid Email Address</p>").show().fadeOut(3000); }
    else {
      $(".insert-status").html("Entered email is incorrect").show();
 }
});

  $("body").on("blur","[name=phone_number]",function(){
    if(($(this).val()).length != 10)
  {
    $(".insert-status").html("Phone number must be 10 digits").show();
  }
    else {
       phoneno = '/^[7-9][0-9]{9}$/'
       if($(this).val().match(phoneno))
       {
           $(".insert-status").html("Phone number must starts with 7,8 or 9 digit").show();
       }
       else {
           $(".insert-status").html(""); 
       }
    }

  });

$("body").on("keyup",".anvalid",function()
             {
var $th = $(this);
    $th.val( $th.val().replace(/[^a-zA-Z0-9_-]/g, function(str) {
    $(".insert-status").html("Please use only letters and numbers.").show().fadeOut(2000);
     return '';
    } )
);
             });

$("body").on("keyup","[name=wms_code]:not([readonly])",function()
             {
var $th = $(this);
    $th.val( $th.val().replace(/[^a-zA-Z0-9 _-]/g, function(str) {
     return '';
    } )
);
             });


//To remove highlights for every inputbox
   $('input[type="text"]').keyup(function (event) {
        var $currentField = $(this);
        if ($currentField.val() !== '')
        {
            $currentField.parent("div").removeClass("has-error");
        }

    });

//To remove highlights for every inputbox
    $('body').on('keydown','input[type="text"],textarea',function(){

    $(this).keyup(function (event) {
        var $currentField = $(this);
        if ($currentField.val() !== '')
        {
            $currentField.parent("div").removeClass("has-error");
        }
    });
    });


//To remove highlights for every Select Option
    $('body').on('change','select:not([name=category],[name=marketplace])',function (event) {
        if($(this).closest('form').attr('id') == 'order-shipment'){
            return
        }
        var $currentField = $(this);
        if ($currentField.val() !== '')
        {
            $currentField.parent("div").removeClass("has-error");
        }
        else
        {
            $currentField.parent("div").addClass("has-error");
        }
    });

  $("#menu-toggle").click(function(e) {
    e.preventDefault();
    $("#wrapper").toggleClass("toggled");
    $(".content").toggleClass("toggle-full");
  });


  $( "#raise_issue" ).submit(function( e ) {
    $('.loading').removeClass('display-none');
    e.preventDefault();
    var values = $(this).serialize();
    var this_data = $(this);
    $.ajax({url: '/insert_issue?' + values,
            'success': function(response) {
        if (response == "New Issue Added Successfully") {
        $('.top-right').notify({
          message: { text: response },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $('.top-right').notify({
          message: { text: response },
          type: 'danger',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
     $('.loading').addClass('display-none');
            }});
});


  $("body").on("submit",  "#update_issue" , function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    $.ajax({url: '/update_issues?' + values,
            'success': function(response) {
      this_data.find(".insert-status").html(response).show();
      $('.loading').addClass('display-none');
      $("#open-issues").dataTable().fnReloadAjax();
      $("#resolved").dataTable().fnReloadAjax();
            }});

    e.preventDefault();
  });


  $('body').on("click", '#open_issue .results', function() {
    var data_id = $(this).data('id');
    var context = this;
    $("#modal-confirmation").empty();
    $.ajax({url: '/edit_issue?data_id=' + data_id,
            'success': function(response) {
                $("#modal-confirmation").append(response);
            }});
    $("#modal-confirmation").modal();
  });

  $('body').on("click", '#resolved .results', function() {
    var data_id = $(this).data('id');
    var context = this;
    $("#modal-confirmation").empty();
    $.ajax({url: '/display_resolved?data_id=' + data_id,
            'success': function(response) {
                $("#modal-confirmation").append(response);
            }});
    $("#modal-confirmation").modal();
  });


  $("body").on("click", ".logout", function(e){

  $("body").append("<iframe id='log-frame' name='logout' class='display-none'></iframe>");
  $("body").append("<form id='connect-logout' target='logout' method='POST' action='https://connect.sellerworx.com/auth/logout'></form>")
  $("#connect-logout").submit();
    window.location = ("/logout");
  });

  $(window).load(function () {
    $(".process-toggle").attr("style","");
  });

  $.fn.make_disable = function(form_name) {
    form_name.find("input,select, textarea").attr('readonly', 'readonly');
    form_name.find("button:not(:contains('Close'), .close)").prop('disabled', true);
    if(!(form_name.hasClass("make_disable"))){
      form_name.addClass("make_disable");
    }
  };

  $("body").on("click", ".close, [data-dismiss='modal']", function(){
    var form_name = $(this).closest("form")
    if(form_name.hasClass("make_disable"))
    {
      form_name.find("input,select, textarea").removeAttr('readonly');
      form_name.find("button:not(:contains('Close'), .close)").prop('disabled', false);
    }
  });

});
