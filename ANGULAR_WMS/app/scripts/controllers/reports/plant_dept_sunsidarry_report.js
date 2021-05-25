FUN = {};
;(function() {
'use strict';
var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('PlantDeptSubsidaryCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    vm.extra_width = {width:'1100px'};

    function getOS() {
      var userAgent = window.navigator.userAgent,
          platform = window.navigator.platform,
          macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
          windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
          iosPlatforms = ['iPhone', 'iPad', 'iPod'],
          os = null;

      if (macosPlatforms.indexOf(platform) !== -1) {
        os = 'Mac OS';
      } else if (iosPlatforms.indexOf(platform) !== -1) {
        os = 'iOS';
      } else if (windowsPlatforms.indexOf(platform) !== -1) {
        os = 'Windows';
      } else if (/Android/.test(userAgent)) {
        os = 'Android';
      } else if (!os && /Linux/.test(platform)) {
        os = 'Linux';
      }
      return os;
    }
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.conf_disable = false;
    vm.datatable = Data.datatable;
    vm.user_type = Session.user_profile.user_type;

    vm.filters = {'datatable': 'PlantDeptMaster', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''
                  , 'search5': '', 'search6': '', 'search7': ''};

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
    vm.dtColumns = [
        DTColumnBuilder.newColumn('Plant Code').withTitle('Plant Code').notSortable(),
        DTColumnBuilder.newColumn('Plant Name').withTitle('Plant Name').notSortable(),
        DTColumnBuilder.newColumn('Plant Internal ID').withTitle('Plant Internal ID').notSortable(),
        DTColumnBuilder.newColumn('Plant Creation Date').withTitle('Plant Creation Date').notSortable(),
        DTColumnBuilder.newColumn('Plant Address').withTitle('Plant Address').notSortable(),
        DTColumnBuilder.newColumn('Subsidiary').withTitle('Subsidiary').notSortable(),
        DTColumnBuilder.newColumn('Department').withTitle('Department').notSortable(),
    ];

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.dis = true;

    vm.reset_filters = function(){
      vm.model_data.filters['plant_code'] = '';
      vm.model_data.filters['plant_name'] = '';
      vm.model_data.filters['sister_warehouse'] = '';
      vm.model_data.filters['datatable'] = 'PlantDeptMaster';
    }

    vm.empty_filter_fields = function(){
      if (Data.rtv_filters) {
        vm.model_data['filters'] = Data.rtv_filters;
      } else {
        vm.model_data.filters['from_date'] = vm.date;
      }
    }

    vm.saveFilters = function(filters){
      filters['datatable'] = 'PlantDeptMaster';
      angular.copy(filters, vm.filters);
    }

  vm.department_type_list = [];
  vm.service.apiCall('get_department_list/').then(function(data){
    if(data.message) {
      vm.department_type_list = data.data.department_list;
    }
  });

  vm.service.apiCall('get_zones_list/').then(function(data){
    if(data.message) {
      data = data.data;
      vm.category_list = data.category_list;
    }
  });
}

})();
