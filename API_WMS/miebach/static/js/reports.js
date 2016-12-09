$(document).ready(function() {


  $( "#datepicker1, #datepicker2, #datepicker3, #datepicker4, #datepicker5, #datepicker6, #datepicker11, #datepicker12, #datepicker13, #datepicker14, #shipment_date,#ordered_date ").datepicker();

  $('#my-select').multiSelect();

  $('#my-select').multiSelect({
    afterSelect: function(values){
      alert("Select value: "+values);
     },
    afterDeselect: function(values){
      alert("Deselect value: "+values);
    }
  });


  $('#reporttoggle').on('click', '.po-report', function() {
    po_number = $("body").find('#reporttoggle').find('input[name=open_po]').val()

    $.ajax({url: '/print_po?data=' + po_number,
            'success': function(response) {
      var mywindow = window.open('', 'PO', 'height=400,width=600');
      mywindow.document.write('<html><head><title>PO</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });


  $('#reporttoggle').on('click', '.sku-report', function() {
    nodes = $("body").find('#sku_list_form').find('input');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });

    $.ajax({url: '/print_sku?' + data,
            'success': function(response) {
      var mywindow = window.open('', 'SKU', 'height=400,width=600');
      mywindow.document.write('<html><head><title>SKU</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write('<h4>SKU List</h4>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });
var print_fun = function(data, uri, title, is_po=""){
    $.ajax({url: uri + data,
            'success': function(response) {
      var mywindow = window.open('', 'SKU', 'height=400,width=600');
      var title1 = '<html><head><title>'+title+'</title>';
      var heading = '<h4>'+title+'</h4>';

      mywindow.document.write(title1);
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      if(!is_po)
      {
          mywindow.document.write(heading);
      }
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});

  };
 $('#reporttoggle').on('click', '.supplier-report', function() {
    data = $("body").find('#supplier_wise_form').serialize();
    print_fun(data, '/print_supplier_pos?', "Supplier Wise POs", "true");
  });

  $('#reporttoggle').on('click', '.location-report', function() {
    nodes = $("body").find('#location_wise_form').find('input');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });

   print_fun(data, '/print_stock_location?', 'Location Wise Stock');
  });

  $('#reporttoggle').on('click', '.receipt-report', function() {
    nodes = $("body").find('#receipt_summary_form').find('input');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });

    $.ajax({url: '/print_receipt_summary?' + data,
            'success': function(response) {
      var mywindow = window.open('', 'Receipt Summary', 'height=400,width=600');
      mywindow.document.write('<html><head><title>Receipt Summary</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write('<h4>Receipt Summary</h4>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });

  $('#reporttoggle').on('click', '.sku-wise-purchase-report', function() {
    nodes = $("body").find('#sku_wise_purchase').find('input');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });

    $.ajax({url: '/print_sku_wise_purchase?' + data,
            'success': function(response) {
      var mywindow = window.open('', 'SKU Wise Purchases', 'height=400,width=600');
      mywindow.document.write('<html><head><title>SKU Wise Purchases</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write('<h4>SKU Wise Purchases</h4>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });

  $('#reporttoggle').on('click', '.sku-wise-report', function() {

    data = $("#sku_wise_form").serialize();
    $.ajax({url: '/print_sku_wise_stock?' + data,
            'success': function(response) {
      var mywindow = window.open('', 'SKU Wise Stock', 'height=400,width=600');
      mywindow.document.write('<html><head><title>SKU Wise Stock</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write('<h4>SKU Wise Stock</h4>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });

  $('body').on("click", '#reporttoggle .results', function() {
    var data_id = $(this).data('id');
    var context = this;
    $('#reports-toggle').empty();
    $.ajax({url: '/print_po_reports?data=' + data_id,
            'success': function(response) {
           $('#reports-toggle').append(response);
        }});
    $("#reports-toggle").modal();
  });


  $('#reporttoggle').on('click', '.dispatch-report', function() {
    nodes = $("body").find('#dispatch_summary_form').find('input');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });

    $.ajax({url: '/print_dispatch_summary?' + data,
            'success': function(response) {
      var mywindow = window.open('', 'Dispatch Summary', 'height=400,width=600');
      mywindow.document.write('<html><head><title>Dispatch Summary</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write('<h4>Dispatch Summary</h4>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });

  $('#reporttoggle').on('click', '.sales-return-report', function() {
    nodes = $("body").find('#sales_return_form').find('input');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });

    $.ajax({url: '/print_sales_returns?' + data,
            'success': function(response) {
      var mywindow = window.open('', 'Sales Return Report', 'height=400,width=600');
      mywindow.document.write('<html><head><title>Sales Return Report</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write('<h4>Sales Return Report</h4>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });

  $('#reporttoggle').on('click', '.inventory-adjust-report', function() {
    nodes = $("body").find('#inventory_adjust_form').find('input');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });

    $.ajax({url: '/print_adjust_report?' + data,
            'success': function(response) {
      var mywindow = window.open('', 'Adjustment Summary', 'height=400,width=600');
      mywindow.document.write('<html><head><title>Adjustment Summary</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write('<h4>Adjustment Summary</h4>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });

  $('#reporttoggle').on('click', '.inventory-aging-report', function() {
    nodes = $("body").find('#inventory_aging_form').find('input');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });

    $.ajax({url: '/print_aging_report?' + data,
            'success': function(response) {
      var mywindow = window.open('', 'Aging Summary', 'height=400,width=600');
      mywindow.document.write('<html><head><title>Aging Summary</title>');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/bootstrap.css" />');
      mywindow.document.write('<link rel="stylesheet" type="text/css" href="/static/css/page.css" />');
      mywindow.document.write('</head><body>');
      mywindow.document.write('<h4>Aging Summary</h4>');
      mywindow.document.write(response);
      mywindow.document.write('</body></html>');

      mywindow.document.close(); // necessary for IE >= 10
      mywindow.focus(); // necessary for IE >= 10

      mywindow.print();
      mywindow.close();

      return true;
        }});
  });

  $("#config-save").on("click", function () {

     var report_selected = [];
     var report_removed = [];
     data = {};

     var date_val = $('#datepicker11').val();
     var selected = $('#configurations').find('#ms-my-select').find('.ms-elem-selection.ms-selected').find('span')
      var removed = $('#configurations').find('#ms-my-select').find('.ms-selectable').find('li').not($('.ms-selected')).find('span');
     for(i=0; i<selected.length; i++) {
       report_selected.push($(selected[i]).text());
     }
     for(i=0; i<removed.length; i++) {
       report_removed.push($(removed[i]).text());
     }
     data['selected'] = report_selected;
     data['removed'] = report_removed;
     data['email'] = $("#email_input").val();
     data['frequency'] = $('#days_range').val();
     data['date_val'] = date_val;
     data['range'] = $('.time_data option:selected').val();
     $.ajax({url: '/update_mail_configuration/',
             method: 'POST',
             data: data,
             'success': function(response) {
              $('.top-right').notify({
                message: { text: "Updated Successfully" },
                type: 'success',
                fadeOut: { enabled: true, delay: 6000 },
              }).show();

  }});

  });

    $("#reporttoggle table").on("draw.dt",function(){
      if ($('.excel-button').length == 0) {
         $excel_position = $(".tab-content").find(".dataTables_filter")
         print_value = $(".tab-content:last").attr("value");
         $excel_position.after("<form id='print-report-excel' style='float: right;margin-right: 20px;'><input type='hidden' name='excel_name' value='"+print_value+"' class='excel-button'><button type='submit' class='btn btn-primary'>Excel</button></form>")
      }
    });

  $("body").on("submit",  "#print-report-excel" , function( e ) {
    data = []
    table = $(this).parent().find("table:last").attr("id");
    if(table == undefined)
    {
        table = $("table:not(.table)").last().attr("id");
    }
    table_id = "#" + table;
    nodes = $(".data-reports>form").find('input,select');

    data = ''
    $.each(nodes, function(index, value) {
      if (data == '') {
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
      else {
        data += '&'
        data += $(value).prop('name') + '=' + $(value).prop('value');
      }
   });
    e.preventDefault();
    $.ajax({type: 'POST',
    url: '/excel_reports/',
    data: {
            "columns": $(table_id).myfunction_excel(),
            "serialize_data": $(this).serialize() + "&" + data,

    },
    'success': function(response) {
      window.location = response;
    }

    });
  });


});
