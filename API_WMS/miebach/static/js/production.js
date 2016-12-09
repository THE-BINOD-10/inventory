$(document).ready(function() {

$.fn.process_material = function(this_data) {
    var form_name = this_data.closest('form').attr('id');
    var row = this_data.parent().parent().parent();
    var sku_code = row.find("[name=product_code]").val();
    var quan_data = material_data[sku_code];
    var rem_class = row.find("[name=id]").attr("class");
    var t_rows = $("#" + form_name + " ." + rem_class).parent().parent();
    var this_val = this_data.val();
    if(quan_data != undefined)
    {
        $.each(quan_data, function(key, value){
            $.each(t_rows,function(index,obj){
                if($(obj).find("[name=material_code]").val() == key){
                    $(obj).find("[name=material_quantity]").val(Number(this_val) * Number(value));
                }
            });
        });
    }


}

  $("#raise-jo").on("click",function(){
   $("#po-modal").attr("style","");
   active_id = $("#job-orders").find(".active").attr("id");
   url = '/raise_jo_toggle';
   form_id = 'raise_job_order';
   if(active_id == 'raise_rwo')
   { 
     url = '/raise_rwo_toggle'; 
     form_id = 'add_rwo';
   }
   $.ajax({url: url,
          'success': function(response) {
                $('#po-modal').html(response);
                $('#po-modal').modal();
                $("#myModal").modal();
                tr_row = $("tr#raise-jo-row").html();
                $("#" + form_id + " .active").after("<tr>" + tr_row + "</tr>");
            }});
  });

  $.fn.delete_jo = function(data) {
   $.ajax({url: '/delete_jo/',
           method: 'POST',
           data: data,
        'success': function(response) {
        $("#sortingTable").dataTable().fnReloadAjax();
   } });

  }


  $("body").on("click", "#raise_job_order #add_row, #add_rwo #add_row", function(e){
    row =  $(this).parent().parent();
    var data = {}
    data['job_code'] = $("[name=job_code]").val();
    if($(this).attr("src").search("open") != -1 && row.find("[name=product_code]").val())
    {
        row.after("<tr>" + $("body #raise-jo-row").html() + "</tr>");
        row.find("[name=product_code]").attr("readonly", "true");
        row.next().find("[name=product_code]").val(row.find("[name=product_code]").val());
        row.next().find("[name=product_code]").attr("type", "hidden");
        row.next().find("[name=product_quantity]").attr("type", "hidden");
        $(this).attr("src","/static/img/details_close.png");
    }
    else if($(this).attr("src").search("close") != -1){
        if(row.find("[name=product_code][type=hidden]").length == 0)
        {
            sku_code = row.find("[name=product_code]").val();
            $("form tr [name=product_code][value=" + sku_code + "]").parent().parent().remove();
            row.remove();
            data['rem_id'] = row.find("[name=id]").val();
            data['wms_code'] = sku_code;
            if(data['rem_id']){
                $.fn.delete_jo(data);
            }
            if($("form tr:not(.active,#raise-jo-row)").length == 0)
            {
                tr_row = $("tr#raise-jo-row").html();
                $("#raise_job_order .active").after("<tr>" + tr_row + "</tr>");
            }
        }
        else {
            row.remove();
            data['rem_id'] = row.find("[name=id]").val();
            data['wms_code'] = '';
            if(data['rem_id']){   
                $.fn.delete_jo(data);
            }

        }
    }
  });

  $('body').on("click", '#raise_job_order .add-prod-sku, #add_rwo .add-prod-sku', function() {
      new_row = $('body').find('tr#raise-jo-row').clone();
      $("body").find("#raise-jo-row").parent().append("<tr>" + new_row.html() + "</tr>");

  });

  $("body").on("click","#raise_job_order .save-jo", function(e){
    data = $("form:not(#raise-jo-row)").serializeArray()
    $.ajax({url: '/save_jo/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $("body").find(".insert-status").html(response).show();
                if(response == 'Added Successfully'){
                    $.fn.make_disable($("#raise_job_order"));
                    $("#raise_job_order").find(".save-jo,.confirm-jo").prop("disabled","true");
                }
                $("#sortingTable").dataTable().fnReloadAjax();
            }});
  });


  $("#raise_jo").on("click", "td:not(:first-child)", function(event) {
    event.preventDefault();
    var data_id = $(this).parent().find('td').eq(1).html();
    $("#po-modal").attr("style","");
    $.ajax({url: '/generated_jo_data?data_id=' + data_id,
            'success': function(response) {
                $('#po-modal').empty();
                $('#po-modal').append(response);
                $("#po-modal").modal();
            }});
  });

  $("body").on("click","#raise_job_order .confirm-jo", function(e){
    data = $("form:not(#raise-jo-row)").serializeArray()
    $.ajax({url: '/confirm_jo/',
            method: 'POST',
            data: data,
            'success': function(response) {
                if(response.search('<tbody>') == -1){
                    $("body").find(".insert-status").html(response).show();
                }
                else {
                    $('#po-modal').empty();
                    $('#po-modal').append(response);
                    $("#po-modal").modal();
                    $("#raise_job_order").find(".save-jo,.confirm-jo").prop("disabled","true");
                }
                $("#sortingTable").dataTable().fnReloadAjax();
            }});
  });

    $('#raise_jo #sortingTable').find("th:first-child").unbind("click.DT");

    $("#raise_jo #sortingTable ").on("draw.dt",function(){
      if ($('#raise_jo #sortingTable').find("th:first-child input").is(':checked')) {
           $('#raise_jo #sortingTable tbody input[type="checkbox"]').prop('checked',true);
      }
    });



 $("#raise_jo #sortingTable").change("tr.results td:first-child input",function() {

  if($("#sortingTable tbody").find("[type=checkbox]").is(":checked"))
  {
    $("#raise_jo").find(".confirm-jo1, .delete-jo1").prop("disabled",false);
  }
  else
  {
    $("#raise_jo").find(".confirm-jo1, .delete-jo1").prop("disabled",true);
  }

  });

  $("body").on("click","#raise_jo .confirm-jo1", function(e){
    data = $("#sortingTable tbody").find(":checked").serializeArray();
    $("#po-modal").attr("style",""); 
    $.ajax({url: '/confirm_jo_group/',
            method: 'POST',
            data: data,
            'success': function(response) {
                if(response.search('<tbody>') == -1){
                    $('.top-right').notify({
                      message: { text: response },
                      type: 'danger',
                      fadeOut: { enabled: true, delay: 6000 },
                    }).show();

                }
                else {
                    $("#raise_jo").find(".delete-jo1,.confirm-jo1").prop("disabled","true");
                    $('#po-modal').empty();
                    $('#po-modal').append(response);
                    $("#po-modal").modal();
                }
                $("#sortingTable").dataTable().fnReloadAjax();
            }});
  });

  $("body").on("click","#raise_jo .delete-jo1", function(e){
    data = $("#sortingTable tbody").find(":checked").serializeArray();
    $.ajax({url: '/delete_jo_group/',
            method: 'POST',
            data: data,
            'success': function(response) {
                if(response == 'Deleted Successfully'){
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
                $("#sortingTable").dataTable().fnReloadAjax();
                $("#raise_jo").find(".delete-jo1,.confirm-jo1").prop("disabled","true");
            }}); 
  });

  $("#raw-picklist").on("click", "tr td:not(.dataTables_empty)", function(event) {
    event.preventDefault();
    data = {}
    data['data_id'] = $(this).parent().attr("data-id");
    $("#po-modal").attr("style","");
    $.ajax({url: '/view_rm_picklist/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $('#po-modal').empty();
                $('#po-modal').append(response);
                $("#po-modal").modal();
            }});
  });

  $("body").on("click", ".print-jo", function(e) {
    var content = $(this).closest("form").clone();
    e.preventDefault();
    content.find(".modal-footer").remove();

    var mywindow = window.open('', 'PO', 'height=400,width=600');
    var content = '<html><head><title>PO</title>' + '<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />' + '<link rel="stylesheet" type="text/css" href="/static/css/page.css" />' + '</head><body>' + content.html() + '</body></html>';

    mywindow.document.write(content);

    mywindow.document.close(); // necessary for IE >= 10
    mywindow.focus(); // necessary for IE >= 10

    setTimeout(function(){
        mywindow.print();
        mywindow.close();
    }, 1000);

    return true;
  });

  $('body').on("click", ".confirm-raw-picklist", function(event) {
    var values = $('form').serializeArray();
    var this_data = $('form');
    if(confirm("Are you sure to Confirm Picklist"))
    {
        $('.loading').removeClass('display-none'); 
        $.ajax({url: '/rm_picklist_confirmation/',
            method: 'POST',
            data: values,
            'success': function(response) {
            this_data.find(".insert-status").html(response).show();
            $('#sortingTable').dataTable().fnReloadAjax();
            if(response == "Picklist Confirmed")
            {
                $.fn.make_disable($("#confirm_raw_picklist"));
                setTimeout(function() { $("#po-modal").modal('toggle') }, 0);
                $("#confirm_raw_picklist").find(".confirm-raw-picklist").prop("disabled",true);
            }
            $("#rm-picklist").dataTable().fnReloadAjax();
            }});
    }
    $('.loading').addClass('display-none');
    event.preventDefault();
  });

  $("body").on('click','#confirm_raw_picklist .print', function(event) {
    var data_id =  $(this).parent().parent().find('h5 b').text()

    $.ajax({url: '/print_rm_picklist?data_id=' + data_id,
            'success': function(response) {
    var mywindow = window.open('', 'Picklist', 'height=400,width=600');
    mywindow.document.write(response);

    mywindow.document.close(); // necessary for IE >= 10
    mywindow.focus(); // necessary for IE >= 10

      setTimeout(function(){
          mywindow.print();
          mywindow.close();
      }, 1000);

    return true;

 }});
  });

  $("#receive-jo").on("click", "#sortingTable td", function(event) {
    event.preventDefault();
    var data_id = $(this).parent().attr("data-id");
    $("#po-modal").attr("style","");
    $.ajax({url: '/confirmed_jo_data?data_id=' + data_id,
            'success': function(response) {
                $('#po-modal').empty();
                $('#po-modal').append(response);
                $("#po-modal").modal();
            }});
  });

  $("body").on("click","#jo-form #add-receive-jo",function(e){
    e.stopImmediatePropagation();
    var tot_quan = 0;
    var id = $(this).parent().parent().attr("id");
    var choice = $(this).attr("src");
    var row = $(this).parent().parent();
    var jo_quan = row.find("td:eq(1)").html();
    $("body [name=received_quantity]").each(function(index,value){
    p_id = $(value).parent().parent().attr("id");
    if(Number(id) == Number(p_id)){
      tot_quan = tot_quan + Number($(value).val());
    }
    });
    if(choice.search('open') != -1)
    {
        if(Number(tot_quan) < Number(jo_quan)){
            row.after("<tr id=" + id + ">" + row.html() + "</tr>");
            $(this).attr("src","/static/img/details_close.png");
            row.next().find("receive_quantity").val(Number(tot_quan) < Number(jo_quan));
        }
    }
    else{
        row.remove();
    }
  });

  $("body").on("keyup","#jo-form [name=received_quantity]",function(e){
   var row = $(this).parent().parent();
   var id = $(this).parent().parent().attr("id");
   var jo_quan = row.find("td:eq(1)").html();
   var tot_quan = 0;
    $("body [name=received_quantity]").each(function(index,value){
    p_id = $(value).parent().parent().attr("id");
    if(Number(id) == Number(p_id)){
      tot_quan = tot_quan + Number($(value).val());
    }
    });
    if(Number(tot_quan) > Number(jo_quan))
    {
        diff = Number(tot_quan) - Number(jo_quan)
        $(this).val(Number($(this).val()) - diff);
        $("body").find(".insert-status").html("Received Quantity should be less than or equal to jo quantity").show();
    }
    else{
        $("body").find(".insert-status").html("").show();
    }

  });

  $("body").on("click","#jo-form .save-receive-jo",function(e){
     data = $("#jo-form") .serializeArray();
     $.ajax({url: '/save_receive_jo/',
             method: 'POST',
             data: data,
             'success': function(response) {
             if(response == "Saved Successfully"){
               $.fn.make_disable($("#jo-form"));
             }
             $("body").find(".insert-status").html(response).show();
            }});
  }); 

  $("body").on("click","#jo-form .rm-generate-grn",function(e){
     data = $("#jo-form") .serializeArray();
     $.ajax({url: '/confirm_jo_grn/',
             method: 'POST',
             data: data,
             'success': function(response) {
             if(response.search('<div') != -1)
             {
               $("#sortingTable").dataTable().fnReloadAjax();
                $('#po-modal').empty();
                $('#po-modal').append(response);
                $("#po-modal").modal();
             }
             else {
               $("body").find(".insert-status").html(response).show();
             }

            }});
  });

  $("#jo-putaway").on("click", "#sortingTable td", function(event) {
    event.preventDefault();
    var data_id = $(this).parent().attr("data-id");
    $("#po-modal").attr("style","");
    $.ajax({url: '/received_jo_data?data_id=' + data_id,
            'success': function(response) {
                $('#po-modal').empty();
                $('#po-modal').append(response);
                $("#po-modal").modal();
            }});
  });

  $("body").on("click", "#putaway_jo .print", function(e) {
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

      setTimeout(function(){
          mywindow.print();
          mywindow.close();
      }, 1000);

    return true;
  });

  $("body").on("keyup","#putaway_jo [name=putaway_quantity]",function(e){
   var row = $(this).parent().parent();
   var id = $(this).parent().parent().attr("id");
   var jo_quan = $(this).parent().prev().html();
   var tot_quan = 0;
    $("body [name=putaway_quantity]").each(function(index,value){
    p_id = $(value).parent().parent().attr("id");
    if(Number(id) == Number(p_id)){
      tot_quan = tot_quan + Number($(value).val());
    }
    });
    if(Number(tot_quan) > Number(jo_quan))
    {
        diff = Number(tot_quan) - Number(jo_quan)
        $(this).val(Number($(this).val()) - diff);
        $("body").find(".insert-status").html("Putaway Quantity should be less than or equal to Original quantity").show();
    }
    else{
        $("body").find(".insert-status").html("").show();
    }

  });

  $("body").on("keyup","#putaway_jo [name=putaway_quantity]",function(){
    jo_quan = $(this).parent().prev().html();
    tot_quan = 0
    id = $(this).parent().parent().attr("id");
    $(this).parent().parent().parent().find("[name=putaway_quantity]").each(function(index,value){
    p_id = $(value).parent().parent().attr("id");
    if(Number(id) == Number(p_id)){
      tot_quan = tot_quan + Number($(value).val());
    }
    });

   if(Number(jo_quan) > Number(tot_quan))
   { 
     $(this).parent().parent().find("td:last-child").html("<img src='/static/img/details_open.png'>");
   }
   else
   { 
     if(!($(this).parent().parent().find("td:last-child").html()))
     {
      $(this).parent().parent().find("td:last-child").html("");
     }
     else {
       $(this).parent().parent().find("td:last-child").html("<img src='/static/img/details_close.png'>");
     }
   }
});

  $("body").on("click","#putaway_jo tr td:last-child img", function(event){
    event.preventDefault();
    img_state = $(this).attr("src");
    dup_con = $(this).parent().parent().clone();
    tot_quan = 0;
    orig_quan = $(this).parent().prev().prev().html();

    id = $(this).parent().parent().attr("id");
    $(this).parent().parent().parent().find("[name=putaway_quantity]").each(function(index,value){
    p_id = $(value).parent().parent().attr("id");
    if(Number(id) == Number(p_id)){
      tot_quan = tot_quan + Number($(value).val());
    }
    });
    dif_quan = Number(orig_quan) - Number(tot_quan);
    $(dup_con).find("[name=putaway_quantity]").attr('value', dif_quan);
    if(img_state.search('open') != -1) {
      if(Number(orig_quan) > Number(tot_quan)){
        $(this).attr("src","/static/img/details_close.png");
        $(this).parent().parent().after("<tr id='" + id + "'>"+ dup_con.html() + "</tr>");
      }
    }
    else {
        id = $(this).parent().parent().attr("id");
        if(($(this).parent().parent().parent().find("tr#"+id)).length != 1)
        {
          $(this).parent().parent().remove();
        }
    }
  });

  $("body").on("click","#putaway_jo .jo-putaway-confirm",function(e){
     data = $("#putaway_jo") .serializeArray();
     $.ajax({url: '/jo_putaway_data/',
             method: 'POST',
             data: data,
             'success': function(response) {
             $("body").find(".insert-status").html(response).show();
             if(response == "Updated Successfully")
             { 
                  $.fn.make_disable($("#putaway_jo"));
                 $("#putaway_jo").find(".jo-putaway-confirm").prop("disabled", true);
                 $("#sortingTable").dataTable().fnReloadAjax();
             }
            }});
  });

  $("#back_orders_rm").on("change","#check-back-orders",function() {
    if($(this).is(":checked"))
    {
        $('#back_orders_rm #sortingTable tbody input[type="checkbox"]').prop('checked',true);
    }
    else
    {
        $('#back_orders_rm #sortingTable tbody input[type="checkbox"]').prop('checked',false);
    }

  });

  $("#back_orders_rm").on("change","[type=checkbox]",function() {

    if($("#sortingTable tbody").find("[type=checkbox]").is(":checked"))
    {
        $("body").find(".back-order-confirm").prop("disabled",false);
        $("body").find(".back-order-rwo-confirm").prop("disabled",false);
    }
    else
    {
        $("body").find(".back-order-confirm").prop("disabled",true);
        $("body").find(".back-order-rwo-confirm").prop("disabled",true);
    }

  });

    $("#back_orders_rm #sortingTable").on("draw.dt",function(){
      if ($('#back_orders_rm #sortingTable').find("th:first-child input").is(':checked')) {
           $('#back_orders_rm #sortingTable tbody input[type="checkbox"]').prop('checked',true);
      }
    });

    $('#back_orders_rm #sortingTable').find("th:first-child").unbind("click.DT");

    $("#back_orders_rm").on("click", ".back-order-confirm", function() {
        var data = {}
        var input = $('#back_orders_rm tbody').find('input:checked');
        $("#po-modal").empty();
        for(i=0; i<input.length; i++) {
            var index = $(input[i].parentNode.parentNode).find('td');
            data[$(index[1]).text() + ":" + $(index[0]).find("input").attr("name")] = $(index[5]).text();
        }
        if (input.length > 0) {
           $.ajax({url: '/generate_rm_po_data/',
            method: 'POST',
            data: data,
            'success': function(response) {
                    $("#po-modal").append(response);
                    $("#po-modal").modal();
                    $("body").find("#myModal").modal();
                    $("body").find(".send-sms-select").selectpicker();
          }});
        }
    });

    $("#po-modal").on("click",".close", function(){
        $('#back_orders #sortingTable input[type="checkbox"]').prop('checked', false);

    });

  material_data = {}
  $("body").on("blur", "#raise_job_order [name=product_code]:not([readonly]), #add_rwo [name=product_code]:not([readonly])",function(e){
      sku_code = $(this).val();
      data = "sku_code=" +sku_code;
      row =  $(this).parent().parent();
      prev_quan = row.find("[name=product_quantity]").val();
      if (!prev_quan)
          prev_quan = 1
      prev_row = row.prev();
      rem_class = row.find("[name=id]").attr("class");
      if(rem_class == undefined){
          rem_class = ''
      }
      var counter = 0;
      if(rem_class != sku_code){
          $.ajax({url: '/get_material_codes/',
                 method: 'POST',
                 data: data,
                 'success': function(response) {
                     if(rem_class != ''){
                         $("#raise_job_order ." + rem_class).parent().parent().remove();
                         new_row = $('body').find('tr#raise-jo-row').clone();
                         prev_row.after("<tr>" + new_row.html() + "</tr>");
                         prev_row.next().find("[name=product_code]").val(sku_code);
                         row = prev_row.next();
                     }
                     if(response == "No Data Found")
                     {
                     }
                     else
                     {
                         material_data[sku_code] = response
                         $.each(response, function(key, value)
                         {
                             if(counter == 0)
                             {
                                 row.find("[name=material_code]").val(key);
                                 row.find("[name=material_quantity]").val(Number(prev_quan) * Number(value));
                                 row.find("[name=id]").attr("class", sku_code);
                             }
                             else {
                                 row.after("<tr>" + row.html() + "</tr>");
                                 row.find("img").attr("src","/static/img/details_close.png");
                                 row.next().find("[name=product_code], [name=product_quantity]").attr("type", "hidden");
                                 row.next().find("[name=product_code]").val(sku_code);
                                 row.next().find("[name=material_code]").val(key);
                                 row.next().find("[name=material_quantity]").val(Number(prev_quan) * Number(value));
                                 row.next().find("[name=id]").attr("class", sku_code);
                                 row = row.next();
                             }
                             counter += 1;
                         });
                      }
              }});
          }
  });

  $("body").on("keyup", "#raise_job_order [name=product_quantity], #add_rwo [name=product_quantity]",function(e){
    $.fn.process_material($(this))
  });

  $("#picklist-orders #sortingTable").on("click", "tr td:not(.dataTables_empty)", function(event) {
    event.preventDefault();
    data = {}
    data['data_id'] = $(this).parent().attr("data-id");
    $("#po-modal").attr("style","");
    $.ajax({url: '/view_confirmed_jo/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $('#po-modal').empty();
                $('#po-modal').append(response);
                $("#po-modal").modal();
            }});
  });

  $("body").on("click", ".generate-picklist-jo", function(event) {
    event.preventDefault();
    data = $("#jo-generate-picklist").serializeArray();
    $.ajax({url: '/jo_generate_picklist/',
            method: 'POST',
            data: data,
            'success': function(response) {
                if(response.search('<form') != -1)
                {
                    $('#po-modal').empty();
                    $('#po-modal').append(response);
                    $("#po-modal").modal();
                    $("#sortingTable").dataTable().fnReloadAjax();
                    $("#rm-picklist").dataTable().fnReloadAjax();
                }
                else
                {
                    $("body").find(".insert-status").html(response).show();
                }
            }});
  });

    $("#back_orders_rm").on("draw.dt",function(){
           if ($('#back_orders_rm').find("th:first-child input").is(':checked')) {
                  $('#back_orders_rm tbody input[type="checkbox"]').prop('checked',true);
              }
    });

  $("body").on("click","#add_rwo .save-rwo, #update_rwo .save-rwo", function(e){
    e.preventDefault();
    form = $(this).closest('form');
    data = form.serializeArray()
    $.ajax({url: '/save_rwo/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $("body").find(".insert-status").html(response).show();
                if(response == 'Added Successfully'){
                    $.fn.make_disable($("#add_rwo"));
                }
                $("#returnableTable").dataTable().fnReloadAjax();
            }});
  });

  $("#raise_rwo").on("click", "td", function(event) {
    event.preventDefault();
    var data_id = $(this).parent().attr('data-id');
    $("#po-modal").attr("style","");
    $.ajax({url: '/saved_rwo_data?data_id=' + data_id,
            'success': function(response) {
                $('#po-modal').empty();
                $('#po-modal').append(response);
                $("#po-modal").modal();
            }});
  });

  $("body").on("click","#add_rwo #raise-rwo-confirm", function(e){
    data = $("form:not(#raise-jo-row)").serializeArray()
    $.ajax({url: '/confirm_rwo/',
            method: 'POST',
            data: data,
            'success': function(response) {
                if(response.search('<tbody>') == -1){
                    $("body").find(".insert-status").html(response).show();
                }
                else {
                    $('#po-modal').empty();
                    $('#po-modal').append(response);
                    $("#po-modal").modal();
                    $("#add_rwo").find("#raise-rwo-confirm, .save-rwo").prop("disabled","true");
                }
                $("#returnableTable").dataTable().fnReloadAjax();
                $("#sortingTable").dataTable().fnReloadAjax();
            }});
  });

    $("#back_orders_rm").on("click", ".back-order-rwo-confirm", function() {
        var data = {}
        var input = $('#back_orders_rm tbody').find('input:checked');
        $("#po-modal").empty();
        for(i=0; i<input.length; i++) {
            var index = $(input[i].parentNode.parentNode).find('td');
            data[$(index[1]).text() + ":" + $(index[0]).find("input").attr("name")] = $(index[5]).text();
        }
        if (input.length > 0) {
           $.ajax({url: '/generate_rm_rwo_data/',
            method: 'POST',
            data: data,
            'success': function(response) {
                    $("#po-modal").append(response);
                    $("#po-modal").modal();
                    $("body").find("#myModal").modal();
                    $("body").find(".send-sms-select").selectpicker();
          }});
        }
    });

});
