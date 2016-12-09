$(document).ready(function() {

  $("body").on("submit",  "#cycle-po" , function( event ) {

    var values = $(this).serialize();
    var this_data = $(this);
    $.ajax({url: '/submit_cycle_count?' + values,
            'success': function(response) {
      this_data.find(".insert-status").html(response).show();
      $("#cyc-confirm").dataTable().fnReloadAjax();
            }}); 

    event.preventDefault();
  });

  $("body").on("submit",  "#add_move_inventory" , function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    var wms_code = $(this).find("[name=wms_code]").val()
    var source = $(this).find("[name=source_loc]").val()
    var dest = $(this).find("[name=dest_loc]").val()
    var quant = $(this).find("[name=quantity]").val()
    if(wms_code !="" && source!="" && dest!="" && quant!="")
    {
    $.ajax({url: '/insert_move_inventory?' + values,
            'success': function(response) {
      this_data.find(".insert-status").html(response).show();
      if(response == "Added Successfully"){
        $.fn.make_disable($("#add_move_inventory"));
      }
      $('.loading').addClass('display-none');
            }});
    }
    else
    {
       this_data.find(".insert-status").html("Missing Required fields");
       $('.loading').addClass('display-none');
    }

  });

  $("body").on("submit",  "#add_inventory_adjust" , function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    var wms_code = $(this).find("[name=wms_code]").val()
    var loc = $(this).find("[name=location]").val()
    var quant = $(this).find("[name=quantity]").val()
    if (wms_code != "" && loc !="" && quant !="")
    {
    $.ajax({url: '/insert_inventory_adjust?' + values,
            'success': function(response) {
      if(response == "Added Successfully"){
        $.fn.make_disable($("#add_inventory_adjust"));
      }
      this_data.find(".insert-status").html(response).show();
      $('.loading').addClass('display-none');
            }});
    }
    else {
      this_data.find(".insert-status").html("Missing Required Fields").show();
      $('.loading').addClass('display-none');
    }

  });

  $('body').on("click", '.confirm-adjustment', function() {
    var data = '';

    $.each($('body').find('tr.results'), function(index, obj) {
        if ($(obj).find('input:checked').length > 0) {
            if (data != '') {
                data = data + '&'
            }
            else {
            }
            data = $(obj).find('input:checked').val() + "=" + $(obj).find('input:checked').parent('td').parent('tr').find('td').last().         find('input').val()
        }
        else {
        }
        });

    $.ajax({url: '/confirm_inventory_adjustment?' + data,
            'success': function(response) {
          $("#sortingTable").dataTable().fnReloadAjax();
        }});
  });

  $("#add-move-inventory").on("click",function() {
   $('#move-toggle').empty();
   $.ajax({url: '/add_move_inventory',
            'success': function(response) {
                $('#move-toggle').append(response);
               $('#move-toggle').modal();
               $("#myModal").modal();

            }});
    });

  $("#add-inventory-adjust").on("click",function() {
   $('#sku-toggle').empty();
   $.ajax({url: '/add_inventory_adjust',
            'success': function(response) {
                $('#sku-toggle').append(response);
               $('#sku-toggle').modal();
               $("#myModal").modal();

            }});
    });

    $('body').on("click", '.confirm-move', function() {
    var data = '';

    $.each($('body').find('tr.results'), function(index, obj) {
        if ($(obj).find('input:checked').length > 0) {
            if (data != '') {
                data = data + '&'
            }
            else {
            }
            data = $($(obj).find('input:checked')).attr('name') + "=" +$(obj).find('input:checked').val()
        }
        else {
        }
        });

    $.ajax({url: '/confirm_move_inventory?' + data,
            'success': function(response) {
          $("#sortingTable").dataTable().fnReloadAjax();
        }});
  });

  $('body').on("click", '#cyc-confirm .results', function() {
    var data_id = $(this).attr('id');
    var context = this;
    $('#cycle-toggle').empty();
    $.ajax({url: '/get_id_cycle?data_id=' + data_id,
            'success': function(response) {
                $('#cycle-toggle').append(response);
            }});
    $("#cycle-toggle").modal();
  });

  $('#cycle-count').on('click','#cycle',function(event) {
    data = ""
    if($(".selected").find("td:first").html())
    {
      $.each($(".selected"), function(index,obj) {
        wms_code = $(this).find("td:first").html();
        zone = $(this).find("td:nth-child(2)").html();
        loc = $(this).find("td:nth-child(3)").html();
        quantity = $(this).find("td:nth-child(4)").html();
        if (data == "") {
            data = 'wms_code=' + wms_code + '&zone=' + zone + '&location=' + loc + '&quantity=' + quantity
        }
        else {
            data = data + "&" + 'wms_code=' + wms_code + '&zone=' + zone + '&location=' + loc + '&quantity=' + quantity
        }
      });
    }
    else {
      var wms_code = $($('body').find('thead').find('input')[0]).val();
      var zone = $($('body').find('thead').find('input')[1]).val();
      var loc = $($('body').find('thead').find('input')[2]).val();
      var quantity = $($('body').find('thead').find('input')[3]).val();
      var search = $("#cycleCount_filter").find("input").val();
      var data = 'wms_code=' + wms_code + '&zone=' + zone + '&location=' + loc + '&quantity=' + quantity + '&search_term=' + search
    }
    $.ajax({url: '/confirm_cycle_count?' + data,
            'success': function(response) {
           $('#cycle-toggle').empty();
           $('#cycle-toggle').append(response);
           $('#cycle-toggle').modal();
           $("#cyc-confirm").dataTable().fnReloadAjax();
          } });

  });

  $( "#generate-adjustment" ).on('click', '.delete-inventory', function( event ) {
    event.preventDefault();
    var data = '';
    var checked = $(this).parent("div").parent("div").find("input:checked")
    $.each(checked, function(index, obj) {
        if (data == "") {
            data = $(obj).val() + "=" + $(obj).val()
        }
        else {
            data = data + "&" + $(obj).val() + "=" + $(obj).val()
        }
        });
    $.ajax({url: '/delete_inventory?' + data,
            'success': function(response) {
            $("#sortingTable").dataTable().fnReloadAjax();
          }});
  });

  $("body").on("click", ".cycle-print", function() {
    var content = $(this).closest("form").clone();
    content.find(".modal-footer").remove();

  $("form td:nth-child(5) input").each(function() {
    value = $(this).attr('value', $(this).val());
  });

    var mywindow = window.open('', 'Cycle Count', 'height=400,width=600');
    mywindow.document.write('<html><head><title>Cycle Count</title>');
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

  $("#generate-adjustment").on("change","[type=checkbox]",function() {

  if($("#generate-adjustment tbody").find("[type=checkbox]").is(":checked"))
  {
    $("body").find(".confirm-adjustment").prop("disabled",false);
    $("body").find(".delete-inventory").prop("disabled",false);
  }
  else
  {
    $("body").find(".confirm-adjustment").prop("disabled",true);
    $("body").find(".delete-inventory").prop("disabled",true);
  }


  });

});

