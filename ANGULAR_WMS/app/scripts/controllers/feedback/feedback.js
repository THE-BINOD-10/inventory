'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('uploadedfeedbackTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service,  Data, $modal) {
    var vm = this;
    vm.cancelPoDisable = false;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.user_type = Session.roles.permissions.user_type;
    vm.filters = {'datatable': 'FeedbackData', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('User Name').withTitle('User'),
        DTColumnBuilder.newColumn('Feedback Type').withTitle('Feedback Type'),
        DTColumnBuilder.newColumn('SKU').withTitle('SKU'),
        DTColumnBuilder.newColumn('Feedback Remarks').withTitle('Feedback Remarks'),
        DTColumnBuilder.newColumn('URL').withTitle('URL')
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
              vm.update = true;
              vm.message = "";
              vm.title = "View Feedback";
              var mod_data = aData;
              var modalInstance = $modal.open({
                templateUrl: 'views/feedback/toggle/feedback_popup.html',
                controller: 'FeedbackviewDetail',
                controllerAs: 'pop',
                size: 'lg',
                backdrop: 'static',
                keyboard: false,
                resolve: {
                  items: function () {
                    return mod_data;
                  }
                }
              });

              modalInstance.result.then(function (selectedItem) {
              });
            });
        });
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    }

}

function FeedbackviewDetail($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items, Data) {
  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.state_data = items;
  vm.image_url = Session.host
  if (vm.state_data['Feedback Image']){
    vm.image_path = vm.state_data['Feedback Image']
    vm.image = vm.image_url + vm.image_path
  }
    vm.ok = function () {
      $modalInstance.close("close");
    };
  }
angular
  .module('urbanApp')
  .controller('FeedbackviewDetail', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', FeedbackviewDetail]);
