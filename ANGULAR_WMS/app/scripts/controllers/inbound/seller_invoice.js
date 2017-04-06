'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SellerInvoiceCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;

    vm.filters = {'datatable': 'SellerInvoice', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
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
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    var columns = ["PO Number", "Seller Name", "Receipt Date", "Order Quantity", "Received Quantity", "Invoice Number"];
    vm.dtColumns = vm.service.build_colums(columns);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
                .renderWith(function(data, type, full, meta) {
                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                  vm.selected[meta.row] = vm.selectAll;
                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
                }))

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      if($("#"+vm.dtInstance.id+":visible").length != 0) {
        vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
        vm.service.refresh(vm.dtInstance);
      }
    });

    vm.close = function() {

      $state.go("app.inbound.SellerInvoice")
    }

    vm.pdf_data = {};
    vm.generate_invoice = function(){

      var po_number = '';
      var status = false;
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
          if(!(po_number)) {
            po_number = temp['PO Number'];
          } else if (po_number != temp['PO Number']) {
            status = true;
          }
          data.push(temp['id']);
        }
      });

      if(status) {
        vm.service.showNoty("Please select same PO's");
      } else {

        var send = data.join(",");
        vm.service.apiCall("generate_seller_invoice?seller_summary_id="+send+"&po_number="+po_number).then(function(data){

          if(data.message) {
            console.log(data.data);
            angular.copy(data.data, vm.pdf_data);
            $state.go("app.inbound.SellerInvoice.Invoice");
          }
        });
      }
    }
  }

