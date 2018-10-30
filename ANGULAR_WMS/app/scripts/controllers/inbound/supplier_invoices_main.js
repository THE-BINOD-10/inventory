'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierInvoiceMainCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

	var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;

    vm.selected = {};
    vm.checked_items = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.display = false;
    vm.extra_width = {'width': '1100px'};
    console.log(vm.user_type);

	//if(vm.user_type !== "marketplace_user") {

    vm.service.apiCall("supplier_invoice_data/").then(function(data) {
        if(data.message) {
          vm.filters = {'datatable': 'ProcessedPOs', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': ''}
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
            .withOption('order', [5, 'desc'])
            .withOption('lengthMenu', [10, 100, 200, 300, 400, 500, 1000, 2000])
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
              //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
            });
          var columns = data.data.headers;
          var not_sort = ['Order Quantity', 'Picked Quantity']
          vm.dtColumns = vm.service.build_colums(columns, not_sort);
          var row_click_bind = 'td';
          vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle('').notSortable().withOption('width', '20px')
                 .renderWith(function(data, type, full, meta) {
                   if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                     vm.selected = {};
                   }
                   // vm.selected[meta.row] = vm.selectAll;
                   // return "<i style='cursor: pointer' ng-click='showCase.addRowData($event, "+JSON.stringify(full)+")' class='fa fa-plus-square'></i>";
                   return vm.service.frontHtml + meta.row + vm.service.endHtml;
                 }))
          // row_click_bind = 'td:not(td:first)';
          vm.dtInstance = {};

          $scope.$on('change_filters_data', function(){
            if($("#"+vm.dtInstance.id+":visible").length != 0) {
              vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
              vm.service.refresh(vm.dtInstance);
            }
          });
          vm.display = true;
        }
      });

	//}//end if market_place_user

  vm.checked_ids = [];
  vm.checkedItem = function(data, index){
    
    if (vm.checked_items[index]) {
      
      delete vm.checked_items[index];
    } else {
      
      vm.checked_items[index] = data;
      vm.checked_ids.push(vm.checked_items[index].id);
    }
    // vm.checked_items[index] = data;
    console.log(data)      
  }

  vm.reloadData = function () {
    $('.custom-table').DataTable().draw();
  };

  vm.inv_number = '';

  vm.move_to = function (click_type) {
    var supplier_name = '';
    var status = false;
    var field_name = "";
    var data = [];
    if (vm.user_type == 'distributor') {
      data = vm.checked_ids;
    } else {
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
          if(!(supplier_name)) {
            supplier_name = temp['Supplier Name'];
          } else if (supplier_name != temp['Supplier Name']) {
            status = true;
          }
          field_name = temp['check_field'];
          var grn_no = temp['GRN No'];
          grn_no = grn_no.split('/');

          var send_data = JSON.stringify({
            grn_no: grn_no, 
            seller_summary_name: supplier_name, 
            seller_summary_id: temp['id'], 
            purchase_order__order_id: temp['purchase_order__order_id'],
            receipt_number: temp['receipt_number']
          });

          data.push(send_data);
        }
      });
    }

    if(status) {
      vm.service.showNoty("Please select same "+field_name+"'s");
    } else {
      if (click_type == 'move_to_inv') {
        vm.inv_number = '';
        swal2({
          title: 'Please enter invoice number',
          text: '',
          input: 'text',
          confirmButtonColor: '#d33',
          // cancelButtonColor: '#d33',
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          showLoaderOnConfirm: true,
          inputOptions: 'Testing',
          inputPlaceholder: 'Type Reason',
          confirmButtonClass: 'btn btn-danger',
          cancelButtonClass: 'btn btn-default',
          showCancelButton: true,
          preConfirm: function (text) {
            return new Promise(function (resolve, reject) {
              vm.inv_number = text;
              if (text === "") {
                $('.swal2-validationerror').remove();
                vm.service.showNoty("Please enter proper invoice number");
                $('.swal2-loading') = {};
              }
              resolve();
            })
          },
          allowOutsideClick: false,
          // buttonsStyling: false
        }).then(function (text) {
            /*swal2({
              type: 'success',
              title: 'Your entered invoice number saved!',
              // html: 'Submitted text is: ' + text
            }),*/
            // $('.swal2-confirm').click(function(){
              vm.move_to_api(click_type, data);
            // })
        });
      } else {
        vm.move_to_api(click_type, data);
      }
    }
  };

  vm.move_to_api = function(click_type, data){
    var send = data.join(",");
    send = {data: send, inv_number: vm.inv_number}
    var url = click_type === 'move_to_po_challan' ? 'move_to_po_challan/' : 'move_to_invoice/';
    vm.bt_disable = true;
    vm.service.apiCall(url, "GET", send).then(function(data){
      if(data.message) {
        console.log(data.message);
        if(data.data.message == 'success'){
          vm.service.showNoty("Updated Successfully");
          vm.reloadData();
        }
        else {
          vm.service.showNoty(data.data.message);
        }
      } else {
        vm.service.showNoty("Something went wrong while moving to po challan !!!");
      }
    });
  }

}
