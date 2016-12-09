$(document).ready(function() {

    $('#reportsTable').dataTable({
        "scrollX": true,
    });

    $('#locationTable').dataTable({
        "scrollX": true,
    });

    $('#receiptTable').dataTable({
        "scrollX": true,
    });

    $('#summaryTable').dataTable({
        "scrollX": true,
    });

    $('#dispatchTable').dataTable({
        "scrollX": true,
    });

    $('#skustockTable').dataTable({
        "scrollX": true,
    });

    $('#skupurchaseTable').dataTable({
        "scrollX": true,
    });

    $('#suppliertable').dataTable({
        "scrollX": true,
    });

    $('#salesreturnTable').dataTable({
        "scrollX": true,
    });

    $('#inventoryadjustTable').dataTable({
        "scrollX": true,
    });

    $('#inventoryagingTable').dataTable({
        "scrollX": true,
    });

  $.fn.myfunction = function () {
    var data = [];
    if(this.find(".panel-body").length == 2) {
      var this_data = this.find(".panel-body.active")
    }
    else {
      var this_data = this;
    }
    $.each(this_data.find("th"), function(index, value) {
      data.push({"data": $(value).text()});
   });
  return data
  };


  $.fn.myfunction_excel = function () {
    var data = [];
    if(this.find(".panel-body").length == 2) {
      var this_data = this.find(".panel-body.active")
    }
    else {
      var this_data = this;
    }
    $.each(this_data.find("th"), function(index, value) {
      data.push({"data": $(value).text()});
   });

   search_data = {};
   data.push( $(".dataTables_filter").find('input').val());
   search_data["index"] = 0;
   $(".dataTable > thead > tr > th >.search-input-text").each(function (index, value) {
     search_data["search_"+index] = $(value).val();
     search_data["index"] = search_data["index"]+1
   });
   data.push({"search_data":search_data});
  return data
  };





  $.fn.tableWidth = function () {
    var data = [];
    var targets = [];
    var integer_fields = ['Phone Number', 'MOQ', 'Priority', 'Total Quantity', 'Quantity', 'Receipt ID', 'Move Quantity', 'Total Quantity', 'Physical Quantity', 'Picklist ID', '', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity', 'Procurement Quantity', 'Cycle Count ID', ' Customer ID'];
    if(this.find(".panel-body").length == 2) {
      var this_data = this.find(".panel-body.active")
    }
    else {
      var this_data = this;
    }
    $.each(this_data.find("th"), function(index, value) {
        $.each(integer_fields, function(ind, val) {
            if ($(value).text() == val) {
                targets.push(index);
            }
        });
    if (targets.length > 0) {
        data.push({ className: 'table-align-center', 'targets': targets });
    }
   });
  return data
  };

  $.fn.stockdetail = function () {
    var data_id = this.attr("id");
    var resp_data;
    $.ajax({url: '/stock_summary_data?wms_code=' + data_id,
            'async': false,
            'success': function(response) {
              resp_data=response;
            }});
    return resp_data
  };


  $.fn.summary = function () {
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
  return data
  };


  $('#cyc-confirm').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#cyc-confirm').myfunction(),
    "columnDefs": $('#cyc-confirm').tableWidth(),
    "order": [[1, 'desc']],
  } );

  $('#sortingTable').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "bAutoWidth": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#sortingTable').myfunction(),
    "columnDefs": $(this).tableWidth(),
  } );

  $('#view-manifest-orders').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#view-manifest-orders').myfunction(),
    "columnDefs": $('#view-manifest-orders').tableWidth(),
    "order": [[1, 'desc']],
  } );

  $('#pull-open').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#pull-open').myfunction(),
    "columnDefs": $('#pull-open').tableWidth(),
    "order": [[1, 'desc']],
  } );

  $('#cycleCount').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#cycleCount thead').myfunction(),
    "columnDefs": $('#cycleCount thead').tableWidth(),
    "dom": 'T<"clear">lfrtip',
    "tableTools": {
            "sRowSelect": "multi",
            "aButtons": [ "select_all", "select_none" ]
        }
  } );
    $('#open-issues').DataTable( {
        "processing": true,
        "serverSide": true,
        "ajax": { "url": "/results_issue/",
        "method": "POST" },
        "columns": $(this).myfunction(),
        "dom": 'T<"clear">lfrtip',
        "tableTools": {
            "sRowSelect": "multi",
            "aButtons": [ "select_all", "select_none" ]
        }
    } );

    $('#resolved').DataTable( {
        "processing": true,
        "serverSide": true,
        "ajax": { "url": "/resolved_issues/",
        "method": "POST" },
        "columns": $(this).myfunction(),
        "dom": 'T<"clear">lfrtip',
        "tableTools": {
            "sRowSelect": "multi",
            "aButtons": [ "select_all", "select_none" ]
        }
    } );

    $('#quality-check').DataTable( {
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": { "url": "/results_data/",
        "method": "POST" },
        "columns": $('#quality-check').myfunction(),
        "columnDefs": $(this).tableWidth(),
        "order": [[1, 'desc']],
        "dom": 'T<"clear">lfrtip',
        "tableTools": {
            "sRowSelect": "multi",
            "aButtons": [ "select_all", "select_none" ]
        }
    } );

  $('#rm-picklist').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#rm-picklist').myfunction(),
    "columnDefs": $('#rm-picklist').tableWidth(),
    "dom": 'T<"clear">lfrtip',
    "tableTools": {
            "sRowSelect": "multi",
            "aButtons": [ "select_all", "select_none" ]
        }
  } );

  $('#raised-st').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#raised-st').myfunction(),
    "columnDefs": $('#raised-st').tableWidth(),
    "order": [[1, 'desc']],
  } );

  $('#stock-transfer').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#stock-transfer').myfunction(),
    "columnDefs": $('#stock-transfer').tableWidth(),
    "order": [[1, 'desc']],
  } );

  $('#warehouseMaster').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#warehouseMaster').myfunction(),
    "columnDefs": $('#warehouseMaster').tableWidth(),
    "order": [[1, 'desc']],
  } );

  var c_po = $('#confirmed').DataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).myfunction(),
    "order": [[0, 'desc']],
  } );

  var dt = $('#stock-summary').DataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).summary(),
    "columnDefs": $(this).tableWidth()
  } );

    $('#batch-table').DataTable( {
      "processing": true,
      "serverSide": true,
      "scrollX": true,
      "lengthMenu": [100, 200, 300, 400, 500],
      "pageLength": 100,
      "ajax": { "url": "/results_data/",
      "method": "POST" },
      "columns": $("#batch-table").myfunction(),
      "columnDefs": $('#batch-table').tableWidth(),
    } );

  $.fn.market_orders = function(){
    var selected = [];
    var order_filter = []
    var nodes = $(".market-button").find("option:selected");
    for(i=0; i<nodes.length; i++) {
      selected.push($(nodes[i]).val())
    }
    var filters = $(".orderTable .search-input-text:not(.dataTables_sizing input)")
    for(i=0; i<filters.length; i++) {
      order_filter.push($(filters[i]).val());
    }

    $('#picklist1 #view-manifest-orders').dataTable( {
      "processing": true,
      "serverSide": true,
      "scrollX": true,                                                                                                                                "bDestroy": true,
      "ajax": { "url": "/results_data/",
      "method": "POST",
      "data": {'marketplace': selected.join(), 'filters': order_filter.join()} },
      "columns": $('#picklist1 #view-manifest-orders').myfunction(),
      "columnDefs": $('#picklist1 #view-manifest-orders').tableWidth(),
    } );

    $('#batch-table').dataTable( {
      "processing": true,
      "serverSide": true,
      "bDestroy": true,
      "scrollX": true,
      "lengthMenu": [100, 200, 300, 400, 500],
      "pageLength": 100,
      "ajax": { "url": "/results_data/",
      "method": "POST",
      "data": {'marketplace': selected.join()} },
      "columns": $('#batch-table').myfunction(),
      "columnDefs": $('#batch-table').tableWidth(),
    } );  

}

  $('.selectpicker').on('change', function(){
    $.fn.market_orders();
  });

  /*$("#picklist").on("input", ".search-input-text:not(.hide)", function(e){
    e.stopPropagation();
    $.fn.market_orders();
  });*/

    $('a[data-toggle="tab"]').on( 'shown.bs.tab', function (e) {
        $($(this).attr("href")).find("table").resize();
    } );

  function addSearchBox (tableName, ex_col) {
    if(ex_col === undefined) { ex_col = false; }
    $(tableName).find("thead > tr > th").each( function (ind, obj) {
        if(ex_col === ind)
        {
          return true;
        }
        $(this).addClass("rm-blur");
        var title = $(tableName).find("thead > tr > th").eq( $(this).index() ).text();
        $(this).html( '<span>'+title+'</span><input style="width: 94%;border: 1px solid #AAA; padding: 5px;margin-right: 24px;" type="text" data-column="'+$(this).index()+'"class=" hide search-input-text" placeholder="Search '+title+'" />' );
    });
  }


  function addfilters(tableName, ex_col){
  addSearchBox(tableName, ex_col);
  var table_fun = window['table' + tableName]
  table_fun = $(tableName).DataTable();
  applyFilter(tableName, table_fun);
}

  /* cycleCount */
  addfilters(".cycle_count");
  $('#cycleCount tfoot').addClass("hide");

  /* sku master */
  addfilters(".sku_master");

  /* supplier master */
  addfilters(".supplier_master");

  /* supplier_sku_mapping */
  addfilters(".supplier_sku_mapping");

  /* bill of materials */
  addfilters(".bill_of_material");

  /* stock detail */
  addfilters(".stock_detail");

  /* Customer Master */
  addfilters(".customerTable");

  /* Customer SKU Mapping */
  addfilters(".customer_sku_mapping");

  /* BOM Master */
  addfilters(".bomTable");

  /* Warehouse Master */
  addfilters(".warehouseTable");

  /* Raise PO */
  addfilters(".raisepoTable");

  /* Raise ST */
  addfilters(".raisestTable");

  /* Receive PO */
  addfilters(".receivepoTable");

  /* Stock Summary */
  addfilters(".stocksummaryTable");

  /* Orders */
  addfilters(".orderTable", ex_col=0);

  /* Batch Orders */
  addfilters(".batchorderTable", ex_col=0);
  $.fn.dataTable.ext.search.push(
     function( settings, data, dataIndex ) {
     selected = []
     var nodes = $(".market-button").find("option:selected");
     for(i=0; i<nodes.length; i++) {
        selected.push($(nodes[i]).val())
      }
      if ( selected.length > 0 )
      {
         return true;
      }
      return false;
      }
  );

  
  function applyFilter(tableName,table) {

    $(tableName+'> thead > tr > th > .search-input-text').on( 'keyup click', function (event) {   // for text boxes
      event.stopPropagation();
      var i =$(this).attr('data-column');  // getting column index
      var v =$(this).val();  // getting search input value
      table.columns(i).search(v).draw();
    });

    $(tableName+"> thead > tr > th span").on("click", function (event) {

      event.stopPropagation();
      $('.search-input-text').each(function() {
      if ($(this).val().length == 0) {
        $(this).addClass("hide");
        $(this).siblings("span").removeClass("hide");
      }
      });
      //removeValues();
      //$(".search-input-text").addClass("hide")
      //$(tableName+"> thead > tr > th span").removeClass("hide")
      $(this).siblings(".search-input-text").toggleClass("hide");
      $(this).toggleClass("hide");
    });
    
    $("*:not(.search-input-text,span)").click( function () {

      $('.search-input-text').each(function() {
      if ($(this).val().length == 0) {  
        $(this).addClass("hide");
        $(this).siblings("span").removeClass("hide");
     
      //if ($(tableName+" > thead").find("span").hasClass("hide")) {
        //removeValues();
        //$(this).find(".search-input-text").addClass("hide");
        //$(this).find("span").removeClass("hide");
      }
      });
    });
  }

  function removeValues () {
    /*
    $('.search-input-text').each(function() {
      if ($(this).val().length > 0) {
        $(this).val(''); 
        var i =$(this).attr('data-column');  // getting column index
        var v =$(this).val();  // getting search input value
        table.columns(i).search(v).draw();
      }
    });
    */
  }

  /*
  table.columns().every( function () {
        var that = this;

        $( 'input', this.footer() ).on( 'keyup change', function () {
            that
                .search( this.value )
                .draw();
        } );
    } );*/

  $('#confirmTable').dataTable();

  var batch_count=0
  $("[name='batch-process']").on('switchChange.bootstrapSwitch', function(event, state) {
    var state = state;
    $.ajax({url: '/switches?batch_switch=' + state,
        'success': function(response) {
      if(state == true) {
          $("[name='batch-process']").attr("checked", true);
          $("#picklist1").hide();
          $("#picklist2").show();
          $("#picklist2").find("table").resize();

    if (batch_count == 0) {
       batch_count+=1;
      }
      }
      else {
          $("[name='batch-process']").attr("checked", false);
          $("#picklist2").hide();
          $("#picklist1").show();
          $("#picklist1").find("table").resize();
      }
    }});
  });
  var gnr_report = $('#gnr-report').DataTable( {
    "processing": true,
    "serverSide": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).summary()
  } );

  $('#receive-items').DataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).myfunction(),
    "order": [[0, 'desc']]
  } );

  $('#picked').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).find(".panel-body#picked-orders").myfunction(),
    "columnDefs": $('#picked').tableWidth(),
    "order": [[1, 'desc']]
  } );

  $('#batch-picked').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).find(".panel-body#batch-picked-orders").myfunction(),
    "columnDefs": $('#batch-picked').tableWidth(),
    "order": [[1, 'asc']]
  } );

  $('#cancelled').dataTable( {
    "processing": true,
    "serverSide": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).find(".panel-body#cancel-orders").myfunction(),
    "order": [[1, 'asc']]
  } );

  $('#returned').dataTable( {
    "processing": true,
    "serverSide": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).find(".panel-body#return-orders").myfunction(),
    "order": [[1, 'asc']]
  } );



  $('#online-stock').DataTable( {
    "processing": true,
    "serverSide": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $(this).myfunction(),
  } );

  $('#returns-table').DataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#returns-table').myfunction(),
  } );

  $('#vendorTable').DataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#vendorTable').myfunction(),
  } );

  $('#returnableTable').dataTable( {
    "processing": true,
    "serverSide": true,
    "scrollX": true,
    "ajax": { "url": "/results_data/",
    "method": "POST" },
    "columns": $('#returnableTable').myfunction(),
    "columnDefs": $('#returnableTable').tableWidth(),
  } );

    var detailRows = [];

    $('#stock-summary').on( 'click', 'tr td', function () {
        var tr = $(this).closest('tr');
        var row = dt.row( tr );
        var idx = $.inArray( tr.attr('id'), detailRows );

        if ( row.child.isShown() ) {
            tr.removeClass( 'details' );
            row.child.hide();

            // Remove from the 'open' array
            detailRows.splice( idx, 1 );
        }
        else {
            tr.addClass( 'details' );
            var row_data = $(tr).stockdetail();
            row.child( row_data ).show();

            // Add to the 'open' array
            if ( idx === -1 ) {
                detailRows.push( tr.attr('id') );
            }
        }
    } );

    // On each draw, loop over the `detailRows` array and show any child rows
    dt.on( 'draw', function () {
        $.each( detailRows, function ( i, id ) {
            $('#'+id+' td.details-control').trigger( 'click' );
        } );
    } );


  $("body").on("submit",  "#sku_list_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#reportsTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_sku_filter?' + data,
        "columns": $('#reportsTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $("body").on("submit",  "#receipt_note_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#receiptTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_po_filter?' + data,
        "columns": $('#receiptTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $("body").on("submit",  "#location_wise_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#locationTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_location_filter?' + data,
        "columns": $('#locationTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $("body").on("submit",  "#supplier_wise_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#suppliertable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_supplier_details?' + data,
        "columns": $('#suppliertable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $("body").on("submit",  "#receipt_summary_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#summaryTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_receipt_filter?' + data,
        "columns": $('#summaryTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $("body").on("submit",  "#dispatch_summary_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#dispatchTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_dispatch_filter?' + data,
        "columns": $('#dispatchTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $("body").on("submit",  "#sku_wise_form" , function( event ) { 
    event.preventDefault();
    data = $(this).serialize();
    $('#skustockTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_sku_stock_filter?' + data,
        "columns": $('#skustockTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $("body").on("submit",  "#sku_wise_purchase" , function( event ) { 
    event.preventDefault();
    data = $(this).serialize();
    $('#skupurchaseTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_sku_purchase_filter?' + data,
        "columns": $('#skupurchaseTable').myfunction(),
        "columnDefs": $('#skupurchaseTable').tableWidth(),
    } );
  });

  $("body").on("submit",  "#inventory_adjust_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#inventoryadjustTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_inventory_adjust_filter?' + data,
        "columns": $('#inventoryadjustTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $("body").on("submit",  "#inventory_aging_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#inventoryagingTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_inventory_aging_filter?' + data,
        "columns": $('#inventoryagingTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

  $('.selectpicker').selectpicker();
  $('.mailpicker').selectpicker();

    $('.mailpicker').on('change', function(){
    var selected = [];
    var nodes = $(this).find("option:selected")
    for(i=0; i<nodes.length; i++) {
      selected.push($(nodes[i]).val())
    }

    $.ajax({url: '/enable_mail_reports?data=' + selected,
            method: 'GET',
            'success': function(response) {

     }});


});

  $("body").on("submit",  "#sales_return_form" , function( event ) {
    event.preventDefault();
    data = $(this).serialize();
    $('#salesreturnTable').dataTable({
        "bDestroy": true,
        "processing": true,
        "serverSide": true,
        "scrollX": true,
        "ajax": '/get_sales_return_filter?' + data,
        "columns": $('#salesreturnTable').myfunction(),
        "columnDefs": $(this).tableWidth(),
    } );
  });

});
