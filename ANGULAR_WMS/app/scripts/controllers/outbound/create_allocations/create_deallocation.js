FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('CreateDeallocations',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    // vm.date = new Date();
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

    vm.date_format_convert = function(utc_date){

      var os_type = getOS();

      var date = utc_date.toLocaleDateString();
      var datearray = date.split("/");

      if (os_type == 'Windows') {

        if (datearray[1] < 10 && datearray[1].length == 1) {
          datearray[1] = '0'+datearray[1];
        }

        if (datearray[0] < 10 && datearray[0].length == 1) {
          datearray[0] = '0'+datearray[0];
        }

        vm.date = datearray[0] + '/' + datearray[1] + '/' + datearray[2];
      } else {
        vm.date = datearray[0] + '/' + datearray[1] + '/' + datearray[2];
      }
    }

    var today = new Date();
    vm.date_format_convert(new Date(today.setMonth(today.getMonth() - 1)));
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.conf_disable = false;
    vm.datatable = Data.datatable;
    vm.user_type = Session.user_profile.user_type;

    vm.filters = {'datatable': 'OrderAllocations', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''
                  , 'search5': '', 'search6': '', 'search7': '', 'from_date': vm.date};

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
    vm.dtColumns = [
        DTColumnBuilder.newColumn('Customer ID').withTitle('Customer ID'),
        DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('Updated CustomerName').withTitle('Updated CustomerName'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('SKU Description').withTitle('SKU Description'),
        DTColumnBuilder.newColumn('Allocated Quantity').withTitle('Allocated Quantity'),
        DTColumnBuilder.newColumn('Deallocation Quantity').withTitle('Deallocation Quantity'),
        DTColumnBuilder.newColumn('').withTitle(''),
    ];

//    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
//                .renderWith(function(data, type, full, meta) {
//                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
//                    vm.selected = {};
//                  }
//                  vm.selected[meta.row] = vm.selectAll;
//                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
//                }))

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

      vm.model_data['filters'] = {};
      vm.model_data.filters['from_date'] = vm.date;
      vm.model_data.filters['datatable'] = 'OrderAllocations';
      vm.service.generate_report(vm.dtInstance, vm.model_data.filters);
    }

    vm.empty_filter_fields = function(){


      if (Data.rtv_filters) {

        vm.model_data['filters'] = Data.rtv_filters;
      } else {

        vm.model_data['filters'] = {};
        vm.model_data.filters['sku_code'] = '';
        vm.model_data.filters['customer_id'] = '';
        vm.model_data.filters['from_date'] = vm.date;
        vm.model_data.filters['to_date'] = '';
        vm.model_data.filters['order_id'] = '';
        vm.model_data.filters['datatable'] = 'OrderAllocations';
      }
    }

    vm.saveFilters = function(filters){
      Data.rtv_filters = filters;
      vm.model_data.filters['datatable'] = 'OrderAllocations';
      vm.service.generate_report(vm.dtInstance, vm.model_data.filters);
    }

    vm.check_dealloc_qty = function(id, data_id) {
      var dealloc_qty = vm['deallocation_qty_val_'+ data_id];
      var row_data = vm.dtInstance.DataTable.context[0].aoData[id]._aData;
      if(!dealloc_qty){
        dealloc_qty = 0;
      }
      if(row_data['Allocated Quantity'] < dealloc_qty) {
        vm.service.showNoty("Deallocation Quantity should be less than or equal to Allocated Quantity");
        vm['deallocation_qty_val_'+ data_id] = Number(row_data['Allocated Quantity']);
      }
    }

	vm.save_dealloc_qty = function(id, data_id) {
        var row_data = vm.dtInstance.DataTable.context[0].aoData[id]._aData;
        var dealloc_dict = {};
		if (vm['deallocation_qty_val_'+ data_id]) {
		  dealloc_dict['allocation_ids'] = row_data['allocation_ids'];
		  dealloc_dict['dealloc_qty'] = vm['deallocation_qty_val_'+ data_id]
          vm.service.apiCall('insert_deallocation_data/', 'POST', dealloc_dict).then(function(resp) {
            if (resp.data == 'Success') {
              vm.service.refresh(vm.dtInstance);
            }
          })
		}
	}



}

})();
