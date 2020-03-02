'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('GateoutCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, Service) {
    var vm = this;
    vm.service = Service
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;
    vm.host = Session.host;
    vm.upload_enable = true;
    vm.permissions = Session.roles.permissions;
    var titleHtml = '<input type="checkbox" class="data-select" ng-model="vm.selectAll" ng-change="vm.toggleAll(vm.selectAll, vm.selected); $event.stopPropagation();">';

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'ShipmentInfo', 'ship_id':1, 'gateout':1},
              xhrFields: {
                withCredentials: true
              }
           })
      .withDataProp('data')
      .withOption('drawCallback', function(settings) {
        vm.service.make_selected(settings, vm.selected);
      })
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
      })
      .withOption('headerCallback', function(header) {
        if (!vm.headerCompiled) {
            vm.headerCompiled = true;
            $compile(angular.element(header).contents())($scope);
        }
      })
      .withPaginationType('full_numbers')
      .withOption('rowCallback', rowCallback)
      .withOption('RecordsTotal', function( settings ) {
       console.log("complete") 
      });

    vm.dtColumns = []
        /*DTColumnBuilder.newColumn(null).withTitle(titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                 }
                vm.selected[meta.row] = vm.selectAll;
                return '<input class="data-select" type="checkbox" ng-model="vm.selected[' + meta.row + ']" ng-change="vm.toggleOne(vm.selected);$event.stopPropagation();">';
            }).notSortable(),*/

    vm.dtColumns = [];
    if(vm.permissions.central_order_reassigning && !vm.permissions.dispatch_qc_check) {
       vm.dtColumns.push(DTColumnBuilder.newColumn('Serial Number').withTitle('Serial Number')),
       vm.dtColumns.push(DTColumnBuilder.newColumn('Manifest Number').withTitle('Manifest Number')),
       vm.dtColumns.push(DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity')),
       vm.dtColumns.push(DTColumnBuilder.newColumn('Manifest Date').withTitle('Manifest Date'))
    } else {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Shipment Number').withTitle('Shipment Number')),
      vm.dtColumns.push(DTColumnBuilder.newColumn('Customer ID').withTitle('Customer ID')),
      vm.dtColumns.push(DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name')),
      vm.dtColumns.push(DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity'))
    }
    if(vm.permissions.dispatch_qc_check) {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Signed Invoice').withTitle('Signed Invoice Upload').notSortable())
    } else {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Signed Invoice').withTitle('Upload POD').notSortable())
    }
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $compile(angular.element('td', nRow))($scope);
        /*$('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {*/
        $('td:not(td:last)', nRow).unbind('click');
        $('td:not(td:last)', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                var data = { gateout : 1, customer_id: aData['Customer ID'], shipment_number:aData['Shipment Number'],
                             manifest_number:aData['Manifest Number']}
                vm.service.apiCall("shipment_info_data/","GET", data).then(function(data){

                  if(data.message) {
                    angular.copy(data.data, vm.model_data);
                    $state.go('app.outbound.ShipmentInfo.ConfirmShipment');
                  }
                });
            });
        });
        return nRow;
    }

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.selectAll = false;
        vm.dtInstance.reloadData();
    };

    function toggleAll (selectAll, selectedItems, event) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                selectedItems[id] = selectAll;
            }
        }
        vm.button_fun();
    }

    function toggleOne (selectedItems) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                if(!selectedItems[id]) {
                    vm.selectAll = false;
                    vm.button_fun();
                    return;
                }
            }
        }
        vm.selectAll = true;
        vm.button_fun();
    }

    vm.bt_disable = false;
    vm.button_fun = function() {

      var enable = true
      for (var id in vm.selected) {
        if(vm.selected[id]) {
          vm.bt_disable = false;
          enable = false;
          break;
        }
      }
      if (enable) {
        vm.bt_disable = true;
      }
    }

    vm.close = close;
    function close() {
      $state.go('app.outbound.ShipmentInfo');
    }

    vm.confirm_shipment = confirm_shipment;
    function confirm_shipment() {
      var data = $("input[name=shipment_number]").val();
      data = [];
      angular.forEach(vm.selected, function(key,value){
        if(key) {
          data.push({name: "ship_id", value: vm.dtInstance.DataTable.context[0].aoData[parseInt(value)]._aData['Shipment Number']})
        }
      });
      vm.service.apiCall("print_shipment/", "GET", data).then(function(data){
        if(data.message) {
          vm.service.print_data(data.data, 'Confirm Shipment');
        }
      })
    }

    vm.empty_data = {"shipment_number":"", "shipment_date":"","truck_number":"","shipment_reference":"","customer_id":"", "marketplace":"",
                     "market_list":[]};
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);
    vm.uploaded_file_data = function(data, flag){
      vm.uploadedpdf_order_id = ''
      if(flag == 'view') {
        var send = $("form:visible");
        send = $(send).serializeArray();
        for (var i = 0; i < send.length; i++) {
          if(send[i].name == 'id'){
            vm.uploadedpdf_order_id = send[i].value
          }
        }
        vm.view_signed_copy(vm.uploadedpdf_order_id)
      }else if(flag == 'table') {
        vm.uploadedpdf_order_id = data
      }
    }
    vm.upload_file_name = "";
    $scope.$on("fileSelected", function (event, args) {
      $scope.$apply(function () {
        vm.upload_file_name = args.file.name;
        if(vm.upload_enable){
          vm.uploaded_pdf_send(vm.uploadedpdf_order_id, args.file)
        }
      });
    });

    vm.uploaded_pdf_send = function(id, pdf_file) {
      vm.upload_enable = false;
      var formData = new FormData();
      var el = $("#file-upload");
      var files = pdf_file;

      if(files.length == 0){
        return false;
      }
      formData.append('pdf_file', files);
      formData.append('id', id);
      $.ajax({url: Session.url+'upload_signed_under_taking_form/',
        data: formData,
        method: 'POST',
        processData : false,
        contentType : false,
        xhrFields: {
          withCredentials: true
        },
        'success': function(response) {
          if(response == 'Uploaded Successfully') {
            vm.dtInstance.reloadData();
            Service.showNoty(response);
            vm.upload_enable = true;
          } else {
            Service.showNoty(response, 'warning');
            vm.upload_enable = true;
          }
        },
        'error': function(response) {
          Service.showNoty('Something Went Wrong', 'warning');
          vm.upload_enable = true;
        }
      });
    }
    vm.view_signed_copy = function(id) {
      let elem = []
      let host = vm.host
      elem.push({name:'shipment_id', value:id})
      vm.service.apiCall("get_signed_oneassist_form/", "POST", elem).then(function(data) {
        if(data.message) {
          if (data.data == 'Please Upload Signed Invoice Copy'){
            Service.showNoty(data.data, 'warning');
          } else {
            let srcpdf = host+data.data.data_dict[0]
            var mywindow = window.open(srcpdf, 'height=400,width=600');
            mywindow.focus();
            $timeout(function(){
              mywindow.print();
              mywindow.close();
            }, 3000);
            return true;
          }
        }
      });
    }
    vm.submit = function(data) {
      var send = $("form:visible");
      send = $(send).serializeArray();
      vm.service.apiCall("update_shipment_status/", "GET", send).then(function(data){
        if(data.message) {
          if(data.data["status"]) {
            vm.service.showNoty(data.data.message);  
          } else {
            vm.service.showNoty(data.data.message, 'error', 'topRight');
          }
          vm.close();
          reloadData();
        }
      });
    }

  }
