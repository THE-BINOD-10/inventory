$(document).ready(function() {

  $("body").on("change", "#update_sku #image-upload, #add_sku #image-upload", function(e){

    var fname = $(this).val();
    var re = /(\.jpg|\.jpeg|\.bmp|\.gif|\.png)$/i;
    if(!re.exec(fname))
    {
        alert("File extension not supported!");
        $(this).val('');
    }

  });

    $('.logo').load(function(){
   var timezone = jstz.determine();
   var tz = timezone.name()
   $.ajax({url: '/set_timezone?tz=' + tz,
            'success': function(response) {
    }});

    });

  $( "#add_supplier" ).submit(function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    var data = {};
    var data_row = $("#sortingTable").dataTable();
    var headers = $("#sortingTable").find("th");
    supp_id = $(this).find("input[name=id]").val();
    supp_name= $(this).find("input[name=name]").val();
    supp_addr = $(this).find("textarea[name=address]").val();
    supp_pho = $(this).find("input[name=phone_number]").val();
    supp_email = $(this).find("input[name=email_id]").val();
    supp_status = $(this).find("select[name=status]").val();
    if ( supp_id !="" && supp_name != "" && supp_addr !="" && supp_pho !="" && supp_email !="") {
    $('.loading').removeClass('display-none');
    var reg = /^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
    if (reg.test(supp_email)){
    $.ajax({url: '/insert_supplier?' + values,
            'success': function(response) {
         $.fn.make_disable($("#add_supplier"));
         this_data.find(".insert-status").html(response).show();
         data_row.DataTable().row.add({'Supplier ID': supp_id,
                        'Name': supp_name,
                        'Address': supp_addr,
                        'Phone Number': supp_pho,
                        'Email': supp_email,
                        'Status': supp_status,
                         }).draw();
         $('.loading').addClass('display-none');
    }});

 }
 else{
        $(".insert-status").html("Invalid email").show().fadeOut(3000);
    $('.loading').addClass('display-none');
 }
   }
   else {
    this_data.find(".insert-status").html("Missing Required fields").show();
}
    $('.loading').addClass('display-none');
    event.preventDefault();
  });

  $( "#add_customer_sku" ).submit(function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    var data = {};
    var data_row = $("#sortingTable").dataTable();
    var headers = $("#sortingTable").find("th");
    cust_id = $(this).find("input[name=id]").val();
    cust_name= $(this).find("input[name=name]").val();
    cust_sku = $(this).find("textarea[name=sku]").val();
    cust_price = $(this).find("input[name=price]").val();
    if ( cust_id !="" && cust_name != "" && cust_sku !="" && cust_price !="") {
        $.ajax({url: '/insert_customer_sku?' + values,
            'success': function(response) {
          $.fn.make_disable($("#add_customer_sku"));
          this_data.find(".insert-status").html(response).show();
          $("#sortingTable").dataTable().fnReloadAjax();
          $('.loading').addClass('display-none');
        }});
    } else {
      this_data.find(".insert-status").html("Missing Required fields").show();
    }
    $('.loading').addClass('display-none');
    event.preventDefault();
  });


  $("#add_zone,#add_supplier").submit(function(){

    $('input[type="text"], textarea[name="address"]').each(function (indx) {
    var $currentField = $(this);
    if ($currentField.val() === '')
    {
    $currentField.parent('div').addClass('has-error');
    }
    else
    {
    $currentField.parent('div').removeClass('has-error');
    }
    });
});

  $( "#add_sku" ).submit(function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serializeArray();
    var this_data = $(this);
    var headers = $("#sortingTable").find("th");

    var correct = true;
    $('input[name=wms_code],input[name=sku_desc],select[name=put_zone]' ).each(function (indx) {
    var $currentField = $(this);
    if ($currentField.val() == '')
    {
    $currentField.parent('div').addClass('has-error');
    correct = false;
    $currentField.one('keydown',function()
    {
     $currentField.removeClass('has-error');
    });
    }
    else
    {
    $currentField.parent('div').removeClass('has-error');
    }
    });

    if(correct == true)
    {
    formData = new FormData()
    files = $("#add_sku").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });

    $.each(values, function(i, val) {
        formData.append(val.name, val.value);
    });
    $.ajax({url: '/insert_sku/',
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            'success': function(response) {
         this_data.find(".insert-status").html(response);
         this_data.find(".insert-status").show()
         if (response == "New WMS Code Added") {
             $("#sortingTable").dataTable().fnReloadAjax();
             $.fn.make_disable($("#add_sku"));
         }
         else {
         }
         $('.loading').addClass('display-none');
            }});
    }
    else
    {
    this_data.find(".insert-status").html("Missing Required Fields").show();
    $('.loading').addClass('display-none');
    }
    event.preventDefault();
  });



 $("body").on("submit","#update_supplier, #add_customer, #update_customer",function(){

    $('input[type="text"], textarea[name="address"]').each(function (indx) {
    var $currentField = $(this);
    if ($currentField.val() === '')
    {
    $currentField.parent('div').addClass('has-error');
    }
    else
    {
    $currentField.parent('div').removeClass('has-error');
    }
    });
});

  $( "#add_zone" ).submit(function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    $.ajax({url: '/add_zone?' + values,
            'success': function(response) {
      this_data.find(".insert-status").html(response);
      if (response == "Added Successfully") {
          zone = this_data.find('input[name="zone"]').val();
          var response_data = '<div class="panel panel-default"><div aria-controls="collapse' + zone + '" aria-expanded="true" href="#collapse' + zone + '" data-parent="#accordion" data-toggle="collapse" data-id="' + zone + '" id="heading' + zone + '" role="tab" class="panel-heading"><h4 class="panel-title"><a class="collapsed">' + zone + '</a> </h4></div><div aria-labelledby="heading' + zone + '" role="tabpanel" class="panel-collapse collapse" id="collapse' + zone + '" aria-expanded="true" style=""><div class="panel-body"><table class="table"><tbody><tr class="active"><th>Location</th><th>Capacity</th><th>Put Sequence</th><th>Get Sequence</th><th>Status</th></tr></tbody></table></div></div></div>'
         $('#accordion').append(response_data);
     $("#add_location .modal-body").find("select[name=zone]").append("<option>"+zone+"</option>");
      }
      else {
      }
    $('.loading').addClass('display-none');
            }});
    event.preventDefault();
  });

  $("body").on("submit","#add_location",function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);

    var correct = true;

    $('input[name=location],select[name=zone]').each(function (indx) {
    var $currentField = $(this);
    if ($currentField.val() === '')
    {
    $currentField.parent('div').addClass('has-error');
    correct = false;
    $currentField.one('keydown',function()
    {
     $currentField.removeClass('has-error');
    });
    }
    else
    {
    $currentField.parent('div').removeClass('has-error');
    }
    });

    if(correct){
    $.ajax({url: '/add_location?' + values,
            'success': function(response) {
      this_data.find(".insert-status").html(response).show();
      if (response == "Added Successfully") {
        $.fn.make_disable($("#add_location"));
        var zone = this_data.find('select[name=zone_id]').val();
        var loc = this_data.find('input[name=location]').val();
        var capacity = this_data.find('input[name=max_capacity]').val();
        var pallet_capacity = this_data.find('input[name=pallet_capacity]').val();
        var put_sequence = this_data.find('input[name=fill_sequence]').val();
        var pick_sequence = this_data.find('input[name=pick_sequence]').val();
        var rec_status = this_data.find('select[name=status]').val();
        if (!capacity)
        capacity = 0
        if (!put_sequence)
        put_sequence = 0
        if(!pick_sequence)
        pick_sequence = 0
        var header = '<div class="modal fade" id="' + loc + '" tabindex="-1" role="dialog" aria-labelledby="myLargeModalLabel" aria-           hidden="true"></div>'
        var data = '<tr class="locations" id="' + loc + '"><td>' + loc + '</td><td>' + capacity + '</td><td>' + put_sequence + '</td><td>' +   pick_sequence + '</td><td>' + rec_status + '</td></tr>'
        $('#collapse' + zone).find('.panel-body').prepend(header);
        $('#collapse' + zone).find('.panel-body').find('tbody').append(data);
      }
      else {
      }
    $('.loading').addClass('display-none');
            }});
    }
    else{
    $("body").find(".insert-status").html("Missing required fields")
    }
    event.preventDefault();
  });

  $("body").on("submit",  "#update_sku" , function( event ) {

    event.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $("#update_sku").serializeArray();
    data_id = $(this).find("input[name=data_id]").val();
    var data_row = $("#sortingTable").dataTable();
    var this_data = $(this);

    var correct = true;
    $('input[name=wms_code],input[name=sku_desc],select[name=zone_id]' ).each(function (indx) {
    var $currentField = $(this);
    if ($currentField.val() === '')
    {
    $currentField.parent('div').addClass('has-error');
    correct = false;
    $currentField.one('keydown',function()
    {
     $currentField.removeClass('has-error');
    });
    }
    else
    {
    $currentField.parent('div').removeClass('has-error');
    }
    });

    formData = new FormData()
    files = $("#update_sku").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });

    $.each(values, function(i, val) {
        formData.append(val.name, val.value);
    });

    $.ajax({url: '/update_sku/',
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            'success': function(response) {
      this_data.find(".insert-status").html(response).show();

      data_row.fnUpdate({'Sellerworx SKU Code': '',
                       'WMS SKU Code': this_data.find("input[name=wms_code]").val(),
                        'Product Description': this_data.find("input[name=sku_desc]").val(),
                        'SKU Type': this_data.find("select[name=sku_type]").val(),
                        'SKU Category': this_data.find("input[name=sku_category]").val(),
                        'SKU Class': this_data.find("input[name=sku_class]").val(),
                        'Zone': this_data.find("select[name=zone_id]").val(),
                        'Status': this_data.find("select[name=status]").val(),
                         }, $("#sortingTable tr[data-id="+ data_id + "]"));
       $('.loading').addClass('display-none');
            }});

    event.preventDefault();
  });

  $("body").on("submit",  "#update_supplier" , function( event ) {

    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var err_len = $("body #update_supplier").find(".has-error").length;
    data_id = $(this).find("input[name=id]").val();
    var data_row = $("#sortingTable").dataTable();
    var this_data = $(this);
    var reg = /^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
    if (reg.test(this_data.find("input[name=email_id]").val())){
        $(".insert-status").html("");
        if(err_len == 0)
        {
          $.ajax({url: '/update_supplier_values?' + values,
                 'success': function(response) {
                    this_data.find(".insert-status").html(response).show();

                    data_row.fnUpdate({'Supplier ID': this_data.find("input[name=id]").val(),
                                       'Name': this_data.find("input[name=name]").val(),
                                       'Address': this_data.find("textarea[name=address]").val(),
                                       'Phone Number': this_data.find("input[name=phone_number]").val(),
                                       'Email': this_data.find("input[name=email_id]").val(),
                                       'Status': this_data.find("select[name=status]").val(),
                                      }, $("#sortingTable tr[id="+data_id + "]"));

            }});
        }
    $('.loading').addClass('display-none');
}

 else{
        $(".insert-status").html("Entered email is incorrect");
    $('.loading').addClass('display-none');
 }


    event.preventDefault();
  });

  $("body").on("submit",  "#update_location" , function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    loc = $(this).find("input[name=LOCID]").val();
    var location1=this_data.find("input[name=location]").val();
    var capacity=this_data.find("input[name=max_capacity]").val();
    var pallet_capacity=this_data.find("input[name=pallet_capacity]").val();
    var put_seq=this_data.find("input[name=fill_sequence]").val();
    var get_seq=this_data.find("input[name=pick_sequence]").val();
    var status1=this_data.find("select[name=status]").val();

    if( capacity == "")
    {
    capacity = 0
    }
    if(put_seq == "")
    {
    put_seq = 0
    }
    if(get_seq == "")
    {
    get_seq = 0
    }
    $.ajax({url: '/update_location?' + values,
            'success': function(response) {
    $('.loading').addClass('display-none');
       this_data.find(".insert-status").html(response).show();
    if (response == "Updated Successfully") {
     $("tr[id="+location1+"]").html("<td>"+location1+"</td><td>"+capacity+"</td><td>"+put_seq+"</td><td>"+get_seq+"</td><td>"+status1+"</td>");
     }
        //$('.loading').addClass('display-none');
            }});

    event.preventDefault();
  });

  $('body').on("click", '.locations', function() {
    data_id = $(this).attr('id');
    context = this;
    $('#location-toggle').empty();
    //$('#' + data_id).empty();
    $.ajax({url: '/get_location_data?location_id=' + data_id,
            'success': function(response) {
                $('#location-toggle').html(response);
               $('#location-toggle').modal();
               $("#locationModal").modal();

            }});
      $("#locationModal").modal();
  });


  $("#add_rack").on("click",function() {
   $('#location-toggle').empty();
   $.ajax({url: '/add_location_data',
            'success': function(response) {
                $('#location-toggle').append(response);
               $('#location-toggle').modal();
               $("#locationModal").modal();

            }});
    });

  $('body').on("click", '#sku-master .results', function() {
    var data_id = $(this).data('id');
    var context = this;
    $('#sku-toggle').empty();
    $.ajax({url: '/get_sku_data?data_id=' + data_id,
            'success': function(response) {
                $('#sku-toggle').html(response);
            }});
    $("#sku-toggle").modal();
  });

  $('body').on("click", '#supplier-master .results', function() {
    var data_id = $(this).attr('id');
    var context = this;
    $('#supplier-toggle').empty();
    $.ajax({url: '/get_supplier_update?data_id=' + data_id,
            'success': function(response) {
                $('#supplier-toggle').append(response);
            }});
    $("#supplier-toggle").modal();
  });

  $('body').on("click", '#customer-sku .results', function() {
    var data_id = $(this).attr('id');
    var context = this;
    $('#customer-toggle').empty();
    $.ajax({url: '/get_customer_sku_data?data_id=' + data_id,
            'success': function(response) {
                $('#customer-toggle').append(response);
            }});
    $("#customer-toggle").modal();
  });

  $(".button_column").mouseenter(function() {
    $("button[type='add_zone']").animate({ opacity: 1 });
    $("button[type='add_location']").animate({ opacity: 1 });
      }).mouseleave(function() {
    $("button[type='add_zone']").animate({ opacity: 0 }, 0);
    $("button[type='add_location']").animate({ opacity: 0 }, 0);
    });

  $("button[type='get_input']").click(function() {
    $("form").trigger('reset');
    $("form").find(".insert-status").empty();
    $("form").find(".form-control").parent('div').removeClass("has-error");
    $("#add_sku #new-market").nextAll().remove();
  });

  $("button[type='add_zone']").click(function() {
    $("form").trigger('reset');
    $("form").find(".insert-status").empty();
    $("form").find(".form-control").parent('div').removeClass("has-error");
  });

  $("button[type='add_location']").click(function() {
    $("form").trigger('reset');
    $("form").find(".insert-status").empty();
    $("form").find(".form-control").parent('div').removeClass("has-error");
  });

  $("body").on("submit",  "#add_supplier_mapping" , function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    sku = $(this).find("input[name=sku_code]").val();
    var data_row = $("#sortingTable").dataTable();
    var this_data = $(this);
    var wms = $(this).find("input[name=wms_id]").val();
    var priority = $(this).find("input[name=preference]").val();
    var correct = true;
    $('input[name=wms_id]').each(function (indx) {
    var $currentField = $(this);
    if ($currentField.val() === '')
    {
    $currentField.parent('div').addClass('has-error');
    correct = false;
    }
    else
    {
    $currentField.parent('div').removeClass('has-error');
    }
    });

    if(wms != "")
    {
    if(correct == true)
    {
    $.ajax({url: '/insert_mapping?' + values,
            'success': function(response) {
      this_data.find(".insert-status").html(response).show();

      if (response == "Added Successfully") {
        $.fn.make_disable($("#add_supplier_mapping"))
        $("#sortingTable").DataTable().row.add({'Supplier ID ': this_data.find("select[name=supplier_id]").val(),
                          'WMS Code': this_data.find("input[name=wms_id]").val(),
                          'Supplier Code': this_data.find("input[name=supplier_code]").val(),
                          'Priority': this_data.find("input[name=preference]").val(),
                          'MOQ': this_data.find("input[name=moq]").val(),
                           }).draw( false );
         }
         else {
         }
    $('.loading').addClass('display-none');
      }});
    }
    }
    else
    {
    this_data.find(".insert-status").html("Missing Required Fields").show();
    event.preventDefault();
    }
    $('.loading').addClass('display-none');
    event.preventDefault();
  });

  $("body").on("submit",  "#update_customer_sku" , function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    cust_id = $(this).find("input[name=customer_id]").val();
    var data_row = $("#sortingTable").dataTable();
    var this_data = $(this);
    var sku_code = $(this).find("input[name=sku_code]").val();
    var price = $(this).find("input[name=price]").val();
    var correct = true;
    var insert_status = "Missing Required Fields";
    if (sku_code === '' || price === '') {
      correct = false;
      insert_status = "Missing Required Fields";
    }
    if(correct == true) {
      $.ajax({url: '/update_customer_sku_mapping?' + values,
            'success': function(response) {
        this_data.find(".insert-status").html(response).show();

        if (response == "Updated Successfully") {
           $("#sortingTable").dataTable().fnReloadAjax();
        } else {
           this_data.find(".insert-status").html(response).show();
        }
        $('.loading').addClass('display-none');
      }});
    } else {
      this_data.find(".insert-status").html(insert_status).show();
      event.preventDefault();
    }
    $('.loading').addClass('display-none');
    event.preventDefault();
  });

   $("body").on("submit",  "#update_sku_supplier" , function( event ) {


    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var data_row = $("#sortingTable").dataTable();
    var this_data = $(this);
    data_id = $(this).find("[name=data-id]").val();
    priority = $(this).find("input[name=preference]").val();

    var correct = true;

    $('input[name=preference]').each(function (indx) {
    var $currentField = $(this);
    if ($currentField.val() === '')
    {
    $currentField.parent('div').addClass('has-error');
    correct = false;
    }
    else
    {
    $currentField.parent('div').removeClass('has-error');
    }
    });

    if(priority != "")
    {
    if(correct = true)
    {

    $.ajax({url: '/update_sku_supplier_values?' + values,
            'success': function(response) {
      this_data.find(".insert-status").html(response).show();

      data_row.fnUpdate({'Supplier ID ': this_data.find("input[name=supplier_id]").val(),
                        'WMS Code': this_data.find("input[name=sku_id]").val(),
                        'Supplier Code': this_data.find("input[name=supplier_code]").val(),
                        'Priority': this_data.find("input[name=preference]").val(),
                        'MOQ': this_data.find("input[name=moq]").val(),
                         }, $("#sortingTable tr[id="+data_id + "]"));
      $('.loading').addClass('display-none');

        }});
    }
    }
    else
    {
    this_data.find(".insert-status").html("Missing Required Fields").show();
    $('.loading').addClass('display-none');
    event.preventDefault();
    }
   event.preventDefault();
  });

  $('body').on("click", '#supplier-sku .results', function() {
    var data_id = $(this).attr('id');
    var context = this;
    $('#mapping-toggle').empty();
    $.ajax({url: '/get_sku_supplier_update?data_id=' + data_id,
            'success': function(response) {
                $('#mapping-toggle').append(response);
            }});
    $("#mapping-toggle").modal();
  });

  $('body').on("click", '.add-market', function() {
      new_row = $('body').find('#new-market').clone();
      add_id = $(this).closest("form").attr("id");
      if(add_id == 'add_sku')
      {
          $(this).parent().prev().append("<div class='row col-md-12'>" + new_row.html() + "<div class='col-md-1'><img src='/static/img/details_close.png' class='del-map'></div></div>");
      }
      else
      {
          $(this).parent().prev().after("<div class='row col-md-12'>" + new_row.html() + "</div>");
      }
  });

  $('body').on("click", '.del-map', function() {
    data_id = $(this).parent().parent().find("[name=market_id]").val();
    if(data_id != '' && data_id != undefined)
    {
      $.ajax({url: '/delete_market_mapping?data_id=' + data_id,
            'success': function(response) {
            }});
    }
    $(this).parent().parent().remove();
  });

  $("body").on("submit",  "#print-excel-sheet" , function( e ) {
    data = []
    table = $(this).parent().find("table:last").attr("id");
    if(table == undefined)
    {
        table = $("table:not(.table)").last().attr("id");
    }
    table_id = "#" + table;
    e.preventDefault();
    $.ajax({type: 'POST',
    url: '/results_data/',
    data: {
            "columns": $(table_id).myfunction_excel(),
            "serialize_data": $(this).serialize(),
            
    },
    'success': function(response) {
      window.location = response;
    }
    
    });
  });

  $( "#add_customer" ).submit(function( event ) {
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    var data = {};
    var data_row = $("#sortingTable").dataTable();
    var headers = $("#sortingTable").find("th");
    cus_id = $(this).find("input[name=id]").val();
    cus_name= $(this).find("input[name=name]").val();
    cus_addr = $(this).find("textarea[name=address]").val();
    cus_pho = $(this).find("input[name=phone_number]").val();
    cus_email = $(this).find("input[name=email_id]").val();
    cus_status = $(this).find("select[name=status]").val();
    if ( cus_id !="" && cus_name != "" && cus_addr !="" && cus_pho !="" && cus_email !="") {
    $('.loading').removeClass('display-none');
    var reg = /^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
    if (reg.test(cus_email)){
    $.ajax({url: '/insert_customer?' + values,
            'success': function(response) {
         this_data.find(".insert-status").html(response).show();
         $.fn.make_disable($("#add_customer"));
         data_row.DataTable().row.add({' Customer ID': cus_id, 'Customer Name': cus_name, 'Address': cus_addr, 'Phone Number': cus_pho,
                                       'Email': cus_email, 'Status': cus_status }).draw();
         $('.loading').addClass('display-none');
    }});

 }   
 else{
        $(".insert-status").html("Invalid email").show().fadeOut(3000);
    $('.loading').addClass('display-none');
 }
   }
   else {
    this_data.find(".insert-status").html("Missing Required fields").show();
}
    $('.loading').addClass('display-none');
    event.preventDefault();
  });

  $('body').on("click", '#customer-master .results', function() {
    var data_id = $(this).attr('id');
    var context = this;
    $('#supplier-toggle').empty();
    $.ajax({url: '/get_customer_update?data_id=' + data_id,
            'success': function(response) {
                $('#supplier-toggle').append(response);
            }});
    $("#supplier-toggle").modal();
  });

  $("body").on("submit",  "#update_customer" , function( event ) {

    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var err_len = $("body #update_customer").find(".has-error").length;
    data_id = $(this).find("input[name=id]").val();
    var data_row = $("#sortingTable").dataTable();
    var this_data = $(this);
    var reg = /^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
    if (reg.test(this_data.find("input[name=email_id]").val())){
        $(".insert-status").html("");
        if(err_len == 0)
        { 
          $.ajax({url: '/update_customer_values?' + values,
                 'success': function(response) {
                    this_data.find(".insert-status").html(response).show();

                    data_row.fnUpdate({' Customer ID': this_data.find("input[name=id]").val(),
                                       'Customer Name': this_data.find("input[name=name]").val(),
                                       'Address': this_data.find("textarea[name=address]").val(),
                                       'Phone Number': this_data.find("input[name=phone_number]").val(),
                                       'Email': this_data.find("input[name=email_id]").val(),
                                       'Status': this_data.find("select[name=status]").val(),
                                      }, $("#sortingTable tr[id="+data_id + "]"));

            }});
        }
    $('.loading').addClass('display-none');
}

 else{
        $(".insert-status").html("Entered email is incorrect");
    $('.loading').addClass('display-none');
 }
    event.preventDefault();
  });

  $("body .add-bom").on("click",function() {
   $('#sku-toggle').empty();
   $.ajax({url: '/add_bom_data',
            'success': function(response) {
                $('#sku-toggle').append(response);
               $('#sku-toggle').modal();
               $("#myModal").modal();
                tr_row = $("tr#raise-bom-row").html();
                $("#add_bom .active").after("<tr>" + tr_row + "</tr>");

            }});
    });

  $("body").on("click","#add_bom .save-bom", function(e){
    e.preventDefault();
    data = $("form:not(#raise-bom-row)").serializeArray()
    $.ajax({url: '/insert_bom_data/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $("body").find(".insert-status").html(response).show();
                if(response == 'Added Successfully'){
                    $.fn.make_disable($("#add_bom"));
                }
                $("#sortingTable").dataTable().fnReloadAjax();
            }});
  });

  $("body").on("click", "#add_bom #add_row", function(e){
    row =  $(this).parent().parent();
    var data = {}
    if($(this).attr("src").search("open") != -1)
    {
        row.after("<tr>" + $("body #raise-bom-row").html() + "</tr>");
        $(this).attr("src","/static/img/details_close.png");
    }
    else {
        data_id = row.find("[name=id]").val();
        if(data_id) {
            $.ajax({url: '/delete_bom_data?data_id=' + data_id,
                'success': function(response) {
            }});
        }
        row.remove();
    }

  });

  $('body').on("click", '#bom-master .results', function() {
    var data_id = $(this).data('id');
    var context = this;
    $('#sku-toggle').empty();
    $.ajax({url: '/get_bom_data?data_id=' + data_id,
            'success': function(response) {
                $('#sku-toggle').append(response);
                $("#sku-toggle").modal();
                $("#myModal").modal();
            }});
  });

  if ($(".tab-content").hasClass("add-excel")) {

    $excel_position = $(".tab-content").find(".dataTables_filter")
    print_value = $(".tab-content").attr("value");
    $excel_position.after("<form id='print-excel-sheet' style='float: right;margin-right: 20px;'><input type='hidden' name='excel_name' value='"+print_value+"'><button type='submit' class='btn btn-primary'>Excel</button></form>")
  }

  var suggestions = [""]
  $value = $("#add_customer_sku input[name=customer_id]");
  QUERY = $value.val();
  $('#add_customer_sku input[name=customer_id]').typeahead({
        name: 'typeahead',
        remote:'/search_customer_sku_mapping?search_data=%QUERY',
        limit : 10
    });

  $("body").on("submit","#add_warehouse_user",function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serializeArray();
    var this_data = $(this);
    username = $(this).find("[name=username]").val();
    if(username)
    {
        $.ajax({url: '/add_warehouse_user/',
                method: 'POST',
                data: values,
                'success': function(response) {
          this_data.find(".insert-status").html(response).show();
          $("#warehouseMaster").dataTable().fnReloadAjax();
          $('.loading').addClass('display-none');
        }});
    }
  });

  $('#warehouseMaster').on("click", 'tbody tr td', function() {
    data_id = $(this).parent().attr('id');
    context = this;
    $.ajax({url: '/get_warehouse_user_data?username=' + data_id,
            'success': function(response) {
                $('#warehouse-toggle').html(response);
               $('#warehouse-toggle').modal();

            }});
  });

  $("body").on("submit","#update_warehouse_user",function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serializeArray();
    var this_data = $(this);
    username = $(this).find("[name=username]").val();
    if(username)
    {
        $.ajax({url: '/update_warehouse_user/',
                method: 'POST',
                data: values,
                'success': function(response) {
          this_data.find(".insert-status").html(response).show();
          $("#warehouseMaster").dataTable().fnReloadAjax();
          $('.loading').addClass('display-none');
        }});
    }
  });

  $( "#add_discount" ).submit(function( event ) {
    event.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serializeArray();
    var this_data = $(this);
    var headers = $("#sortingTable").find("th");

    var sku_code = $('input[name=sku_code]')
    var sku_discount = $('input[name=sku_discount]')
    correct = true;
    if ((sku_code.val() == '') && (sku_discount.val() != ''))
    {
        sku_code.parent('div').addClass('has-error');
        correct = false;
        sku_code.on('keydown',function()
        {
            sku_code.removeClass('has-error');
            correct = true;
        });
    }
    else
    {
        sku_discount.parent('div').removeClass('has-error');
    }

    if ((sku_code.val() != '') && (sku_discount.val() == ''))
    {
        sku_discount.parent('div').addClass('has-error');
        correct = false;
        sku_discount.on('keydown',function()
        {
            sku_discount.removeClass('has-error');
            correct = true;
        });
    }
    else
    {
        sku_discount.parent('div').removeClass('has-error');
    }

    var sku_code = $('input[name=category]')
    var sku_discount = $('input[name=category_discount]')
    if ((sku_code.val() == '') && (sku_discount.val() != ''))
    {
        sku_code.parent('div').addClass('has-error');
        correct = false;
        sku_code.on('keydown',function()
        {
            sku_code.removeClass('has-error');
            correct = true;
        });
    }
    else
    {
        sku_discount.parent('div').removeClass('has-error');
    }

    if ((sku_code.val() != '') && (sku_discount.val() == ''))
    {
        sku_discount.parent('div').addClass('has-error');
        correct = false;
        sku_discount.on('keydown',function()
        {
            sku_discount.removeClass('has-error');
            correct = true;
        });
    }
    else
    {
        sku_discount.parent('div').removeClass('has-error');
    }

    if(correct == true)
    {

        $.ajax({url: '/insert_discount/',
              data: {'data': JSON.stringify(values)},
              method: 'POST',
              'success': function(response) {
        $(".insert-status").html(response);
        $(".insert-status").show()
      if (response == "Updated Successfully") {
             $.fn.make_disable($("#add_discount"));
             $("#sortingTable").dataTable().fnReloadAjax();
         }
         else {
         }
         $('.loading').addClass('display-none');
            }});
    }
    else
    {
    $(".insert-status").html("Missing Required Fields").show();
    $('.loading').addClass('display-none');
    }
    event.preventDefault();
  });

  $( "#add_vendor" ).submit(function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    var data = {};
    var data_row = $("#vendorTable").dataTable();
    var headers = $("#vendorTable").find("th");
    vendor_id = $(this).find("input[name=vendor_id]").val();
    vendor_name= $(this).find("input[name=name]").val();
    vendor_addr = $(this).find("textarea[name=address]").val();
    vendor_pho = $(this).find("input[name=phone_number]").val();
    vendor_email = $(this).find("input[name=email_id]").val();
    vendor_status = $(this).find("select[name=status]").val();
    if ( vendor_id !="" && vendor_name != "" && vendor_addr !="" && vendor_pho !="" && vendor_email !="") {
      $('.loading').removeClass('display-none');
      var reg = /^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
      if (reg.test(vendor_email)){
        $.ajax({url: '/insert_vendor?' + values,
              'success': function(response) {
           this_data.find(".insert-status").html(response).show();
           if(response == 'New Vendor Added') {
             $.fn.make_disable($("#add_vendor"));
           }
           data_row.DataTable().row.add({'Vendor ID': vendor_id,
                          'Name': vendor_name,
                          'Address': vendor_addr,
                          'Phone Number': vendor_pho,
                          'Email': vendor_email,
                          'Status': vendor_status,
                           }).draw();
           $('.loading').addClass('display-none');
        }});
      } }
  });

  $('body').on("click", '#vendor-master .results', function() {
    var data_id = $(this).attr('id');
    var context = this;
    $('#supplier-toggle').empty();
    $.ajax({url: '/get_vendor_data?data_id=' + data_id,
            'success': function(response) {
                $('#supplier-toggle').append(response);
            }});
    $("#supplier-toggle").modal();
  });

  $("body").on("submit",  "#update_vendor" , function( event ) {

    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var err_len = $("body #update_vendor").find(".has-error").length;
    data_id = $(this).find("input[name=vendor_id]").val();
    var data_row = $("#vendorTable").dataTable();
    var this_data = $(this);
    var reg = /^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/;
    if (reg.test(this_data.find("input[name=email_id]").val())){
        $(".insert-status").html("");
        if(err_len == 0)
        { 
          $.ajax({url: '/update_vendor_values?' + values,
                 'success': function(response) {
                    this_data.find(".insert-status").html(response).show();

                    data_row.fnUpdate({'Vendor ID': this_data.find("input[name=vendor_id]").val(),
                                       'Name': this_data.find("input[name=name]").val(),
                                       'Address': this_data.find("textarea[name=address]").val(),
                                       'Phone Number': this_data.find("input[name=phone_number]").val(),
                                       'Email': this_data.find("input[name=email_id]").val(),
                                       'Status': this_data.find("select[name=status]").val(),
                                      }, $("#vendorTable tr[id="+data_id + "]"));
                    $('.loading').addClass('display-none');

            }});
        }
        else {
          $('.loading').addClass('display-none');
        }
 }

 else{
        $(".insert-status").html("Entered email is incorrect");
    $('.loading').addClass('display-none');
 }
    event.preventDefault();
  });
});
