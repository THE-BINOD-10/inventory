'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('uploadedPosTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.filters = {'datatable': 'UploadedPos', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':''}
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
       .withOption('rowCallback', rowCallback);
    vm.dtColumns = [
        DTColumnBuilder.newColumn('id').withTitle('S.No'),
        DTColumnBuilder.newColumn('uploaded_user').withTitle('Uploaded User'),
        DTColumnBuilder.newColumn('po_number').withTitle('Po No'),
        DTColumnBuilder.newColumn('uploaded_date').withTitle('Date'),
        DTColumnBuilder.newColumn('customer_name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('verification_flag').withTitle('Validation')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    vm.customer_name=true;


    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    var empty_data = {"validate":"","remarks":""}

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    vm.status = [{name:'To be verified', value:'to_be_verified'},
                 {name:'Verified', value:'verified'},
                 {name:'Rejected', value:'rejected'}];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                vm.model_data = {};
                vm.update = true;
                vm.message = "";
                vm.title = "Update Updated PO's";
                var poId = {id:aData.id};

                vm.service.apiCall("get_updated_pos/", "POST", poId, true).then(function(data) {
                  if(data.message) {
                    angular.extend(vm.model_data, data.data);
                    vm.model_data.data.uploaded_file = Session.host+data.data.data.uploaded_file;
                    $state.go('app.uploadedPOs.PO');
                  }
                });
            });
        });
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    }

    vm.filter_enable = true;

    vm.close = close;
    function close() {

      vm.model_data = {};
      angular.extend(vm.model_data, empty_data);
      $state.go('app.uploadedPOs');
    }

  vm.updateUploadedPO = updateUploadedPO;
  function updateUploadedPO() {
    vm.service.apiCall("validate_po/", "POST", vm.model_data.data, true).then(function(data) {
      if(data.message) {
        vm.close();
        reloadData();

        vm.service.pop_msg(data.data);
      }
    });
  }

  vm.submit = submit;
  function submit(form) {
    vm.model_data.data.verification_flag = form.verification_flag.$viewValue;
    vm.updateUploadedPO();
  }

}
