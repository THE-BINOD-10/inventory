'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SizeMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'SizeMaster'}
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
         //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('size_name').withTitle('Size Name'),
        DTColumnBuilder.newColumn('size_value').withTitle('Sizes')
    ];

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                angular.copy(aData, vm.model_data);
                vm.model_data['sizes'] = [];
                angular.forEach(vm.model_data.size_value, function(temp){
                  if(temp) {
                    vm.model_data.sizes.push({"size":temp})
                  }
                })
                vm.update = true;
                vm.title = "Update Size"
                $state.go('app.masters.SizeMaster.AddSize');
            });
        });
        return nRow;
    }

    var empty_data = {
                    "size_name": "",
                    "sizes": [{"size":""}]
                    }
    vm.update = false;
    vm.title = "Add Size"
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.SizeMaster');
  }

  vm.add = function() {

    vm.title = "ADD SIZE"
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    $state.go('app.masters.SizeMaster.AddSize');
  }

  vm.send_size = function(url, data) {

    vm.service.apiCall(url, 'POST', data, true).then(function(data){
      if(data.message) {
        if (data.data.data == 'New Size Added' || data.data.data == 'Updated Successfully')  {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data.data);
        }
      }
    });
  }

  vm.submit = function(data) {
    if (data.$valid) {
      var data = {};
      data['size_name'] = vm.model_data.size_name;
      data['size_value'] = '';
      angular.forEach(vm.model_data.sizes, function(temp, index){
        if (temp.size && (data['size_value'].indexOf(temp.size) == -1)) {
          if(vm.model_data.sizes.length-1 == index) {
            data['size_value'] += temp.size;
          } else {
            data['size_value'] += temp.size+'<<>>'
          }
        }
      })
      if ("ADD SIZE" == vm.title) {
        vm.send_size('add_size/', data);
      } else {
        data['id'] = vm.model_data.DT_RowAttr['data-id'];
        vm.send_size('update_size/', data);
      }
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

}
