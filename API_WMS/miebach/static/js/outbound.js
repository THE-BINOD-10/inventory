$(document).ready(function() {

  $("body").on('keydown', '#pull-confirmation #scan_imei, #generate_picklist #scan_imei',function(e){

    if(e.which == 13) {
    value = $(this).val();
    this_data = $(this);
    temp = value.split("\n");
    data_id = temp[temp.length-1]
    key = this_data.parent().parent().attr("id");
    count = Number($(this).parent().prev().find("input").val());
    picked = Number(this_data.parent().parent().find('.quantityvalid').val());
    reserved = Number(this_data.parent().prev().prev().html());
    $.ajax({url: '/check_imei?' + key + "=" + data_id,
            'success': function(response) {
              if(response.search('already') != -1)
              {
                  $("body").find(".insert-status").html(response);
                  temp.splice( temp.indexOf(data_id), 1 );
              }
              else if(reserved <= picked)
              {
                  temp.splice( temp.indexOf(data_id), 1 );
              }
              else
              {
                  $("body").find(".insert-status").html("");
                    if(scanned.indexOf(value) < 0)
                    {
                        scanned.push(value);
                        count = count + 1;
                    }
              }

            this_data.parent().prev().find("input").val(count);
            temp.push('');
            this_data.val(temp.join('\n'));
            $.fn.addpicking(this_data.parent().parent().find(".quantityvalid"));
            }});

    }
  });

    $.fn.addpicking = function(this_data) {
   res_quan = this_data.parent().parent().find("td .quantityvalid").parent().prev().html();

    tot_quan = 0
    id = this_data.parent().parent().attr("id");
    this_data.find("tr td:nth-child(8)").each(function(index,value){
    p_id = $(value).parent().attr("id");
    if(Number(id) == Number(p_id)){
      tot_quan = tot_quan + Number($(value).find(".quantityvalid").val());
    }
    });

   if(Number(res_quan) > Number(tot_quan))
   {
     this_data.parent().parent().find("td:last-child").html("<img src='/static/img/details_open.png'>");
   }
   else
   {
     if(!(this_data.parent().parent().find("td:last-child").html()))
     {
      this_data.parent().parent().find("td:last-child").html("");
     }
     else {
       this_data.parent().parent().find("td:last-child").html("<img src='/static/img/details_close.png'>");
     }
   }
     }

    $("#create-order").on("click",'.plus1',function(e) {
    e.stopImmediatePropagation();
    var choice = $(this).attr("src");
    if(choice.search('open') != -1)
    {
    $(this).parent().parent().parent().parent().append("<div class='row col-md-12'>" + $(this).parent().parent().parent().html() + "</div>");
    $(this).attr("src","/static/img/details_close.png");
    }
    else
    {
        $(this).parent().parent().remove();
    }
});


  $("body").on("blur","#pull-confirmation .quantityvalid,#picklist .quantityvalid",function() {
    var picked = $(this).val();
    var reserved = $(this).parent().parent().find("td").eq(3).html();
    if (Number(picked) > Number(reserved))
    {
     $("body").find(".insert-status").html("Picked Quantity must be less than the reserved quantity");
     $(this).val(reserved);
    }
    else
    {
     $("body").find(".insert-status").html("");
    }
});

  $( "#picklist" ).on('click', '.gnr-picklist', function( event ) {
    event.preventDefault();
    var data = {};
    var checked = $(this).parent("div").parent("div").find("input:checked:not('#checkall')")
    var fifo_switch = $('body').find('input[name=fifo-switch]').bootstrapSwitch('state');
    data['fifo-switch'] = fifo_switch;
    $.each(checked, function(index, obj) {
        data[$(obj).attr("name")] = $(obj).val();
        });
    data['ship_reference'] = $(this).parent().find("input").val();
    var table = $('#view-manifest-orders').DataTable();
    $('#picklist').find(".modal").empty();
    $.ajax({url: '/generate_picklist/',
            method: 'POST',
            data: data,
            'success': function(response) {
           $("#processing-confirmation").html(response);
           $("#processing-confirmation").modal();

           $.each(checked, function(index, obj) {
             table.row($("tr[data-id=" + $(obj).attr("name") + "]")).remove().draw( false );
          $("#view-manifest-orders").dataTable().fnReloadAjax();
          $("#batch-table").dataTable().fnReloadAjax();

          });
          }});

    $('#picklist').find(".modal").modal();

  });

 $( "#picklist2" ).on('click', '.gnr-picklist1', function( event ) {
    $('.loading').removeClass('display-none');

    selected = [];
    var nodes = $(".selectpicker").find("option:selected")
    for(i=0; i<nodes.length; i++) {
      selected.push($(nodes[i]).val())
    }

    event.preventDefault();
    var data = {};
    var checked = $('#batch-table').find('input:checked:not("#checkall_batch")')
    var fifo_switch = $('body').find('input[name=fifo-switch]').bootstrapSwitch('state');
    data['fifo-switch'] = fifo_switch;
    $.each(checked, function(index, obj) {
            data[$(obj).attr("value") + "<>" + $(obj).attr("name") + "<>" + $(obj).parent().parent().find("td:eq(2)").html()] = $(obj).parent().parent().find('td:last').text();
        });
     data['selected'] = selected.join();
     $('#processing-confirmation').empty();
    $.ajax({url: '/batch_generate_picklist/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $("#processing-confirmation").append(response);
                $("#sortingTable").dataTable().fnReloadAjax();
                $("#batch-table").dataTable().fnReloadAjax();
                $("#batch-table").closest('.dataTables_scroll').find("[type=checkbox]").prop("checked", false);

            }});
    $("#processing-confirmation").modal();


  });

 $( "#picklist2" ).on('click', '.transfer-order-btn1', function( event ) {
    $('.loading').removeClass('display-none');
    event.preventDefault();
    var data = {};
    var checked = $('#batch-table').find('input:checked:not("#checkall_batch")')
    $.each(checked, function(index, obj) {
            data[$(obj).attr("value")] = $(obj).parent().parent().find('td:last').text();
        });
     $('#processing-confirmation').empty();
    $.ajax({url: '/batch_transfer_order/',
            method: 'POST',
            data: data,
            'success': function(response) {
                if(response.search('No Users') != -1)
                {   
                  $('.top-right').notify({
                  message: { text: response },
                  type: 'danger',
                  fadeOut: { enabled: true, delay: 6000 },
                  }).show();
                }
                else {
                  $("#processing-confirmation").append(response);
                  $("#processing-confirmation").modal();
                  $("#view-manifest-orders").dataTable().fnReloadAjax();
                  $("#batch-table").dataTable().fnReloadAjax();
                }

            }});


  });

 $( "#picklist1" ).on('click', '.transfer-order-btn', function( event ) {
    $('.loading').removeClass('display-none');
    event.preventDefault();
    var data = {};
    var checked = $(this).parent("div").parent("div").find("input:checked:not('#checkall')");
    $.each(checked, function(index, obj) {
            data[$(obj).attr("name")] = $(obj).parent().parent().find('td:last').text();
        });
     $('#processing-confirmation').empty();
    $.ajax({url: '/transfer_order/',
            method: 'POST',
            data: data,
            'success': function(response) {
                if(response.search('No Users') != -1)
                {
                  $('.top-right').notify({
                  message: { text: response },
                  type: 'danger',
                  fadeOut: { enabled: true, delay: 6000 },
                  }).show();
                }
                else {

                  $("#processing-confirmation").append(response);
                  $("#processing-confirmation").modal();
                  $("#view-manifest-orders").dataTable().fnReloadAjax();
                  $("#batch-table").dataTable().fnReloadAjax();
                }

            }});


  });



  $("#picklist").on("click", "tr.results", function(e) {
    if($(e.target).closest('input[type="checkbox"]').length > 0){
    }else {
    var checkbox = $(this).find("input");
    if(checkbox.is(":checked"))
  {
      checkbox.prop("checked", false);
      if($(this).parent().parent().find("[type=checkbox]:checked").length == 0)
      {
         $(this).closest(".dataTables_wrapper").parent().find("button:not(#print-excel)").prop("disabled", true);
      }
  }
    else {
    checkbox.prop("checked", true);
    $(this).closest(".dataTables_wrapper").parent().find("button:not(#print-excel)").prop("disabled", false);
    }
   }
  });


  $('body').on("click", '#open-orders .results', function() {
    var data_id = $(this).data('id');
    var context = this;
    $("#modal-confirmation").empty();
    $.ajax({url: '/view_picklist?data_id=' + data_id,
            'success': function(response) {
                $("#modal-confirmation").append(response);
            }});
    $("#modal-confirmation").modal();
  });


  $('body').on("click", '#picked-orders .results', function() {
    var data_id = $(this).data('id');
    var context = this;
    $("#modal-confirmation").empty();
    $.ajax({url: '/view_picked_orders?data_id=' + data_id,
            'success': function(response) {
                $("#modal-confirmation").append(response);
            }});
    $("#modal-confirmation").modal();
  });


  $("#pull-confirmation,#picklist, #processing-confirmation").on('click','.print', function(event) {
    var data_id =  $(this).parent().parent().find('h5 b').text()

    $.ajax({url: '/print_picklist?data_id=' + data_id,
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

  $("#pull-confirmation,#picklist, #processing-confirmation").on('click','.print-excel', function(event) {
    $('.loading').removeClass('display-none');
    var data_id =  $(this).parent().parent().find('h5 b').text()

    $.ajax({url: '/print_picklist_excel?data_id=' + data_id,
            'success': function(response) {
            $('.loading').addClass('display-none');
            window.location = response;
 }});
  });

  $("#batch-picked-orders").on('click','.marketplace-segregation', function(event) {

    checked_id = [];
    checked = $('body').find('#batch-picked-orders tbody').find('input:checked')
    for(i=0; i<checked.length; i++) {
      checked_id.push($(checked[i]).val());
    }

    $.ajax({url: '/marketplace_segregation?data_id=' + checked_id.join(),
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


  $('body').on("click", ".confirm-picklist", function(event) {
    var values = $('form').serializeArray();
    var this_data = $('form');
    var picklist_id = this_data.find("h5").find("b").text();
    tr_data = $("#pull-open tr[data-id=" + picklist_id + "]").children("td");
    var data = {}
    data["Picklist ID "] = $(tr_data[0]).html();
    data["Picklist Note"] = $(tr_data[1]).html();
    data["Date"] = $(tr_data[2]).html();
    values.push({name: 'picklist_number', value: picklist_id});

    var missing_class = $('#picked').find("tbody").find("tr:not([data-id])");
    missing_class.addClass('results');
    missing_class.attr("data-id", picklist_id);
    if(confirm("Are you sure to Confirm Picklist"))
    {
        $('.loading').removeClass('display-none');
        $.ajax({url: '/picklist_confirmation/',
            method: 'POST',
            data: values,
            'success': function(response) {
            this_data.find(".insert-status").html(response).show();
            $('#pull-open').DataTable().row($("#pull-open tr[data-id=" + picklist_id + "]")).remove().draw( false );
            $('#picked').DataTable().row.add(data).draw( false );
            $("#batch-picked").dataTable().fnReloadAjax();
            $('.loading').addClass('display-none');
            if(response == "Picklist Confirmed")
            {
            $.fn.make_disable(this_data);
            setTimeout(function() { $("#modal-confirmation").modal('toggle') }, 0);
            }
            }});
    }
    else {
       $('.loading').addClass('display-none');
    }
    event.preventDefault();
  });

  $('body').on("submit", "#batch_generate_picklist", function(event) {
    $('.loading').removeClass('display-none');
    var values = $('form').serialize();
    var this_data = $(this);
    var picklist_id = this_data.find("h5").find("b").text();
    tr_data = $("#batch-table tr").children("td");
    var data = {}
    data["SKU Code "] = $(tr_data[1]).html();
    data["Title"] = $(tr_data[2]).html();
    data["Quantity"] = $(tr_data[3]).html();

    var missing_class = $('#picked').find("tbody").find("tr:not([data-id])");
    missing_class.addClass('results');
    missing_class.attr("data-id", picklist_id);

    $.ajax({url: '/picklist_confirmation/?' + values,
        'success': function(response) {
         this_data.find(".insert-status").html(response).show();
         $('#batch-table').DataTable().row($("#batch-table tr[data-id=" + picklist_id + "]")).remove().draw( false );
         $('#picked').DataTable().row.add(data).draw( false );
        $('.loading').addClass('display-none');
        }});
    event.preventDefault();
  });

$("#picklist1").on("click","#checkall",function(){

   if($(this).is(":checked"))
  {
    $('#picklist #view-manifest-orders tbody input[type="checkbox"]').prop('checked', this.checked);
  }
  else
  {
    $('#picklist #view-manifest-orders tbody input[type="checkbox"]').prop('checked', false);
  }
});

$("#picklist2").on("click","#checkall_batch",function(){

   if($(this).is(":checked"))
  {
    $('#picklist #batch-table tbody input[type="checkbox"]').prop('checked', this.checked);
  }
  else
  {
    $('#picklist #batch-table tbody input[type="checkbox"]').prop('checked', false);
  }
});


  $("#picklist1").on("change","[type=checkbox]",function() {

  if($("#picklist1 tbody").find("[type=checkbox]:not('#chackall')").is(":checked"))
  {
    $("body").find(".gnr-picklist").prop("disabled",false);
    $("body").find(".transfer-order-btn").prop("disabled",false);
  }
  else
  {
    $("body").find(".gnr-picklist").prop("disabled",true);
    $("body").find(".transfer-order-btn").prop("disabled",true);
  }

});

  $("#picklist2").on("change","[type=checkbox]",function() {

  if($("#picklist2 tbody").find("[type=checkbox]:not('#checkall_batch')").is(":checked"))
  {
    $("body").find(".gnr-picklist1").prop("disabled",false);
    $("body").find(".transfer-order-btn1").prop("disabled",false);
  }
  else
  {
    $("body").find(".gnr-picklist1").prop("disabled",true);
    $("body").find(".transfer-order-btn1").prop("disabled",true);
  }


  });

  $("#batch-picked-orders").on("change","[type=checkbox]",function() {

  if($("#batch-picked-orders").find("[type=checkbox]").is(":checked"))
  {
    $("body").find(".marketplace-segregation").prop("disabled",false);
  }
  else
  {
    $("body").find(".marketplace-segregation").prop("disabled",true);
  }


  });


$("#picklist").on("click","#generate_picklist .close",function() {

    $("#picklist1").find(".gnr-picklist").attr("disabled",true);
    $("#picklist1").find(".transfer-order-btn").attr("disabled",true);
});

$("#picklist").on("click","#batch_generate_picklist .close",function() {

    $("#picklist2").find(".gnr-picklist1").attr("disabled",true);
    $("#picklist1").find(".transfer-order-btn1").attr("disabled",true);
});



    $('#picklist #view-manifest-orders').closest('.dataTables_scroll').find("th:first-child").unbind("click.DT");
    $("#picklist #batch-table ").on("draw.dt",function(){
           if ($('#picklist #batch-table').closest(".dataTables_scroll").find("th:first-child input").is(':checked')) {
                        $('#picklist #batch-table tbody input[type="checkbox"]').prop('checked',true);
              }
             });

    $("#picklist #view-manifest-orders").on("draw.dt",function(){
           if ($('#picklist #view-manifest-orders').closest(".dataTables_scroll").find("th:first-child input").is(':checked')) {
                        $('#picklist #view-manifest-orders tbody input[type="checkbox"]').prop('checked',true);
              }
             });

    $('#picklist #batch-table').closest('.dataTables_scroll').find("th:first-child").unbind("click.DT");

  $("body").on("keyup","#pull-confirmation .quantityvalid, #generate_picklist .quantityvalid, #confirm_raw_picklist .quantityvalid",function(){
   res_quan = $(this).parent().parent().find("td:last").prev().prev().html();

    tot_quan = 0
    id = $(this).parent().parent().attr("id");
    $(this).parent().parent().parent().find(".quantityvalid").each(function(index,value){
    p_id = $(value).parent().parent().attr("id");
    if(Number(id) == Number(p_id)){
      tot_quan = tot_quan + Number($(value).val());
    }
    });

   if(Number(res_quan) > Number(tot_quan))
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

  $("body").on("click","#pull-confirmation tr td:last-child img, #generate_picklist tr td:last-child img,#confirm_raw_picklist tr td:last-child img", function(event){
    event.preventDefault();
    img_state = $(this).attr("src");
    dup_con = $(this).parent().parent().clone();
    tot_quan = 0;
    orig_quan = $(this).parent().parent().find("td .quantityvalid").parent().prev().html();

    id = $(this).parent().parent().attr("id");
    $(this).parent().parent().parent().find(".quantityvalid").each(function(index,value){
    p_id = $(value).parent().parent().attr("id");
    if(Number(id) == Number(p_id)){
      tot_quan = tot_quan + Number($(value).val());
    }
    });
    dif_quan = Number(orig_quan) - Number(tot_quan);
    $(dup_con).find("input.quantityvalid").attr('value', dif_quan);
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

  $("body").on("keyup","#pull-confirmation .quantityvalid, #generate_picklist .quantityvalid, #confirm_raw_picklist .quantityvalid",function(){
      id = $(this).parent().parent().attr("id");
      tot_quan = 0
      orig_quan = $(this).parent().parent().find("td:last").prev().prev().html();
      $(this).parent().parent().parent().find(".quantityvalid").each(function(index,value){
        p_id = $(value).parent().parent().attr("id");
        if(Number(id) == Number(p_id)){
          tot_quan = tot_quan + Number($(value).val());
        }
      });
      if(Number(tot_quan) > Number(orig_quan))
      {
        var difference = Number(tot_quan) - Number(orig_quan)
        $("body").find(".insert-status").html("Picked Quantity must be less than the reserved quantity").show();
        $(this).val(Number($(this).val()) - difference);
      }
      else
      {
        $("body").find(".insert-status").html("");
      }
});
$(".modal").css("overflow", "hidden");
$("#shippment").on('change','#customer_id, #marketplace',function(){
if(($("#customer_id").val() != "") || ($("#marketplace").val() != "")){
    $("#add-shippment-btn").removeAttr('disabled');
}
else{
  $("#add-shippment-btn").attr('disabled','disabled');
}
});

$("#shippment").on('click','#add-shippment-btn',function(e){
    e.stopImmediatePropagation();
    var c_id = $("#customer_id").val();
    var date = $("#shipment_date").val();
    if(date)
    {
        var data = $("#order-shipment").serialize();
        $("#location-toggle").empty();
        $.ajax({url:'/get_customer_sku?' + data,
        success:function(response){
            if(response.search('No orders') != -1)
            {
                $('.top-right').notify({
                message: { text: response },
                type: 'danger',
                fadeOut: { enabled: true, delay: 6000 },
                }).show();

            }
            else
            {
            $("#location-toggle").append(response);
            $('#location-toggle').modal();
            $('#myModal').modal();
            }

    }
        });
    }
    else
    {
          $('.top-right').notify({
          message: { text: "Shipment date should not be null" },
          type: 'danger',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();

    }
});

$("#create-order").on('click','#add-order-btn',function(e){
    e.preventDefault();
    var cust_id = $("[name=customer_id]").val();
    var sku_id = $("[name=sku_id]").val();
    if(cust_id && sku_id)
    {
        var data = $("#order-create").serialize();
        $.ajax({url:'/insert_order_data?' + data,
        success:function(response){
          if (response == "Success") {
              $('#order-create').trigger("reset");
              $('.top-right').notify({
               message: { text: "Order Created Successfully" },
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
    }
        });
    }
    else
    {
          $('.top-right').notify({
          message: { text: "Missing Required Fields" },
          type: 'danger',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();

    }
});


   $.fn.summary1 = function () {
    var data = [];
    data.push({"class": "details-control", "orderable": false, "data": null, "defaultContent": ""})
    if(this.find(".panel-body").length == 2) {
      var this_data = this.find(".panel-body.active")
    }
    else {
      var this_data = this;
    }
    $.each(this_data.find("th"), function(index, value) {
    if($(value).text() != "") {
      data.push({"data": $(value).text()});
    }
    else {
      return
    }
   });
  //data.push({ 'ship_id': $("[name=shipment_number]")});
  return data
  };

  $.fn.shipmenttable = function () {
    var data_id = this.attr("id");
    var ship_no = $('[name=shipment_number]').val();
    var data = 'customer_id=' + data_id + '&shipment_number=' + ship_no;
    var resp_data;
    $.ajax({url: '/shipment_info_data?' + data,
            'async': false,
            'success': function(response) {
              resp_data=response;
            }});
    return resp_data
  };

  $.fn.get_ship_url = function(){
    return "/results_data/?ship_id=" + $("[name=shipment_number]").val();
  }

   $("body").find('#shipment-info').DataTable( {
        "processing": true,
        "serverSide": true,
        "ajax": { "url": $.fn.get_ship_url(),
        "method": "POST" },
        "columns": $(this).myfunction(),
    } );


  $('body').on('blur', '[name=shipment_number]', function(e){
    if($("[name=shipment_number]")[0].value){
      $('body').find('#shipment-info').dataTable().fnReloadAjax($.fn.get_ship_url());
    }
  });

  $("body").on('click','.add-shipment',function(e){
    e.preventDefault();
    data = ""
    var checked = $('#add-customer').find('input:checked')
    $.each(checked, function(index, obj) {
      sku = $(obj).parent().siblings().eq(0).find("label").html();
      order_quantity = $(obj).parent().siblings().eq(1).find("label").html();
      ship_quantity = $(obj).parent().siblings().eq(2).find("input").val();
      pack_ref = $(obj).parent().siblings().eq(3).find("input").val();
      id = $(obj).attr("value");
      order_id = $(obj).attr("name");
      c_id = $("#add-customer").find("[name=c-id]").val();
      data_row = $("#shipment-info").dataTable();
      if (data == "")
      {
        data = "order_shipment_id=" + id + "&" + "sku_code=" + sku + "&" + "shipping_quantity=" + ship_quantity + "&" + "order_id=" + order_id + "&" + "package_reference=" + pack_ref + "&" + "order_quantity=" + order_quantity;
      }
      else
      {
          data = data + "&" + "order_shipment_id=" + id + "&" + "sku_code=" + sku + "&" + "shipping_quantity=" + ship_quantity + "&" + "order_id=" + order_id +    "&" + "package_reference=" + pack_ref + "&" + "order_quantity=" + order_quantity;
      }
    });
    if(data){
        $.ajax({url:'/insert_shipment_info?' + data,
        success:function(response){
         $("body").find(".insert-status").html("Inserted Successfully").show();
         $("[type=search]").val(id);
         $("#shipment-info").dataTable().fnReloadAjax();
        }
        });
    }
    else {
        $(".insert-status").html("Please make sure that check box is checked in").show().fadeOut(3000);
    }
 });

  $('#shipment-display').on('click', '.print-shipment', function() {
    ship_id = $("[name=shipment_number]").val()

    $.ajax({url: '/print_shipment/?ship_id=' + ship_id,
            'success': function(response) {
                if(response == 'No Records')
                {
                $('.top-right').notify({
                  message: { text: "No Records Found" },
                  type: 'danger',
                  fadeOut: { enabled: true, delay: 6000 },
                  }).show();
               }
               else
              {
                var mywindow = window.open('', 'Shipment', 'height=400,width=600');
                mywindow.document.write('<html><head><title>Shipment</title>');
                mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
                mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
                mywindow.document.write('</head><body>');
                mywindow.document.write('<h4>Shipment List</h4>');
                mywindow.document.write(response);
                mywindow.document.write('</body></html>');

                mywindow.document.close(); // necessary for IE >= 10
                mywindow.focus(); // necessary for IE >= 10

                mywindow.print();
                mywindow.close();

              return true;
             }
        }});
  });

  $("#online-percentage").find("#online-stock").on("click", "td", function(event) {
    event.preventDefault();
    var id = $(this).parent().attr("data-id");
    var online_quantity = $(this).parent().find(":nth-child(3)").html();
    var offline_quantity = $(this).parent().find(":nth-child(4)").html()
    var order_id = $(this).parent().parent().parent().parent().prev().attr('id');
    if ($(this).parent().find('input').length == 0) {
      $(this).parent().find("td:nth-child(3)").html('<input type="text" name="online_quantity" class="smallbox numvalid" value="' + online_quantity + '" style="text-align: center;">');
    }
    if($(this).find('td').last().prev().find('input'))
    {
      $("#online-percentage").find('button[type="submit"]').attr("disabled",false);
    }
  });

  $( "#online-percentage" ).on('click', '.online-percent-stock', function( event ) {
    $('.loading').removeClass('display-none');
    event.preventDefault();
    var data = '';
    var inputs = $("#online-percentage").find("input[name=online_quantity]");
    $.each(inputs, function(index, obj) {
        if (data == "") {
            data = "id=" + $(obj).parent().parent().attr("data-id") + "&" +"online_quantity=" + $(obj).val();
        }
        else {
            data = data + "&" + "id=" + $(obj).parent().parent().attr("data-id") + "&" +"online_quantity=" + $(obj).val();
        }
        });
    var data_row = $('#online-stock').dataTable();
    $.ajax({url: '/update_online_percentage?' + data,
            'success': function(response) {
           $.each(inputs, function(index, obj) {
             data_id = $(obj).parent().parent().attr("data-id")
      data_row.fnUpdate({'SKU Code': $(obj).parent().parent().find("td:nth-child(1)").html(),
                        'Total Quantity': $(obj).parent().parent().find("td:nth-child(2)").html(),
                        'Suggested Online Quantity': $(obj).val(),
                        'Current Online Quantity': $(obj).parent().parent().find("td:nth-child(4)").html(),
                        'Offline Quantity': Number($(obj).parent().parent().find("td:nth-child(2)").html()) - Number($(obj).val()),
                         }, $("#online-stock tr[data-id="+ data_id + "]"));
     $('.top-right').notify({
     message: { text: "Updated Successfully" },
     type: 'success',
     fadeOut: { enabled: true, delay: 6000 },
     }).show();
          });
    $('.loading').addClass('display-none');
          }});
  });

$("#online-stock").on("keyup",".smallbox",function(e){
  e.preventDefault();
  total_quantity = Number($(this).parent().prev().html());
  online_quantity = Number($(this).val());
  offline_quantity = Number($(this).parent().next().next().html());
  if(!online_quantity)
  {
     $('.top-right').notify({
     message: { text: "Online Quantity should not be null" },
     type: 'danger',
     fadeOut: { enabled: true, delay: 6000 },
     }).show();
  }
  if(total_quantity < online_quantity)
  {
     $(this).val(total_quantity - offline_quantity);
     $('.top-right').notify({
     message: { text: "Online and Offline Quantities should not exceed total quantity" },
     type: 'danger',
     fadeOut: { enabled: true, delay: 6000 },
     }).show();
 }
});

$("#shippment").on('click','#add-shippment-btn',function(e){
    var c_id = $("#customer_id").val();
    var date = $("#shipment_date").val();
    if(date)
    {
        var data = $("#order-shipment").serialize();
        $("#location-toggle").empty();
        $.ajax({url:'/get_customer_sku?' + data,
        success:function(response){
            $("#location-toggle").append(response);
            $('#location-toggle').modal();
            $('#myModal').modal();

    }
        });
    }
    else
    {
          $('.top-right').notify({
          message: { text: "Shipment date should not be null" },
          type: 'danger',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();

    }
});

  $.fn.get_customer_data = function(form_name, data){
    $.ajax({url: '/get_customer_data?id=' + data,
            'success': function(response) {
            var res = response.split('<br>')
            form_name.find("[name=customer_name]").val(res[0]);
            form_name.find('[name=telephone]').val(res[1]);
            form_name.find('[name=email_id]').val(res[2]);
            form_name.find('[name=address]').val(res[3]);
          }});
   }

  $("body" ).on('blur', '#modal-order [name=customer_id]', function( event ) {
    event.preventDefault();
    var data = $(this).val();
    var form_name = $("body").find("#modal-order");
    if(data)
    {
        $.fn.get_customer_data(form_name, data);
    }
  });

  $( "#create-order" ).on('blur', '[name=customer_id]', function( event ) {
    event.preventDefault();
    var data = $(this).val();
    var form_name = $("#order-create");
    if(data)
    {
        $.fn.get_customer_data(form_name, data);
    }
  });

  $( "#pullto-locate" ).on('click', '.confirm-return-orders', function( event ) {
    event.preventDefault();
    data = ''
    var status = 'RETURNS'
    var checked = $(this).parent().parent().find("input:checked");
    $.each(checked,function(index,obj) {
    if(!data)
    {
        data = 'id=' + $(obj).attr('name') + '&return_quantity=' + $(obj).parent().parent().find("[name=return_quantity]").val() + '&damaged_quantity=' + $(obj).parent().parent().find("[name=damaged_quantity]").val() + '&status=' + status;
    }
    else {
        data += '&' + 'id=' + $(obj).attr('name') + '&return_quantity=' + $(obj).parent().parent().find("[name=return_quantity]").val() + '&damaged_quantity=' + $(obj).parent().parent().find("[name=damaged_quantity]").val() + '&status=' + status;
    }
    });
    if(data)
    {
    $.ajax({url: '/confirm_return_order?' + data,
            'success': function(response) {
            $('#returned').dataTable().fnReloadAjax();
                if(response == 'Success')
                {
                    $('.top-right').notify({
                    message: { text: response },
                    type: 'success',
                    fadeOut: { enabled: true, delay: 6000 },
                    }).show();
                }
                else
                {
                    $('.top-right').notify({
                    message: { text: response },
                    type: 'warning',
                    fadeOut: { enabled: true, delay: 6000 },
                    }).show();

                }
          }});

    }
    else
    {
        $('.top-right').notify({
            message: { text: "Please make sure that check box is checked in" },
            type: 'danger',
            fadeOut: { enabled: true, delay: 6000 },
            }).show();
    }
  });

  $( "#pullto-locate" ).on('click', '.confirm-cancel-orders', function( event ) {
    event.preventDefault();
    data = ''
    var status='CANCELLED'
    var checked = $(this).parent().parent().find("input:checked");
    $.each(checked,function(index,obj) {
    if(!data)
    {
        data = 'id=' + $(obj).attr('name') + '&return_quantity=' + $(obj).parent().parent().find("[name=return_quantity]").val() + '&damaged_quantity=' + $(obj).parent().parent().find("[name=damaged_quantity]").val() + '&status=' + status;
    }
    else {
        data += '&' + 'id=' + $(obj).attr('name') + '&return_quantity=' + $(obj).parent().parent().find("[name=return_quantity]").val() +'&damaged_quantity=' + $(obj).parent().parent().find("[name=damaged_quantity]").val() + '&status=' + status;
    }
    });
    if(data)
    {
    $.ajax({url: '/confirm_return_order?' + data,
            'success': function(response) {
                $('#cancelled').dataTable().fnReloadAjax();
                if(response == 'Success')
                {
                    $('.top-right').notify({
                    message: { text: response },
                    type: 'success',
                    fadeOut: { enabled: true, delay: 6000 },
                    }).show();
                }
                else
                {
                    $('.top-right').notify({
                    message: { text: response },
                    type: 'warning',
                    fadeOut: { enabled: true, delay: 6000 },
                    }).show();

                }
                    }});

    }
    else
    {
        $('.top-right').notify({
            message: { text: "Please make sure that check box is checked in" },
            type: 'danger',
            fadeOut: { enabled: true, delay: 6000 },
            }).show();
    }
  });

  $("#sales").on("submit", "#sales-returns", function(e) {
  e.preventDefault();
  var data = $(this).serialize();
  var html_data = ''
  $.ajax({url: '/get_order_detail_data/?' + data,
        'success': function(response) {
         $('#sales-orders').removeClass('display-none')
           if(response.search('dispatched') != -1)
           {
              $('.top-right').notify({
                message: { text: response },
                type: 'danger',
                fadeOut: { enabled: true, delay: 6000 },
               }).show();

                  order_data = $('.returns-data').clone();
                  order_data.removeClass('display-none');
                  $("#sales-orders").find('table').find('tr.active').after('<tr>' + order_data.html() + '</tr>')
           }
           else
           {
               res = response.split('$')
               for(i=0;i < res.length;i++)
                {
                   data = res[i].split(',');
                   html_data = $('.returns-data').clone();
                   html_data.find("[name=order_id]").parent().html(data[1]);
                   html_data.find("[name=sku_code]").parent().html(data[2]);
                   html_data.find("[name=customer_id]").parent().html(data[3]);
                   html_data.find("[name=shipping_quantity]").parent().html(data[4]);
                   $("#sales-orders").find('table').find('tr.active').after('<tr id=' + data[i] + '>' + html_data.html() + '</tr>');

                }
           }
          }
        });

  });

 $("body").on('click', '.confirm-transfer', function( event ) {
    $('.loading').removeClass('display-none');

    data = {}
    selected_options = $("#transfer-orders").find(":selected");
    $.each(selected_options, function(index, obj) {
        id = $(obj).parent().parent().parent().find("[name=order_id]").val();
        if($(obj).val())
        {
            data[id] = $(obj).val();
        }
    });

    event.preventDefault();
    $.ajax({url: '/confirm_transfer/',
            method: 'POST',
            data: data,
            'success': function(response) {
            $("body").find(".insert-status").html(response);
            $("body").find(".confirm-transfer").prop("disabled",true);
            $("#batch-table").dataTable().fnReloadAjax();
            }});
    $('.loading').addClass('display-none');


  });

  $("body").on("change","[name=transfer_to]",function() {
    //alert($(this).val());
  });

  $("body").on('keydown', '#generate_picklist #scan_order',function(e){

  if(e.which == 13) {
   value = $(this).val();
   this_data = $(this);
   temp = value.split("\n");
   data_id = temp[temp.length-1]
   var wms_tr = $("#generate_picklist").find("td").filter(function() {
    text = $(this).text().trim()
    return text == data_id;
   }).closest("tr");

   if(wms_tr.length != 0)
   {
       wms_tr.find('#scan_imei').focus();
       this_data.val("");
   }
   else
   {
      alert("Order ID not exists in this picklist");
   }
  }


  });


  $("body").on('keydown', '#generate_picklist .mediumbox',function(e){

  if(e.which == 13) {
    $(this).parent().parent().find("input.quantityvalid").focus();
  }

  });


  $("body").on('keydown', '#generate_picklist .mediumbox',function(e){

  if(e.which == 13) {
    $(this).parent().parent().find("input.quantityvalid").focus();
  }

  });

  $("#back_orders").on("change","#check-back-orders",function() {
    if($(this).is(":checked"))
    {
        $('#back_orders #sortingTable tbody input[type="checkbox"]').prop('checked',true);
    }
    else
    {
        $('#back_orders #sortingTable tbody input[type="checkbox"]').prop('checked',false);
    }

  });

  $("#back_orders").on("change","[type=checkbox]",function() {

    if($("#sortingTable tbody").find("[type=checkbox]").is(":checked"))
    {
        $("body").find(".back-order-confirm").prop("disabled",false);
        $("body").find(".back-order-jo-confirm").prop("disabled",false);
    }
    else
    {
        $("body").find(".back-order-confirm").prop("disabled",true);
        $("body").find(".back-order-jo-confirm").prop("disabled",true);
    }

  });

    $('#back_orders #sortingTable').find("th:first-child").unbind("click.DT");

    $("#back_orders #sortingTable").on("draw.dt",function(){
      if ($('#back_orders').find("th:first-child input").is(':checked')) {
           $('#back_orders #sortingTable tbody input[type="checkbox"]').prop('checked',true);
      }
    });


    $("#back_orders").on("click", ".back-order-confirm", function() {
        var data = {}
        var input = $('#back_orders tbody').find('input:checked');
        $("#po-modal").empty();
        for(i=0; i<input.length; i++) {
            var index = $(input[i].parentNode.parentNode).find('td');
            data[$(index[1]).text() + ":" + $(index[0]).find("input").attr("name")] = $(index[index.length-1]).text();
        }
        if (input.length > 0) {
           $.ajax({url: '/generate_po_data/',
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


  $("body").on("click",".confirm-back-order", function(){
    $('.loading').removeClass('display-none');
    data = $("#back_order_confirm").serialize();
    if(data)
    {
           $.ajax({url: '/confirm_back_order/',
            method: 'POST',
            data: data,
            'success': function(response) {
            $("body").find(".insert-status").html(response);
            $("body").find(".confirm-back-order").prop("disabled", true);
           $("#sortingTable").dataTable().fnReloadAjax();
           $('.loading').addClass('display-none');
           }});
    }
  });

    $("#back_orders").on("click", ".back-order-jo-confirm", function() {
        var data = {}
        var input = $('#back_orders tbody').find('input:checked');
        $("#po-modal").empty();
        for(i=0; i<input.length; i++) {
            var index = $(input[i].parentNode.parentNode).find('td');
            data[$(index[1]).text() + ":" + $(index[0]).find("input").attr("name")] = $(index[index.length-1]).text();
        }
        if (input.length > 0) {
           $.ajax({url: '/generate_jo_data/',
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

  $("#stock-transfer").on("click", "tr td:not(:first-child)", function(e){
    var checkbox = $(this).parent().find("[type=checkbox]");
    if(checkbox.is(":checked")) {
        $(this).parent().find("[type=checkbox]").prop("checked", false);
    }
    else {
    $(this).parent().find("[type=checkbox]").prop("checked", true);
    }
  });

  $("#stock-transfer").find("th:first-child").unbind("click.DT");
  $("#stock-transfer").on("draw.dt",function(){
      if($('#stock-transfer').find("th:first-child input").is(':checked')) {
          $('#stock-transfer tbody input[type="checkbox"]').prop('checked',true);
      }
  });

  $("#stock-transfer").on("click","#checkall_stock",function(){
     if($(this).is(":checked")) {
       $('#stock-transfer tbody input[type="checkbox"]').prop('checked', this.checked);
     }
     else {
       $('#stock-transfer tbody input[type="checkbox"]').prop('checked', false);
     }
  });

  $("#stock-transfer").on("change","[type=checkbox]",function() {
    if($("#stock-transfer tbody").find("[type=checkbox]").is(":checked")) {
      $("body").find("#st-generate-picklist").prop("disabled",false);
    }
    else {
      $("body").find("#st-generate-picklist").prop("disabled",true);
    }

  });

 $("body").on('click', '#st-generate-picklist', function( event ) {
    $('.loading').removeClass('display-none');
    data = {}
    event.preventDefault();
    var checked = $("#stock-transfer tbody input:checked");
    $.each(checked, function(index, obj) {
        data[$(obj).parent().parent().find("td:eq(2)").text() + ":" + $(obj).parent().parent().find("td:eq(3)").text()] = $(obj).val();
    });
    $.ajax({url: '/st_generate_picklist/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $("#processing-confirmation").html(response);
                $("#stock-transfer").dataTable().fnReloadAjax();

            }});
    $("#processing-confirmation").modal();

  });

  $("body").on("click","#st-create-order", function(e){
    e.preventDefault();
    form = $(this).closest('form');
    data = form.serializeArray();
    $.ajax({url: '/create_stock_transfer/',
            method: 'POST',
            data: data,
            'success': function(response) {
                $("body").find(".insert-status").html(response).show();
                if(response == 'Confirmed Successfully'){
                  $('.top-right').notify({
                  message: { text: response },
                  type: 'success',
                  fadeOut: { enabled: true, delay: 6000 },
                  }).show();
                  $("#add_st").trigger('reset');
                }
                else
                {
                  $('.top-right').notify({
                  message: { text: response },
                  type: 'danger',
                  fadeOut: { enabled: true, delay: 6000 },
                  }).show();
                }
            }});
  });

  $("body").on("click",".place-order", function(e){
    e.preventDefault();
    data = 'skus=' + selected_images.join();
    $.ajax({url: '/get_selected_skus/?' + data,
           'success': function(response) {
           $("#location-toggle").html(response);
           $("#location-toggle").modal();
           }
    });
  });

  $("body").on("submit", "#modal-order", function(e){
    e.preventDefault();
    data = $(this).serialize();
    var cust_id = $(this).find("[name=customer_id]").val();
    var sku_id = $(this).find("[name=sku_id]").val();
    if(cust_id && sku_id)
    {
      $.ajax({url: '/insert_order_data/?' + data,
             'success': function(response) {
                if(response == 'Success'){
                  $("body").find(".insert-status").html("Order Created Successfully");
                  $(".append-data1").find(".img-selected").prev().remove();
                  $(".append-data1").find(".img-selected").removeClass("img-selected");
                  selected_images = [];
                  $("#modal-order").find("#add-order-btn").prop('disabled', true);
                }
             }
      });
    }
    else {
      $("body").find(".insert-status").html("Missing Required Fields");
    }
  });
  $("body").on("focus", "#modal-order #modal-shipment", function(e){
     if( $("#modal-order #modal-shipment").hasClass('hasDatepicker') === false )  {
          $("#modal-order #modal-shipment").datepicker();
      }
  });

  $('body').on("click", '#shipment-info .results', function() {
    var data_id = $(this).attr('id');
    var context = this;
    $("#modal-confirmation").empty();
    $.ajax({url: '/shipment_info_data?customer_id=' + data_id + '&shipment_number=' + $("[name=shipment_number]").val(),
            'success': function(response) {
                $("#location-toggle").html(response);
                $("#location-toggle").modal();
            }});
  });

  $('body').on("submit", '#confirm_shipment', function(e) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    var data = {};
    $.ajax({url: '/update_shipment_status?' + values,
                 'success': function(response) {
          this_data.find(".insert-status").html(response).show();
          $("#shipment-info").dataTable().fnReloadAjax($.fn.get_ship_url());
          $("body #confirm_shipment").find("[type=submit]").prop("disabled",true);
          $('.loading').addClass('display-none');
        }});
    $('.loading').addClass('display-none');
  });


});
