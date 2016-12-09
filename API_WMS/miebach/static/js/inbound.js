$(document).ready(function() {

  $.fn.confirm_modal = function(message) {
        var obj = $.Deferred();
        var confirmation = false;
        BootstrapDialog.confirm({
            title: 'Confirmation',
            message: message,
            btnCancelLabel: 'No', // <-- Default value is 'Cancel',
            btnOKLabel: 'Yes', // <-- Default value is 'OK',
            callback: function(result) {
                // result will be true if button was click, while it will be false if users close the dialog directly.
                obj.resolve();
                obj.done(function(){
                confirmation = result;
                return confirmation;
               });
            }
        });
  }

    $.fn.validate_qc = function(this_data) {
    ins_status = ''
    form_id = this_data.closest("form");
    row_id = form_id.find(".table tr:not('.active')").attr("id");
    accepted = form_id.find("tr#" + row_id + " [name=accepted_quantity]").val();
    rejected = form_id.find("tr#" + row_id + " [name=rejected_quantity]").val();
    quantity = Number(this_data.parent().prev().html());
    total = Number(accepted) + Number(rejected);
    if(total == quantity )
    {   
        $("#scan-qc").prop("disabled", true);
    }
    else if(total > quantity)
    {   
        ins_status = "Total quantity should be less than or equal to quality check quantity"
        form_id.find(".insert-status").html(ins_status);
        diff = Number(this_data.val()) - Number(Math.abs(total - quantity));
        this_data.val(diff);

    }
    else {
       form_id.find(".insert-status").html(""); 
    }

    return ins_status;

    }

  $.fn.validate_qc_serial = function(data_id) {
   exist_status = ''
   data = 'serial=' + data_id + '&id=' + $("#wms_quality_wise .table").find("tr:not('.active')").attr("id");
   $.ajax({url: '/check_serial_exists/',
           method: 'POST',
           async: false,
           data: data,
        'success': function(response) {
            exist_status = response
   } });

  return exist_status;

  }

  $.fn.get_supplier_data = function(data_id) {
    modal_field = $(".process-toggle:not(#po-modal1)")
    $.ajax({url: '/get_supplier_data?supplier_id=' + data_id,
            'success': function(response) {
                modal_field.html(response);
                modal_field.modal();
            }});

  }

  $.fn.get_received_orders = function(data_id) {
    modal_field = $(".process-toggle:not(#po-modal1)")
    $.ajax({url: '/get_received_orders?supplier_id=' + data_id,
            'success': function(response) {
                modal_field.html(response);
                modal_field.modal();
            }});
  }

  $.fn.quality_check_data = function(data_id) {
    modal_field = $(".process-toggle:not(#po-modal1)");
    modal_field.empty();
    if(data_id){
    $.ajax({url: '/quality_check_data?order_id=' + data_id,
            'success': function(response) {
                modal_field.append(response);
            }});
      modal_field.modal();
        }

  }



  scanned = []
  $("body").on('keydown', '#grn-form #scan_imei',function(e){

  if(e.which == 13) {
   value = $(this).val();
   this_data = $(this);
   temp = value.split("\n");
   data_id = temp[temp.length-1]
   count = Number($(this).parent().prev().find("input").val());
   $.ajax({url: '/check_imei_exists?' + "imei" + "=" + data_id,
        'success': function(response) {
            if(response.search('exists') == -1)
            {
                $("body").find(".insert-status").html("");
                if(scanned.indexOf(data_id) < 0)
                {
                    scanned.push(data_id);
                    count = count + 1;
                }

            }
            else
            {
                $("body").find(".insert-status").html(response);
                temp.splice( temp.indexOf(data_id), 1 );
            }
            this_data.parent().prev().find("input").val(count);
            temp.push('');
            this_data.val(temp.join('\n'));

   } });
  }

  });


    $("body").on("click","#grn-form .close",function() {
      scanned = []
    });

    $("body").on("click","#generate_picklist,#putaway-list .close",function() {
      scanned = []
    });


    $("body").on("click",'.plus1',function(e) {
    e.stopImmediatePropagation();
    var choice = $(this).attr("src");
    if(choice.search('open') != -1)
    {
    $(this).parent().parent().parent().parent().append("<div class='row col-md-12'>" + $(this).parent().parent().parent().html() + "</div>");
    $(this).parent().parent().parent().parent().parent().find("div.row:last").find("input").val("");
    $(this).attr("src","/static/img/details_close.png");
    }
    else
    {
        $(this).parent().parent().remove();
        var data_id = $(this).parent().parent().find("[name=id]").val();
        if (data_id && $("#raise-purchase").find(".active").attr("id") == 'raise-st')
        {
        $.ajax({url: '/delete_st?data_id=' + data_id,
                  'success': function(response) {
          $("#raised-st").dataTable().fnReloadAjax();
               }});
        }

    }
});

    $("body").on("click",'.plus2',function(e) {
        e.stopImmediatePropagation();
        var choice = $(this).attr("src");
        if(choice.search('open') != -1)
        {
        $(this).attr("src","/static/img/details_close.png");
        $(".clearfix:last").append("<div class='row col-md-12'><div class='form-group'><div class='col-md-3'><input id='wms1' type='text' name='wms_code' class='form-control mapping-check' value=''></div><div class='col-md-3'><input id='wms1' type='text' name='supplier_code' class='form-control ' value=''></div><div class='col-md-3'><input id='quant1' type='text' name='order_quantity' class='form-control numvalid' value=''></div><div class='col-md-2'><input type='text' name='price' class='form-control pricevalid' value=''></div><div class='col-md-1'><img src='/static/img/details_open.png' class='plus2'></div></div></div>");
        }
        else
        {
        var data_id = $(this).parent().parent().find("[name=data-id]").val();
        if (data_id)
        {
        $.ajax({url: '/delete_po?' + data_id+"="+data_id,
                  'success': function(response) {
          $("#sortingTable").dataTable().fnReloadAjax();
               }});
        }
        $(this).parent().parent().parent().remove();
        }
});

    $("body").on("blur", ".mapping-check", function() {
        var wms_code = this.value;
        var temp = "[value="+ wms_code + "]";
        var count = 0;
        $("body form").find("[name=wms_code]").each(function(index,value){
            var cur_wms = $(value).val();
            if(wms_code == cur_wms){
                count +=1
            }
        });

        var this_data = $(this);
        if(Number(count) > 1){
            $("body").find(".insert-status").html("Entered WMS Code already in the list").show();
            this_data.val("");
        }
        else {
            $("body").find(".insert-status").html("").show();
            var supplier_id = $(this).closest('.modal-body').find('select[name=supplier_id]').val();
            if (supplier_id == undefined) {
                var supplier_id = $(this).closest('.modal-body').find('input[name=supplier_id]').val();
            }
            var values = "wms_code=" + wms_code + "&supplier_id=" + supplier_id
            $.ajax({url: '/get_mapping_values?' + values,
                'success': function(response) {
                    if(response.supplier_code != undefined) {
                        this_data.parent().parent().find('input[name=supplier_code]').val(response.supplier_code);
                        this_data.parent().parent().find('input[name=price]').val(response.price);
                    }
                    else {
                        this_data.parent().parent().find('input[name=supplier_code]').val('');
                        this_data.parent().parent().find('input[name=price]').val('');
                    }
                }});  
        }
        });

$("#confirmed-po").on("blur",".smallbox",function() {
var received = $(this).val();
var ordered = $(this).parent().parent().find("td").eq(1).html();
    if (Number(ordered) < Number(received))
    {
        $('.top-right').notify({
          message: { text: "Received Quantity must be less than or equal to the Ordered quantity" },
          type: 'danger',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
    }
});


  $("body").on("submit", "#add_po", function( event ) {
    event.preventDefault();
    var values = $(this).serialize();
    var this_data = $(this);
    var data = {};
    var headers = $("#sorting_table").find("th");
    sup_id = $(this).find("input[name=suppler_id]").val();
    wms_code = $(this).find("input[name=wms_code]").val();
    quant = $(this).find("input[name=order_quantity]").val();
    var correct = true;


    $('input[name=wms_code]').each(function(){
    var $wms = $(this);
    if ($wms.val() === '')
    {
    }
    else
    {
    var check = $wms.parent().parent().find("input[name=order_quantity]");
      if(check.val() == '' || check.val() == '0')
      {
      check.parent('div').addClass('has-error');
      correct = false
      }
      else
      {
      check.parent('div').removeClass('has-error');
      }
    }
    });
    if(wms_code != "" && quant != "")
    {
    if(correct == true)
    {
        $.ajax({url: '/validate_wms?' + values,
                  'async': false,
                  'success': function(response) {
                    status = response
               }});
        if(status == 'success' || confirm(status + "\n Do you want to continue"))
        {
           $('.loading').removeClass('display-none');
           $.ajax({url: '/add_po?' + values,
                'success': function(response) {
                   this_data.find(".insert-status").html(response).show();
                   if(response == "Added Successfully"){
                     $.fn.make_disable($("#add_po"));
                   }
                   $("#generated-po #sortingTable").dataTable().fnReloadAjax();
            }});
        }
    }
    $('.loading').addClass('display-none');
    }
    else
    {
    wms1 = $(this).find("#wms1");
    ord1 = $(this).find("#quant1");
    if(wms1.val() == "")
    {
    wms1.parent('div').addClass('has-error');
    }
    else
    {
    ord1.parent('div').removeClass('has-error');
    }
    if(ord1.val() == "")
    {
    ord1.parent('div').addClass('has-error');
    }
    else
    {
    ord1.parent('div').removeClass('has-error');
    }
    this_data.find(".insert-status").html("Missing WMS Code or Quantity").show();
    $('.loading').addClass('display-none');
    event.preventDefault();
    }
    event.preventDefault();
   });


  $("#raise-po").on("click",function(){
   $('#location-toggle').empty();
   active_id = $("#raise-purchase").find(".active").attr("id");
   url = '/raise_st_toggle';
   if(active_id == 'generated-po')
   {
     url = '/raise_po_toggle'
   }
   $.ajax({url: url,
           'success': function(response) {
              $('#po-modal').html(response);
              $('#po-modal').modal();
              if(url.search('po') != -1)
              { 
                $("[name=supplier_id]").select2({width: 'resolve'});
                $.fn.modal.Constructor.prototype.enforceFocus = function () {};
              }
         }});

  });

  $("#generated-po #sortingTable ").on("draw.dt",function(){
   var checkboxes = $("#generated-po tr.results td:first-child ").find("input[type='checkbox']"),
   submitButt = $("#generated-po").find("button[type='submit']");
   submitButt.attr("disabled", !checkboxes.is(":checked"));
});

  $("#confirmed-po #confirmed ").on("draw.dt",function(){
    $("#confirmed-po").find('button[type="submit"]').attr("disabled",true);
});

  $("#received-items #returns-table").on("draw.dt",function(){
    $("#received-items").find('.confirm-returns-putaway').attr("disabled",true);
    temp = $("#returns-table_info").text().split('of ')
    temp[temp.length-1]
    count = temp[temp.length-1].replace(" entries","")
    $("[href=#return-orders]").find("span").html(count);
});

  $("#received-items #receive-items").on("draw.dt",function(){
    temp = $("#receive-items_info").text().split('of ')
    temp[temp.length-1]
    count = temp[temp.length-1].replace(" entries","")
    $("[href=#po-orders]").find("span").html(count);
});


 $("#generated-po").change("tr.results td:first-child input",function() {

  if($("#generated-po tbody").find("[type=checkbox]").is(":checked"))
  {
    $("#generated-po").find(".confirm-po").prop("disabled",false);
    $("#generated-po").find(".delete-po").prop("disabled",false);
  }
  else
  {
    $("#generated-po").find(".confirm-po").prop("disabled",true);
    $("#generated-po").find(".delete-po").prop("disabled",true);
  }
  });


  $("#picklist #sortingTable ").on("draw.dt",function(){
    if ($('#picklist #sortingTable').find("th:first-child input").is(':checked')) {
         $('#picklist #sortingTable tbody input[type="checkbox"]').prop('checked',true);
    }
  });


  $( "#generated-po" ).on('click', '.confirm-po', function( event ) {
    $('.loading').removeClass('display-none');
    event.preventDefault();
    var data = '';
    var checked = $(this).parent("div").parent("div").find("input:checked")
    $.each(checked, function(index, obj) {
        if (data == "") {
            data = $(obj).parent().parent().find("td").eq(1).html() + "=" + $(obj).val()
        }
        else {
            data = data + "&" + $(obj).parent().parent().find("td").eq(1).html() + "=" + $(obj).val()
        }
        });
    var table = $('#sortingTable').DataTable();
    $('#po-modal.modal').empty();
    if(confirm("Are you sure to Confirm PO"))
    {
        $.ajax({url: '/confirm_po1?' + data,
                'success': function(response) {
            $('#po-modal.modal').append(response);
            $('#po-modal.modal').modal();

            $.each(checked, function(index, obj) {
                table.row($("tr[data-id=" + $(obj).attr("name") + "]")).remove().draw( false );
            });
            }});
    }
  $('.loading').addClass('display-none');
  });


  $( "#generated-po" ).on('click', '.delete-po', function( event ) {
    event.preventDefault();
    var data = '';
    var checked = $(this).parent("div").parent("div").find("input:checked")
    $.each(checked, function(index, obj) {
        if (data == "") {
            data = $(obj).parent().parent().find("td").eq(1).html() + "=" + $(obj).val()
        }
        else {
            data = data + "&" + $(obj).parent().parent().find("td").eq(1).html() + "=" + $(obj).val()
        }
        });
    var table = $('#sortingTable').DataTable();
    var confirm_delete =  confirm("Are you sure you want to delete PO ?");
    if(confirm_delete){
    $.ajax({url: '/delete_po_group?' + data,
            'success': function(response) {

           $.each(checked, function(index, obj) {
             table.row($("tr[data-id=" + $(obj).attr("name") + "]")).remove().draw( false );
          });
          }});
    }
  });


  $( "body" ).on('click', '.confirm-putaway', function( event ) {
    $('.loading').removeClass('display-none');
    event.preventDefault();
    var data = $('#putaway_confirmation').serialize();
    if(data != "" )
    {
    $.ajax({url: '/putaway_data?' + data,
            'success': function(response)
      {
            if(response == 'Updated Successfully')
            {
              $("body").find(".confirm-putaway").prop("disabled", true);
            }
            $("#receive-items").dataTable().fnReloadAjax();
            $('.loading').addClass('display-none');
            $('#putaway_confirmation').find(".insert-status").html(response);
       }});
    event.preventDefault();
    }
  });

  $( "body" ).on('click', '.confirm-returns-putaway', function( event ) {
    data = '';
    $('.loading').removeClass('display-none');
    event.preventDefault();
    checked = $('#returns-table').find(":checked");
    $.each(checked, function(index,obj)
    {
        if(!data)
        {
            data = "id=" + $(obj).attr("name") + "&zone=" + $(obj).parent().parent().find("[name=zone]").val() + "&location="
                   + $(obj).parent().parent().find("[name=location]").val() + "&quantity=" +
                     $(obj).parent().parent().find("[name=quantity]").val();
        }
        else
        {
            data = data + "&id=" + $(obj).attr("name") + "&zone=" + $(obj).parent().parent().find("[name=zone]").val() + "&location="
                   + $(obj).parent().parent().find("[name=location]").val() + "&quantity=" +                                                                         $(obj).parent().parent().find("[name=quantity]").val();

        }

    });
    if(data != "" )
    {
	$.ajax({url: '/returns_putaway_data?' + data,
		'success': function(response)
	        {
		    $("#returns-table").dataTable().fnReloadAjax();
                    if(response == "Updated Successfully")
                    {
		      $('.top-right').notify({
		       	message: { text : response },
			type: 'success',
			fadeOut: { enabled : true, delay: 6000 },
		    }).show();
                    }
                    else
                    {
                      $('.top-right').notify({
                        message: { text : response },
                        type: 'danger',
                        fadeOut: { enabled : true, delay: 6000 },
                    }).show();
                    }
                    
             }});
       }
    event.preventDefault();
    $('.loading').addClass('display-none');
  });

  $("body").on('click', '#confirm_quality_check .confirm-quality', function( event ) {
    $('.loading').removeClass('display-none');
    event.preventDefault();
    data = $("body").find("#confirm_quality_check").serialize()
    if(data != "" )
    {
    data = data + "&qc_scan=" + JSON.stringify(scan_data)
    $.ajax({url: '/confirm_quality_check/',
            method: 'POST',
            data: data,
            'success': function(response)
      {
            $("#quality-check").dataTable().fnReloadAjax();
      $('.loading').addClass('display-none');
       $("body").find(".insert-status").html(response).show();
       if( response == "Updated Successfully")
        {
            $("body").find(".confirm-quality").prop("disabled", true);
            $("body").find(".inb-putaway").removeClass("display-none");
        }
       }});
    event.preventDefault();
    }
    else
    {
    $('.top-right').notify({
            message: { text: "Please make sure that check box is checked in" },
            type: 'danger',
            fadeOut: { enabled: true, delay: 6000 },
            }).show();
    event.preventDefault();
    }
  });


  $( "body" ).on('click', '#grn-form .save-po', function( event ) {
    event.preventDefault();
    $('.loading').removeClass('display-none');
    var emp_test = false
    var data = '';
    var input_data = $('#grn-form').find('#receive_quantity');

    $.each(input_data, function(index, obj) {
        var parent_id = $(obj).parent().parent().attr('id')
        if (data == "") {
            if(!($(obj).val())) {
              emp_test = true 
            }
            data = parent_id + "=" + $(obj).val();
        }
        else {
            if(!($(obj).val())) {
                emp_test = true 
            }
            data = data + "&" + parent_id + '=' + $(obj).val();
        }
        });
    $.ajax({url: '/update_putaway?' + data,
            'success': function(response) {
            $("#grn-form").find(".insert-status").html(response).show();
        $("#confirmed").dataTable().fnReloadAjax();
        $('.loading').addClass('display-none');
          }});
    $('.loading').addClass('display-none');
  });

  $("#generated-po").on("click", "td:not('.sorting_1')", function(event) {
    event.preventDefault();
    var data_id = $(this).parent().find('td').eq(1).html();
    $('#po-modal').attr("style","");
    $.ajax({url: '/generated_po_data?data_id=' + data_id,
            'success': function(response) {
                $('#po-modal').empty();
                $('#po-modal').append(response);
                $("#po-modal").modal();
            }});
  });


  $("#confirmed-po").find("#confirmed").on("click", "td tr:not('.first') td:not(:nth-child(5))", function(event) {
    event.preventDefault();
    var field_data = $(this).parent().find('td').last().prev().prev().text();
    var wms_code = $(this).parent().find('td').first().text();
    if(!wms_code)
    {
      wms_code = $(this).parent().find('td').first().find('input').val();
    }
    var order_id = $(this).parent().parent().parent().parent().parent().prev().attr('id');
    if ($(this).parent().find('input:not("[name=wms_code]")').length == 0) {
      $(this).parent().find('td').last().prev().prev().html('<input type="text" name="' + order_id + '-' + wms_code + '" class="smallbox numvalid" value="' +   field_data + '" style="text-align: center;" id="receive_quantity">')
    }
    if($(this).parent().find('td').last().prev().prev().find('input'))
    {
      $("#confirmed-po").find('button[type="submit"]').attr("disabled",false);
    }
  });

  $("body").on("click", ".print-po", function(e) {
    var content = $(this).closest("form").clone();
    e.preventDefault();
    content.find(".modal-footer").remove();

    var mywindow = window.open('', 'PO', 'height=400,width=600');
    var content = '<html><head><title>PO</title>' + '<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />' + '<link rel="stylesheet" type="text/css" href="/static/css/page.css" />' + '</head><body>' + content.html() + '</body></html>';

    mywindow.document.write(content);

    mywindow.document.close(); // necessary for IE >= 10
    mywindow.focus(); // necessary for IE >= 10

    mywindow.print();
    mywindow.close();

    return true;
  });

  $("body").on("click", "#putaway_confirmation .print", function(e) {
    var content = $(this).closest("form").find('.modal-body').clone();
    e.preventDefault();
    content.find(".modal-footer").remove();
    content.find('input').css({'border':'0px', 'backgroundColor':'transparent' })
    var mywindow = window.open('', 'PO', 'height=400,width=600');
    mywindow.document.write('<html><head><title>Putaway Confirmation</title>');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/theme.css" />');
    mywindow.document.write('</head><body><h4 style="text-align: center">Putaway Confirmation<h4/>');
    mywindow.document.write(content.html());
    mywindow.document.write('</body></html>');

    mywindow.document.close(); // necessary for IE >= 10
    mywindow.focus(); // necessary for IE >= 10

    mywindow.print();
    mywindow.close();

    return true;
  });

  $("body").on("click", ".print-grn", function() {
    var content = $(this).closest("form").clone();
    content.find(".modal-footer").remove();

    var mywindow = window.open('', 'GRN', 'height=400,width=600');
    mywindow.document.write('<html><head><title>Goods Receipt Note</title>');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
    mywindow.document.write('</head><body>');
    mywindow.document.write(content.html());
    mywindow.document.write('</body></html>');

    mywindow.document.close(); // necessary for IE >= 10
    mywindow.focus(); // necessary for IE >= 10

    mywindow.print();
    mywindow.close();

    return true;
  });

  $( "body" ).on("submit", "#update-po", function( event ) {
    $('.loading').removeClass('display-none');
    event.preventDefault();
    var values = $(this).serialize();
    var this_data = $(this);

    wms_code = $(this).find("input[name=wms_code]").val();
    quant = $(this).find("input[name=order_quantity]").val();
    var correct = true;
    $('input[name=wms_code]').each(function(){
    var $wms = $(this);
    if ($wms.val() === '')
    {
    }
    else
    {
    var check = $wms.parent().parent().find("input[name=order_quantity]");
      if(check.val() == '' || check.val() == '0')
      {
      check.parent('div').addClass('has-error');
      correct = false
      }
      else
      {
      check.parent('div').removeClass('has-error');
      }
    }
    });
    if(wms_code != "" && quant != "")
    {
    if(correct == true)
    {
        $.ajax({url: '/validate_wms?' + values,
                  'async': false,
                  'success': function(response) {
                    status = response
               }});
    if(status == 'success' || confirm(status + "\n Do you want to continue"))
    {
    $.ajax({url: '/modify_po_update?' + values,
            'success': function(response) {
         this_data.find(".insert-status").html(response);
        $("#update-po .btn-primary").attr('disabled','true')
      $("#generated-po #sortingTable").dataTable().fnReloadAjax();
    }});
    }
    $('.loading').addClass('display-none');
    }
    else
    {
    this_data.find(".insert-status").html("Missing Required Fields");
    $('.loading').addClass('display-none');
    event.preventDefault();
    }
    }
    else
    {
    wms1 = $(this).find("#wms1");
    ord1 = $(this).find("#quant1");
    if(wms1.val() == "")
    {
    wms1.parent('div').addClass('has-error');
    }
    else
    {
    ord1.parent('div').removeClass('has-error');
    }
    if(ord1.val() == "")
    {
    ord1.parent('div').addClass('has-error');
    }
    else
    {
    ord1.parent('div').removeClass('has-error');
    }
    this_data.find(".insert-status").html("Missing Required Fields");
    $('.loading').addClass('display-none');
    event.preventDefault();
    }
    event.preventDefault();
    $('.loading').addClass('display-none');
  });

  $("body").on("click","#po-conf-form",function(event){

    $('.loading').removeClass('display-none');
    var values = $("#update-po").serialize();
    var this_data = $("#update-po");

    wms_code = $(this).find("input[name=wms_code]").val();
    quant = $(this).find("input[name=order_quantity]").val();
    var correct = true;
    $('input[name=wms_code]').each(function(){
    var $wms = $(this);
    if ($wms.val() === '')
    {
    }
    else
    {
    var check = $wms.parent().parent().find("input[name=order_quantity]");
      if(check.val() == '' || check.val() == '0')
      {
      check.parent('div').addClass('has-error');
      correct = false
      }
      else
      {
      check.parent('div').removeClass('has-error');
      }
    }
    });
    if(wms_code != "" && quant != "")
    {
    if(correct == true)
    {
        $.ajax({url: '/validate_wms?' + values,
                  'async': false,
                  'success': function(response) {
                    status = response
               }});
    if(status == 'success' || confirm(status + "\n Do you want to continue"))
    {
        if(confirm("Are you sure to Confirm PO"))
        {
            $.ajax({url: '/confirm_po?' + values,
                    'success': function(response) {
            $("#generated-po #sortingTable").dataTable().fnReloadAjax();
            $("#po-modal").empty();
            $("#po-modal").append(response);
                    }});
        }
    }
    }
    }
    $('.loading').addClass('display-none');
 });

  $("body").on("click","#po-conf-form1",function(e){
    e.stopImmediatePropagation();
    $('.loading').removeClass('display-none');
    var values = $("#add_po").serialize();
    var this_data = $("#add_po");

    wms_code = $("#add_po").find("input[name=wms_code]").val();
    quant = $("#add_po").find("input[name=order_quantity]").val();
    var correct = true;
    $('input[name=wms_code]').each(function(){
    var $wms = $(this);
    if ($wms.val() === '')
    {
    }
    else
    {
    var check = $wms.parent().parent().find("input[name=order_quantity]");
      if(check.val() == '' || check.val() == '0')
      {
      check.parent('div').addClass('has-error');
      correct = false
      }
      else
      {
      check.parent('div').removeClass('has-error');
      }
    }
    });
    if(wms_code != "" && quant != "")
    {
    if ( correct == true)
    {
        $.ajax({url: '/validate_wms?' + values,
                  'async': false,
                  'success': function(response) {
                    status = response
               }});
    if(status == 'success' || confirm(status + "\n Do you want to continue"))
    {
        if(confirm("Are you sure to Confirm PO"))
        {
            $.ajax({url: '/confirm_add_po?' + values,
                    'success': function(response) {
                    if(response.search('Invalid') == 0)
                    {
                    $("body").find(".insert-status").html(response).show();
                    }
                    else
                    {
                    $("#po-modal").empty();
                    $("#po-modal").append(response);
                    }
                }});
         }
    }
    $('.loading').addClass('display-none');
    }
    else
    {
    this_data.find(".insert-status").html("Missing Required Fields");
    $('.loading').addClass('display-none');
    e.preventDefault();
    }
    }
    else
    {
    wms1 = $("#add_po").find("#wms1");
    ord1 = $("#add_po").find("#quant1");
    if(wms1.val() == "")
    {
    wms1.parent('div').addClass('has-error');
    }
    else
    {
    ord1.parent('div').removeClass('has-error');
    }
    if(ord1.val() == "")
    {
    ord1.parent('div').addClass('has-error');
    }
    else
    {
    ord1.parent('div').removeClass('has-error');
    }
    this_data.find(".insert-status").html("Missing Required Fields");
    $('.loading').addClass('display-none');
    }
    e.preventDefault();
 });

  $( "body" ).on("submit", "#po-received", function( event ) {
    $('.loading').removeClass('display-none');
    event.preventDefault();
    var values = $(this).serialize();
    var this_data = $(this);
    var headers = $("#sortingTable").find("th");
    $.ajax({url: '/update_receiving?' + values,
            'success': function(response) {
         this_data.find(".insert-status").html(response).show();
      $("#confirmed").dataTable().fnReloadAjax();
    $('.loading').addClass('display-none');
            }});

  });
  $( "body" ).on('click', '.generate-grn', function( event ) {
    event.preventDefault();
    var post_data = '';
    var data = $('#grn-form').find('input#receive_quantity');
    var siblings = data.parent().parent().siblings('tr:not(.active)').find('td:eq(2):not(:has(>input))');
    $.each(data, function(index, obj) {
        var supplier_id = $("body").find("[name=supplier_id]").val();
        var row_id = $(this).parent().parent().attr('id');
        var wms_code = $(this).parent().parent().find("[name=wms_code]").val();
        var pallet_number = $(this).parent().parent().find("[name=pallet_number]").val();
        var imei_number = $(this).parent().parent().find("[name=imei_number]").val();
        if(pallet_number == undefined)
        {
            pallet_number = ''
        }
        if(imei_number == undefined)
        {
            imei_number = ''
        }
        else
        {
            imei_number = imei_number.split("\n");
        }
        if(row_id == undefined)
          {
            wms_code = $(obj).parent().parent().find("input[name='wms_code']").val();
            po_quantity = $(obj).parent().parent().find("input[name='po_quantity']").val();
            price = $(obj).parent().parent().find("input[name='price']").val();
            row_id = $(this).parent().parent().parent().find('tr.active').next().attr('id');
          }
          else
          {
            po_quantity = ''
            price = ''
          }

        if(wms_code == undefined)
        {
            wms_code = ''
        }
        if (post_data == "") {
            if ($(obj).val() != 0)
            {
              post_data = "id=" + row_id + "&quantity=" + $(obj).val() + '&wms_code=' + wms_code + '&po_quantity=' + po_quantity + '&price=' +price + '&supplier_id=' + supplier_id + '&pallet_number=' + pallet_number + '&imei_number=' + imei_number;
            }
        }
        else {
            if($(obj).val() != 0) {
            post_data = post_data + "&id=" + row_id + "&quantity=" + $(obj).val() + '&wms_code=' + wms_code + '&po_quantity=' + po_quantity + '&price=' + price + '&supplier_id=' + supplier_id + '&pallet_number=' + pallet_number + '&imei_number=' + imei_number;
          }
        }
    });

    if(post_data && confirm("Are you sure to Generate GRN"))
    {
    $.ajax({url: '/confirm_grn?' + post_data,
            'success': function(response) {
            if(response.search('Invalid') == -1 && response.search('already') == -1)
            {
            lr_data = $("body").find("#grn-form").serialize();
            $.ajax({url:'/add_lr_details/?'+ lr_data,
                    success:function(response){

       }
    });
     $("#po-modal").empty()
     $('#po-modal').append(response);
    $("#confirmed").dataTable().fnReloadAjax();
        }
        else
        {
            $("#grn-form").find(".insert-status").html(response).show();
        }

          }});
    $("#po-modal").modal();
    }
    else
    {
        $("#grn-form").find(".insert-status").html("Please Update the received quantity").show();
    }
  });


  $("#receive-items").on("click","tr tr td:not(:first-child,:last-child)", function(event){
    event.preventDefault();
    var location_val = $(this).parent().find('td').last().prev().prev().prev().text();
    var quantity_val = $(this).parent().find('td').last().prev().text();
    var wms_code = $(this).parent().find('td').first().next().text();
    var order_id = $(this).parent().parent().parent().parent().parent().prev().attr('id');
    if ($(this).find('input').length == 0)
    {
      if(location_val != "")
      {
        $(this).parent().find('td').last().prev().prev().prev().html('<input type="text" name="' + order_id +'-'+wms_code+ '" class="smallbox"  value="' + location_val + '" style="text-align: center;">');
        $(this).parent().find('td').last().prev().html('<input type="text" name="' + order_id +'-'+wms_code+ '" class="smallbox put_quantity numvalid" Value="' + quantity_val + '"style="text-align: center;"><input type="hidden" value="'+ quantity_val + '" name="h_quantity">');
      }
    }
  });

  $("body").on("keyup", ".put_quantity", function(){
   orig_quan = $(this).parent().parent().find("input.put_quantity").parent().prev().html();
   if(Number(orig_quan) > Number($(this).val()))
   {
     $(this).parent().parent().find("td:last-child").html("<img src='/static/img/details_open.png'>");
   }
   else
   {
     $(this).parent().parent().find("td:last-child").html("");
   }
});

  $("body").on("click", ".receive-toggle > td:last-child img", function(event){
    event.preventDefault();
    img_state = $(this).attr("src");
    dup_con = $(this).parent().parent().clone();
    tot_quan = 0;
    orig_quan = $(this).parent().parent().find("input.put_quantity").parent().prev().html();

    id = $(this).parent().parent().attr("id");
    $(this).parent().parent().parent().find('.receive-toggle').each(function(index,value){
      p_id = $(value).attr("id");
      if(Number(id) == Number(p_id)){
        tot_quan = tot_quan + Number($(value).find(".put_quantity").val());
      }
    });
    dif_quan = Number(orig_quan) - Number(tot_quan);
    $(dup_con).find("input.put_quantity").attr('value', dif_quan);
    if(img_state.search('open') != -1) {
      if(Number(orig_quan) > Number(tot_quan)){
        $(this).attr("src","/static/img/details_close.png");
        $(this).parent().parent().parent().parent().append("<tr id='" + id + "' class='receive-toggle'>"+ dup_con.html() + "</tr>");
      }
    }
    else {
        $(this).parent().parent().remove();
    }
  });

  $("body").on("keyup","#putaway_confirmation .put_quantity",function(){
      id = $(this).parent().parent().attr("id");
      tot_quan = 0
      orig_quan = $(this).parent().prev().html();
      $("#putaway_confirmation").find(".put_quantity").each(function(index,value){
        p_id = $(value).parent().parent().attr("id");
        if(Number(id) == Number(p_id)){
          tot_quan = tot_quan + Number($(value).val());
        }
      });
      if(Number(tot_quan) > Number(orig_quan))
      {
        diff = Number(tot_quan) - Number(orig_quan)
        $(this).val(Number($(this).val()) - diff);
        $("body").find(".insert-status").html("Putaway Quantity should be less than or equal to Original quantity").show();
      }
      else {
        $("body").find(".insert-status").html("");
      }
     $('.loading').addClass('display-none');
});


  $("#generated-po #sortingTable ").on("draw.dt",function(){
   var checkboxes = $("#generated-po tr.results td:first-child ").find("input[type='checkbox']"),
   submitButt = $("#generated-po").find("button[type='submit']");
   submitButt.attr("disabled", !checkboxes.is(":checked"));
});

   //raise po if any change in check box
  $("#generated-po").on("change","tr.results td:first-child input",function(){
   var checkboxes = $("#generated-po tr.results td:first-child ").find("input[type='checkbox']"),
   submitButt = $("#generated-po").find("button[type='submit']");
   checkboxes.click(function()
   {
   submitButt.attr("disabled", !checkboxes.is(":checked"));
   });
  });

  $("#generated-po").on("change","[type=checkbox]",function() {

  if($("#generated-po").find("[type=checkbox]").is(":checked"))
  {
    $("body").find(".confirm-po").prop("disabled",false);
    $("body").find(".delete-po").prop("disabled",false);
  }
  else
  {
    $("body").find(".confirm-po").prop("disabled", true);
    $("body").find(".delete-po").prop("disabled", true);
  }

});


 $("#returns-table").on("change","[type=checkbox]",function(e) {

  if($("#returns-table").find("input[type=checkbox]").is(":checked"))
  {
    $(".confirm-returns-putaway").prop("disabled",false);
  }
  else
  {
    $(".confirm-returns-putaway").prop("disabled",true);
  }

});


  $("body").on("click","#delete-sales",function(e){
     e.preventDefault();
     $(this).parent().parent().remove();
     var tr_length = $("#return-sales-form").find('tr:not(.active,.returns-data)').length;
      if(tr_length == 0)
      {
          $('#sales-orders').addClass('display-none');
      }
   });

  $("body").on("click","#add-receive-po",function(e){
    e.stopImmediatePropagation();
    var id = $(this).parent().parent().attr("id");
    var choice = $(this).attr("src");
    var row_add = 'true'
    if(choice.search('open') != -1)
    {
      if (id != undefined)
  {
      rec_quan = 0
      pal_no = $(this).parent().parent().find('[name=pallet_number]').val();
      po_quan = $(this).parent().parent().find("td:eq(1)").html();
      $(this).parent().parent().parent().find("input#receive_quantity").each(function(index,value){
        p_id = $(value).parent().parent().attr("id");
        if(Number(id) == Number(p_id)){
          rec_quan = rec_quan + Number($(value).val());
        }
      });

      diff = Number(po_quan) - Number(rec_quan)
      if(pal_no && diff>0)
  {
      $(this).parent().parent().after("<tr id=" + id + ">" + $(this).parent().parent().html() + "</tr>");
      $(this).attr("src","/static/img/details_close.png");
      row_add = 'false';
  }
  }
      if(row_add == 'true')
  {
      $(this).attr("src","/static/img/details_close.png");
      $(this).parent().parent().after('<tr><td><input type="text" style="width:90px" name="wms_code"></td><td><input type="text" name="po_quantity" class="smallbox"></td><td><input type="text" name="received_quantity" class="smallbox" id="receive_quantity"></td><td><input type="text" name="price" class="smallbox"></td><td><img id="add-receive-po" src="/static/img/details_open.png"></td></tr>');
      if($(this).parent().parent().parent().find("th").text().search("Pallet") >= 0)
      {
           $(this).parent().parent().next().find("#receive_quantity").parent().before('<td><input type="text" name="pallet_number" class="smallbox"></td>')
      }
      if($(this).parent().parent().parent().find("th").text().search("Serial") >= 0)
      {
           $(this).parent().parent().next().find("#receive_quantity").parent().after('<td><textarea name="imei_number" rows="1" id="scan_imei"></textarea></td>')
      }
  }
    }
    else
    {
      if (id == undefined || $(this).parent().parent().parent().find("tr#" + id).length > 1)
      {
        $(this).parent().parent().remove();
        if($("body").find("#grn-table tr#" + id).length == 1)
        {
            $("body").find("#grn-table tr#" + id).find("img").attr("src","/static/img/details_open.png")
        }
      }
    }
  });

$('body').on("click", '#confirmed tr td', function() {
    var data_id = $(this).parent().attr('id');
    if(data_id){
    $.fn.get_supplier_data(data_id);
    }
  });

  $('body').on("click", '#quality-check tr td', function() {
    var data_id = $(this).parent().attr('id');
    var context = this;
    $.fn.quality_check_data(data_id)
  });

  $( "body" ).on('click', '.close-po', function( event ) {
    event.preventDefault();
    var post_data = '';
    var data = $('#grn-form').find('input#receive_quantity');
    var siblings = data.parent().parent().siblings('tr:not(.active)').find('td:eq(2):not(:has(>input))');
    $.each(data, function(index, obj) {
        var supplier_id = $("body").find("[name=supplier_id]").val();
        var row_id = $(this).parent().parent().attr('id');
        var wms_code = $(this).parent().parent().find("[name=wms_code]").val();
        var new_sku = 'false'
        if(row_id == undefined)
          {
            wms_code = $(obj).parent().parent().find("td").eq(0).find("input[name='wms_code']").val();
            po_quantity = $(obj).parent().parent().find("td").eq(1).find("input[name='po_quantity']").val();
            price = $(obj).parent().parent().find("td").eq(3).find("input[name='price']").val();
            row_id = $(this).parent().parent().parent().find('tr.active').next().attr('id');
            new_sku = 'true';
          }
          else
          {
            po_quantity = ''
            price = ''
          }

        if(wms_code == undefined)
        {
            wms_code = ''
        }
        if (post_data == "") {
              post_data = "id=" + row_id + "&quantity=" + $(obj).val() + '&wms_code=' + wms_code + '&po_quantity=' + po_quantity + '&price=' + price + '&supplier_id=' + supplier_id + '&new_sku=' + new_sku;
        }
        else {
            post_data = post_data + "&id=" + row_id + "&quantity=" + $(obj).val() + '&wms_code=' + wms_code + '&po_quantity=' + po_quantity +  '&price=' + price + '&supplier_id=' + supplier_id + '&new_sku=' + new_sku;
        }
    });
    if(confirm("Are you sure to Close PO"))
    {
        $.ajax({url: '/close_po?' + post_data,
                'success': function(response) {
                if(response.search('Invalid') == -1)
                {
                    lr_data = $("body").find("#grn-form").serialize();
                    $.ajax({url:'/add_lr_details/?'+ lr_data,
                            success:function(response){
                        if( response == 'success'){
                            $('.top-right').notify({
                            message: { text: "LR Details added successfully" },
                            type: 'success',
                            fadeOut: { enabled: true, delay: 6000 },
                            }).show();
                                    }
                        else{
                            $('.top-right').notify({
                            message: { text: "Error while updating LR details" },
                            type: 'danger',
                            fadeOut: { enabled: true, delay: 6000 },
                            }).show();
                        }
                    }});
            }

                $("#grn-form").find(".insert-status").html(response).show();
                $("#confirmed").dataTable().fnReloadAjax();
            }});
    }
  });

  $('body').on("click", '#order-returns .scan-returns', function(e) {
    e.preventDefault();
    $('#sales-toggle').empty();
    $.ajax({url: '/get_returns_page/',
            'success': function(response) {
                $('#sales-toggle').append(response);
                $('#sales-toggle').modal();
                $("#myModal").modal();
            }});
  });

  scanned_returns = []
  $("body").on('keydown', '#confirm-returns #scan_return_id',function(e){

   $("body").find(".insert-status").html('').show();

  if(e.which == 13) {
   value = $(this).val();
   this_data = $(this);
   temp = value.split("\n");
   data_id = temp[temp.length-1]
   if(scanned_returns.indexOf(data_id) < 0)
    {
   $.ajax({url: '/check_returns?' + "return_id" + "=" + data_id,
        'success': function(response) {
            if(!(response.search('confirmed') == -1))
            {
               $("body").find(".insert-status").html(response).show();
            }
            else if(response.search('invalid') == -1)
            {
              data = JSON.parse(response);
              scanned_returns.push(data_id);
              $("body").find("#return-headers").removeClass("display-none");
              $(".table-striped").find("tr#return-headers").after("<tr id='table-field' class='returns-row'><td>" + data.return_id + "</td><td>" + data.sku_code +
                                       "</td><td>" + data.sku_desc + "</td><td>" + data.ship_quantity + "</td><td>"
                                       +  data.return_quantity +
                                       "</td><td><input type='hidden' name='id' value='" + data.id + "'>" +
                                       "<input type='hidden' name='shipping'><input type='hidden' name='sku_code'>" +
                                       "<input type='hidden' name='return'><input type='hidden' name='track_id'>" +
                                       "<input type='text' name='damaged' class='numvalid smallbox'></td></tr>")
            }
            else {
                if(confirm("Return Id not found.Do you want to add it"))
                {
                   $("body").find("#return-headers").removeClass("display-none");
                   fields_clone = $("#scan-return-fields").clone();
                   fields_clone.find("td:first").html(data_id);
                   fields_clone.find("td:last").append("<input type='hidden' name='id' value=''>");
                   fields_clone.find("td:last").append("<input type='hidden' name='track_id' value='" + data_id + "'>");
                   $(".table-striped").find("tr#return-headers").after("<tr id='table-field' class='returns-row'>" + fields_clone.html() + "</tr>");
                }
            }

   } });
    }
    this_data.val("");
  }

  });

  $("body").on('keydown', '#return_sku_code',function(e){

   $("body").find(".insert-status").html('').show();

  if(e.which == 13) {
   value = $(this).val();
   this_data = $(this);
   temp = value.split("\n");
   data_id = temp[temp.length-1]
   if(scanned_returns.indexOf(data_id) < 0)
    {
   $.ajax({url: '/check_sku?' + "sku_code" + "=" + data_id,
        'success': function(response) {
            var update_status = false;
            if(response.search('confirmed') == -1)
            {  
               $("body").find(".insert-status").html(response).show();
            }
            else {
              var sku_node = $(".table-striped").find('.returns-row');
              $.each(sku_node, function(index, obj) {
                var return_id = $(obj).find('td:first').html();
                if (!return_id) {
                  var sku = $(obj).find('input[name=sku_code]').val();
                  if (sku==data_id) {
                      var return_quantity = $(obj).find('input[name=return]').val();
                      if (return_quantity) {
                        return_quantity = parseInt(return_quantity, 10);
                        return_quantity = return_quantity + 1;
                        $(obj).find('input[name=return]').val(return_quantity);
                        update_status = true;
                        return false;
                      }
                  }
                }
              });
              if (!update_status) {
                $("body").find("#return-headers").removeClass("display-none");
                $(".table-striped").find("tr#return-headers").after('<tr id="table-field" class="returns-row">' +
                                '<td></td>' +
                                '<td><input type="text" class="mediumbox" name="sku_code" value="' + data_id + '"></td>' +
                                '<td><input type="text" name="sku_desc"></td>' +
                                '<td><input type="text" class="smallbox numvalid" name="shipping"></td>' +
                                '<td><input type="text" class="smallbox numvalid" name="return" value="1"></td>' +
                                '<td><input type="text" class="smallbox numvalid" name="damaged"><input type="hidden" value="" name="id"><input type="hidden" value="" name="track_id"></td></tr>')
            }
            }

   } });
    }
    this_data.val("");
  }

  });

    $("body").on("click","#confirm-returns .close",function() {
      scanned_returns = []
    });

  $("body").on("click","#confirm-sales",function( event ) {
    $('.loading').removeClass('display-none');
    values = $("tr#table-field :input").serialize();
    if(values)
    {
        $.ajax({url: '/confirm_sales_return?' + values,
                'success': function(response) {
            $("body").find(".insert-status").html(response).show();
            if(response == 'Updated Successfully')
            {
                $("body").find("#confirm-sales").attr("disabled","true");
            }
            $("#sortingTable").dataTable().fnReloadAjax();
                }});
    }
    $('.loading').addClass('display-none');
   });

  $("body").on('keydown', '#grn-form #scan_sku',function(e){

  if(e.which == 13) {
   value = $(this).val();
   this_data = $(this);
   temp = value.split("\n");
   data_id = temp[temp.length-1]
   var wms_tr = $("#grn-form").find("td:nth-child(1)").filter(function() {
    text = $(this).text().trim()
    return text == data_id;
   }).closest("tr");

   if(wms_tr.length != 0)
   {
       wms_tr.find('input#receive_quantity').focus();
       this_data.val("");
   }
   else
   {
      alert("SKU is not in this PO list.You can add sku code by pressing the plus button");
   }
  }


  });

  $("body").on('keydown', '#grn-form [name=wms_code]',function(e){

  if(e.which == 13) {
    $(this).parent().next().find("input").focus();
  }

  });

  $("body").on('keydown', '#putaway_confirmation [name=loc]',function(e){

  if(e.which == 13) {
    $(this).parent().parent().find("[name=quantity]").focus();
  }

  });

  $("#returns-table").on("keyup", "[name=quantity]",function(e){
     e.preventDefault();
     user_val = Number($(this).val());
     orig_val = Number($(this).parent().find('[name=hide_quantity]').val());
     if(user_val > orig_val)
     {
        $('.top-right').notify({
          message: { text: "Quantity must be less than or equal to the Returned quantity" },
          type: 'danger',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
        $(this).val(orig_val);
         
     }
  });

  $("body").on('keydown', '#scan_qc',function(e){

    data = {}
    if(e.which == 13) {
      form_id = $(this).closest("form").attr("id");
      modal = $('#po-modal1');
      if(form_id == undefined) {
        modal = $('#po-modal');
      }
      data[$(this).val()] = $(this).parent().prev().find("h5 b").text();
      if($(this).val()){
      $.ajax({url: '/check_wms_qc/',
              method: 'POST',
              data: data,
              'success': function(response) {
                   if(response.search("not found") == -1)
                   {
                       modal.empty();
                       modal.append(response);
                       modal.modal();
                       $("body").find(".insert-status").html("")
                   }
                   else {
                       if(form_id == undefined)
                       {
                           $('.top-right').notify({
                             message: { text: response },
                             type: 'danger',
                             fadeOut: { enabled: true, delay: 6000 },
                           }).show();
    
                       }
                       else {
                           $("body").find(".insert-status").html(response).show();
                       }
                   }
             } });
         $(this).val("");
     }

  }

  });

  qc_scanned = []
  $("body").on('keydown', '#scan-qc',function(e){
    this_data = $(this);
    value = this_data.val();
    temp = value.split("\n");
    data_id = temp[temp.length-1]
    if(e.which == 13)
    {
        exist_status = $.fn.validate_qc_serial(data_id);
        if(exist_status){
            $("#wms_quality_wise").find(".insert-status").html(exist_status).show();
        }
        if(!$.fn.validate_qc($("#wms_quality_wise .smallbox")) && !exist_status)
        {
            if(qc_scanned.indexOf(data_id) < 0){
                $("body .table-padding").find("button").prop("disabled", false);
                qc_scanned.push(data_id);
            }
            else{
                temp.splice( temp.indexOf(data_id), 1 )
            }
            this_data.val(temp.join('\n'));
        }
    }
  });

  scan_data = []
  $("body").on("click", ".table-padding button:not(#save-reason)",function(e){
    dict_data = {}
    serial = $("#scan-qc").val();
    temp = serial.split("\n");
    data_id = temp[temp.length-2]
    b_name = $(this).attr("name");
    row_id = $("#wms_quality_wise .table").find("tr:not('.active')").attr("id");
    dict_data[b_name] = data_id + "<<>>" + row_id + "<<>>"
    if(b_name == "accept"){
        accepted = $("#wms_quality_wise").find("tr#" + row_id + " [name=accepted_quantity]")
        value = accepted.val();
        accepted.val(Number(value) + 1);
    }
    else{
        rejected = $("#wms_quality_wise").find("tr#" + row_id + " [name=rejected_quantity]")
        value = rejected.val();
        rejected.val(Number(value) + 1);
        $("#reject_reason, #save-reason").removeClass("display-none");
        $("#scan-qc").prop("disabled", true);
    }
    scan_data.push(dict_data)
    $("body .table-padding").find("button :not(#save-reason)").prop("disabled", true);
  });

  $("body").on("click", ".table-padding #save-reason", function(e){
    reason = $(this).parent().parent().find("#reject_reason option:selected").val();
    serial = scan_data[scan_data.length-1]
    scan_data[scan_data.length-1]['reject'] = serial.reject +  reason;
    $("#scan-qc").prop("disabled", false);
    $("#reject_reason, #save-reason").addClass("display-none");
  });

    $("body").on("click","#confirm_quality_check .close, .qc-modal",function() {
      qc_scanned = []
      scan_data = []
    });

    $("body").on("click","#wms_quality_wise .save-scanned" , function(){
      $("#wms_quality_wise .table").find("tr:not('.active')").each(function(index,value){
        row_id = $(value).attr("id");
        accepted = $("#wms_quality_wise").find("tr#" + row_id + " [name=accepted_quantity]").val();
        $("#confirm_quality_check").find("tr#" + row_id + " [name=accepted_quantity]").val(accepted);
        rejected = $("#wms_quality_wise").find("tr#" + row_id + " [name=rejected_quantity]").val();
        $("#confirm_quality_check").find("tr#" + row_id + " [name=rejected_quantity]").val(rejected);
        $("#wms_quality_wise").find(".insert-status").html("Updated Successfully");
        $("#confirm_quality_check").find("tr#" + row_id).find("[name=accepted_quantity], [name=rejected_quantity]").prop("readonly", true);
      });
      
    });

    $("body").on("keyup","#wms_quality_wise .smallbox" , function(e){
      $.fn.validate_qc($(this));
    });

    $("body").on("keyup","#confirm_quality_check .smallbox" , function(e){
      $.fn.validate_qc($(this));
    });

  $('body').on("click", '#receive-items .results', function() {
    var data_id = $(this).data('id');
    var context = this;
    $('.process-toggle').empty();
    $.fn.get_received_orders(data_id);
    
  });


  $("body").on("click",".inb-putaway", function(e){
    data_id = $(this).attr("id");
    $.fn.get_received_orders(data_id);
  });

  $("body").on("click",".inb-qc", function(e){
    data_id = $(this).attr("id");
    $.fn.quality_check_data(data_id);
  });

  $("body").on("click",".inb-receive-po", function(e){
    data_id = $(this).attr("id");
    $.fn.get_supplier_data(data_id);
  });

  $("body").on("keyup","[name=search-track-order]",function(e){
    if(e.which == 13)
    {
      order_id = $(this).parent().find("[name=search-track-order]").val();
      if(order_id)
      {
        data = "order_id=" + order_id;
        $.ajax({url: '/track_orders?' + data,
                'success': function(response) {
                  $(".all-orders").addClass("display-none");
                  if(response.search("collapse") == -1)
                  {
                    $(".searched-order").html("<h5>No Orders Found</h5>");
                  }
                  else
                  {
                    $(".searched-order").html(response);
                  }
                    $(".searched-order").removeClass("display-none");
                    $(".searched-order").find(".stage").each(function(ind,obj){
                      $(obj).css("height", $(obj).parent().parent().height() + "px");
                      $(obj).KKTimeline(JSON.parse($(obj).attr('id')));
                    });

               }});
      }
    }
    if($(this).val() == '')
    {
      $(".searched-order").addClass("display-none");
      $(".all-orders").removeClass("display-none");
    }

  });

  $("body").on("click","#add_st .save-st, #update_st .save-st", function(e){
    e.preventDefault();
    form = $(this).closest('form');
    data = form.serializeArray()
    $.ajax({url: '/save_st/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $("body").find(".insert-status").html(response).show();
                if(response == 'Added Successfully'){
                    form.find("#raise-st-confirm, .save-st").prop("disabled","true");
                }
                $("#raised-st").dataTable().fnReloadAjax();
            }});
  });

  $('body').on("click", '#raised-st tr td', function() {
    var data_id = $(this).parent().attr('id');
    if(data_id){
    modal_field = $(".process-toggle:not(#po-modal1)")
    $.ajax({url: '/update_raised_st?warehouse_name=' + data_id,
            'success': function(response) {
                modal_field.html(response);
                modal_field.modal();
            }});

    }
  });

  $("body").on("click","#add_st #raise-st-confirm, #update_st #raise-st-confirm", function(e){
    e.preventDefault();
    form = $(this).closest('form');
    data = form.serializeArray()
    $.ajax({url: '/confirm_st/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $("body").find(".insert-status").html(response).show();
                if(response.search('Successfully') != -1){
                    form.find("#raise-st-confirm, .save-st").prop("disabled","true");
                }
                $("#raised-st").dataTable().fnReloadAjax();
            }});
  });


});
