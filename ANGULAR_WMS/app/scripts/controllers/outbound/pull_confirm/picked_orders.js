'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PickedOrders',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.special_key = {status: 'picked', market_place: ""}
    vm.tb_data = {};
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'PickedOrders', 'special_key': JSON.stringify(vm.special_key)},
              xhrFields: {
                withCredentials: true
              },
              complete: function(jqXHR, textStatus) {
                $scope.$apply(function(){
                  angular.copy(JSON.parse(jqXHR.responseText), vm.tb_data)
                })
              }
           })
       .withDataProp('data')
       .withOption('order', [1, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('picklist_id').withTitle('Picklist ID'),
        DTColumnBuilder.newColumn('customer').withTitle('Customer / Marketplace').notSortable(),
        DTColumnBuilder.newColumn('picklist_note').withTitle('Picklist Note'),
        DTColumnBuilder.newColumn('picked_quantity').withTitle('Picked Quantity').notSortable(),
        DTColumnBuilder.newColumn('shipment_date').withTitle('Shipment Date'),
        DTColumnBuilder.newColumn('date').withTitle('Date')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              vm.service.apiCall('view_picked_orders/', 'GET', {data_id: aData.DT_RowAttr["data-id"], market_place: vm.market}).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  var L = 842;
                  var x = 160;
                  var z = 221;
                  var v1 = L - (x + z);
                  var v2 = (L - z);
                  /*vm.height = data.data.data.length*20;
                  vm.final_height = 420 - vm.height;*/
                  $state.go('app.outbound.PullConfirmation.Picked');
                }
              });
            });
        });
        return nRow;
    }

    vm.dtInstance = {};

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.model_data = {};

    vm.close = close;
    function close() {
      $state.go('app.outbound.PullConfirmation');
    }

    vm.barcode = function() {

      vm.barcode_title = 'Barcode Generation';

      vm.model_data['barcodes'] = [];

      angular.forEach(vm.model_data.data, function(barcode_data){

        var quant = barcode_data.picked_quantity;

        var sku_det = barcode_data.wms_code;

        vm.model_data['barcodes'].push({'sku_code': sku_det, 'quantity': quant})

      })

      vm.model_data['format_types'] = ['format1', 'format2', 'format3']

      var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

      $state.go('app.outbound.PullConfirmation.barcode');
    }


    vm.market_places = [];
    vm.service.apiCall("get_marketplaces_list/?status=picked").then(function(data){
      if(data.message) {
        vm.market_places = data.data.marketplaces;
      }
    })

    vm.market = "";
    vm.change_market = function(data) {

      vm.special_key.market_place = data;
      vm.dtInstance.DataTable.context[0].ajax.data['special_key'] = JSON.stringify(vm.special_key);
      vm.dtInstance.reloadData();
    }

    vm.pdf_data = {};
    vm.generate_invoice = function() {

      var send = ""
      angular.forEach(vm.model_data.data, function(record){
        send = send + record.order_detail_id + ","
      })
      send = send.slice(0,-1);
      vm.service.apiCall("generate_order_invoice/", 'GET', {order_ids: send}, true).then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.pdf_data)
        if (Session.user_profile['user_type'] == 'marketplace_user') {
                $state.go('app.outbound.PullConfirmation.InvoiceM');
        } else if (vm.pdf_data.detailed_invoice) {
                  var L = 600;
                  vm.x = 320;
                  var z = 221;
                  var v1 = L - (vm.x + z);
                  var v2 = (L - z);
                  var styles = vm.pdf_data.data;
                  var cate = vm.pdf_data.data;
                  var n = Object.keys(styles).length / 10;
                  var c = 0;
                  for (var i=0; i<Object.keys(styles).length; i++) {
                    var cat_len = Object.keys(styles[Object.keys(styles)[i]]).length;
                    c = c + cat_len;
                  }
                  c = c / 20;
                  var y = 20*c + 10*n;

                  if (y<=v1) {
                    vm.p = v1-y;
                  }
                  else if (v1<y<(v1+v2)) {
                    vm.p = v1+v2-y;
                  }
                  else {
                    var r = Math.round((y-v1)/v2) - 1;
                    vm.p = v1 + (1+r)*v2 - y;
                  }
          $state.go('app.outbound.PullConfirmation.DetailGenerateInvoice');
        } else {
          $state.go('app.outbound.PullConfirmation.GenerateInvoice');
        }
      }
    })
    }

  // Edit invoice
    vm.invoice_edit = false;
    vm.save_invoice_data = function(data) {

      var send = $(data.$name+":visible").serializeArray();
      vm.service.apiCall("edit_invoice/","POST",send).then(function(data){
        if(data.message) {
          vm.invoice_edit = false;
        }
      })
      console.log("edit");
    }
  }
