'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CreditNoteCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.apply_filters = colFilters;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.host = Session.host;
    vm.completed = false;
    vm.user_type = Session.user_profile.user_type;
    vm.model_data = {};
    vm.filters = {'datatable': 'CreditNote', 'search0':'', 'search1':''};
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
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });
    // vm.dtColumns = vm.service.build_colums(columns);
      vm.dtColumns = [
        DTColumnBuilder.newColumn('id').withTitle('Credit ID'),
        DTColumnBuilder.newColumn('po_number').withTitle('PO Number'),
        DTColumnBuilder.newColumn('grn_number').withTitle('GRN Number'),
        DTColumnBuilder.newColumn('po_date').withTitle('PO Date'),
        DTColumnBuilder.newColumn('invoice_qty').withTitle('Invoice Quantity'),
        DTColumnBuilder.newColumn('grn_qty').withTitle('GRN Quantity'),
        DTColumnBuilder.newColumn('credit_qty').withTitle('Credit Quantity'),
        DTColumnBuilder.newColumn('invoice_value').withTitle('Invoice Value'),
        DTColumnBuilder.newColumn('credit_number').withTitle('Credit Number'),
        DTColumnBuilder.newColumn('credit_date').withTitle('Credit Date'),
      ];
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
          $scope.$apply(function() {
            if (aData['credit_number'] && aData['credit_date']) {
              var msg = aData['credit_number'] + "- File Ready To Download"
              vm.service.alert_msg(msg).then(function(msg) {
                if (msg == "true") {
                  var sendData = {
                    'credit_id': aData['id']
                  }
                  Service.apiCall("download_credit_note_po_data/", "POST", sendData, true).then(function(data) {
                    if(data.message) {
                      let srcpdf = vm.host+data.data.data[0]
                      var mywindow = window.open(srcpdf, 'height=400,width=600');
                      mywindow.focus();
                      $timeout(function(){
                        mywindow.print();
                        mywindow.close();
                      }, 3000);
                      return true;
                    }
                  });
                }
              });
            } else {
              var dataDict = {
                'po_id': aData['po_id'],
                'prefix': aData['prefix'],
                'receipt': aData['receipt_no']
              }
              vm.service.apiCall('get_credit_note_po_data/', 'POST', dataDict).then(function(data){
                if(data.message) {
                  vm.grn_details_keys = ['PO Number', 'GRN Number', 'Supplier ID', 'Supplier Name', 'Order Date']
                  vm.model_data = data.data;
                  vm.selected_id = aData.id
                  vm.model_data['GRN Number'] = aData.grn_number
                  vm.model_data['PO Number'] = aData.po_number
                  vm.model_data['Order Date'] = aData.po_date
                  vm.model_data['invoice_number'] = aData.invoice_number
                  vm.model_data['invoice_date'] = aData.invoice_date
                  vm.model_data['invoice_value'] = aData.invoice_value
                  vm.model_data['invoice_quantity'] = aData.invoice_qty
                  vm.model_data['challan_number'] = aData.challan_number
                  vm.model_data['challan_date'] = aData.challan_date
                  vm.title = "Credit Note Details";
                  $state.go('app.inbound.RevceivePo.CN');
                }
              });
            }
          });
        });
        return nRow;
    }

    vm.dtInstance = {};
    vm.reloadData = reloadData;
    function reloadData () {
      if (vm.completed) {
        vm.dtInstance.DataTable.context[0].ajax.data.search1 = 'completed';
        vm.dtInstance.reloadData();
      } else {
        vm.dtInstance.DataTable.context[0].ajax.data.search1 = '';
        vm.dtInstance.reloadData();
      }
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    $scope.$on('change_filters_data', function(){
      if($("#"+vm.dtInstance.id+":visible").length != 0) {
        vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
        vm.reloadData();
      }
    });

    vm.file_size_check = function(event, file_obj) {
      var file_size = ($(".grn-form").find('[name="files"]')[0].files[0].size/1024)/1024;
      if(file_size > 10) {
        return true;
      }
      else {
        return false;
      }
    }
    vm.firstReload = function() {
      vm.model_data = {};
      vm.reloadData();
    }
    vm.change_datatable = function() {
      vm.model_data = {};
      vm.reloadData();
    }
    vm.submit = function(form) {
      if (!vm.model_data.credit_number || !vm.model_data.credit_date || !vm.model_data.credit_value) {
        Service.showNoty('Please Fill * Fields');
      } else if ((parseInt(vm.model_data['GRN Price']) + parseInt(vm.model_data.credit_value)) != vm.model_data.invoice_value) {
        Service.showNoty('Credit Note Value Does Not Match Difference Between Invoice Value & GRN Value');
      } else {
        var elem = angular.element($('form'));
        elem = elem[1];
        elem = $(elem).serializeArray();
        var form_data = new FormData();
        vm.selected_id ? form_data.append('credit_id', vm.selected_id) : form_data.append('credit_id', '')
        var files = $(".grn-for").find('[name="file"]')[1].files;
        $.each(files, function(i, file) {
          form_data.append('credit_files', file);
        });
        $.each(elem, function(i, val) {
          form_data.append(val.name, val.value);
        });
        form_data.append("grn_no", vm.model_data["GRN Number"]);
        form_data.append("invoice_date", vm.model_data["invoice_date"]);
        form_data.append("invoice_number", vm.model_data["invoice_number"]);
        vm.service.apiCall('save_credit_note_po_data/', 'POST', form_data, true, true).then(function(data){
          if (data.data == "success"){
            Service.showNoty(data.data);
            vm.close();
            vm.reloadData();
          } else {
            Service.showNoty('Success');
            vm.close();
            vm.reloadData();
          }
        })
      }
    }
    vm.close = close;
    function close() {
      vm.model_data = {};
      vm.reloadData();
      $state.go('app.inbound.RevceivePo');
    }
}
