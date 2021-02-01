FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('ClosingStockCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

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

        vm.date = datearray[1] + '/' + datearray[0] + '/' + datearray[2];
      }
    }

    vm.date_format_convert(new Date());
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.conf_disable = false;
    vm.datatable = Data.datatable;
    // vm.datatable = 'ReturnToVendor';
    vm.user_type = Session.user_profile.user_type;

    vm.filters = {'datatable': 'ClosingStockUI', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''
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
     .withOption('rowCallback', rowCallback)
     .withOption('initComplete', function( settings ) {
       vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
     });
    vm.dtColumns = [
        DTColumnBuilder.newColumn('Plant Code').withTitle('Plant Code'),
        DTColumnBuilder.newColumn('Plant Name').withTitle('Plant Name'),
        DTColumnBuilder.newColumn('Department').withTitle('Department'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('SKU Description').withTitle('SKU Description'),
        DTColumnBuilder.newColumn('Current Available Stock').withTitle('Current Available Stock'),
        DTColumnBuilder.newColumn('Base UOM').withTitle('Base UOM'),
        DTColumnBuilder.newColumn('Stock Value').withTitle('Stock Value'),
        //DTColumnBuilder.newColumn('Closing Quantity').withTitle('Closing Quantity'),
        //DTColumnBuilder.newColumn('Base UOM').withTitle('Base UOM'),
        DTColumnBuilder.newColumn('Consumption Quantity').withTitle('Consumption Quantity'),
        DTColumnBuilder.newColumn('Consumption Value').withTitle('Consumption Value'),
        //DTColumnBuilder.newColumn('Remarks').withTitle('Remarks'),
        //DTColumnBuilder.newColumn('').withTitle('')
    ];

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
      $('td', nRow).unbind('click');
      $('td', nRow).bind('click', function() {
        aData['year'] = vm.year;
        aData['month'] = vm.month_no;
        var data = {'cs_data': aData}
        var modalInstance = $modal.open({
          templateUrl: 'views/outbound/toggle/update_cls.html',
          controller: 'ClosingUpdateCtrl',
          controllerAs: '$ctrl',
          size: 'md',
          backdrop: 'static',
          keyboard: false,
          resolve: {
            items: function () {
              return data;
            }
          }
        });
        modalInstance.result.then(function (selectedItem) {
          if (selectedItem['status'] == 'success') {
            selectedItem['datum']['price_request'] = true;
          }
        });
      });
    }
    vm.check_closing_qty = function(row_id, data_id, closing_qty){
      var row_data = vm.dtInstance.DataTable.context[0].aoData[row_id]._aData;
      var avail_stock = Number.parseFloat(row_data["Current Available Stock"]);
      closing_qty = Number.parseFloat(closing_qty);
      if(closing_qty > avail_stock){
        vm["closing_qty_val_"+data_id] = avail_stock;
        vm.service.showNoty("Closing Quantity should be less than or equal to current available stock");
      }
    }


    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.dis = true;

    vm.close = close;
    function close() {
      $state.go('app.inbound.rtv');
      vm.reloadData();
      vm.empty_filter_fields();
      vm.date_format_convert(new Date());
    }



    vm.reset_filters = function(){

      //vm.model_data['filters'] = {};
      vm.model_data.filters['from_date'] = vm.date;
      vm.model_data.filters['plant_code'] = '';
      vm.model_data.filters['plant_name'] = '';
      vm.model_data.filters['sister_warehouse'] = '';
      vm.model_data.filters['sku_code'] = '';
      vm.model_data.filters['sku_category'] = '';
      vm.model_data.filters['datatable'] = 'ClosingStockUI';
    }

    vm.empty_filter_fields = function(){


      if (Data.rtv_filters) {

        vm.model_data['filters'] = Data.rtv_filters;
      } else {

        //vm.model_data['filters'] = {};
        vm.model_data.filters['from_date'] = vm.date;
        //vm.model_data.filters['datatable'] = 'ClosingStockUI';
      }
    }

    vm.saveFilters = function(filters){
      filters['datatable'] = 'ClosingStockUI';
      angular.copy(filters, vm.filters);
    }

  vm.department_type_list = [];
  vm.service.apiCall('get_department_list/').then(function(data){
    if(data.message) {
      vm.department_type_list = data.data.department_list;
    }
  });

    vm.save_closing_qty = function save_closing_qty(row_id, data_id) {
      vm.conf_disable = true;
      var row_data = vm.dtInstance.DataTable.context[0].aoData[row_id]._aData;
      var elem = {data_id: data_id, quantity: vm["closing_qty_val_"+data_id], year: vm.year, month: vm.month_no, remarks: vm["remarks_"+data_id]};
      vm.service.apiCall('save_closing_stock_ui/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == 'Success') {

            vm.service.refresh(vm.dtInstance);
          } else {
            vm.service.showNoty(data.data);

          }
        }
        vm.conf_disable = false;
      });
    }

    vm.service.apiCall('get_zones_list/').then(function(data){
      if(data.message) {
        data = data.data;
        vm.category_list = data.category_list;
      }
    });

    vm.get_consumption_month = function get_consumption_month() {
      var curdate = new Date();
      var day = curdate.getDate();
      var newdate = curdate;
      if(day < 5){
        newdate = new Date(curdate.getFullYear(), curdate.getMonth()-1, 1);
      }
      console.log(newdate.toDateString());
      vm.month_name = newdate.toLocaleString('default', { month: 'long' });
      vm.month_no = newdate.getMonth()+1;
      vm.year = newdate.getFullYear();
    }
    vm.get_consumption_month();

}

})();

angular.module('urbanApp').controller('ClosingUpdateCtrl', function ($modalInstance, $modal, items, Service, Session) {
  var vm = this;
  vm.user_type = Session.roles.permissions.user_type;
  vm.csData = items['cs_data'];
  console.log(vm.csData);
  vm.current_remarks = ''
  vm.current_cs_qty = 0;
  vm.temp_current_consumption_qty = vm.csData['Consumption Quantity'];
  vm.current_consumption_qty = vm.csData['Consumption Quantity'];
  vm.current_consumption_value = vm.csData['Consumption Value'];
  vm.temp_consumption_value = vm.csData['Consumption Value'];
  vm.sku_avg_price = vm.csData['sku_average_price'];
  vm.service = Service;
  vm.confirm_cs_value = function () {
    vm.conf_disable = true;
    var elem = {data_id: vm.csData['data_id'], quantity: vm.current_cs_qty, year: vm.csData['year'], month: vm.csData['month'], remarks: vm.current_remarks};
    vm.service.apiCall('save_closing_stock_ui/', 'POST', elem, true).then(function(data){
      if(data.message) {
        if(data.data == 'Success') {
          vm.cancel('');
          vm.service.showNoty('success');
          //vm.service.refresh(vm.dtInstance);
        } else {
          vm.service.showNoty(data.data);
        }
      }
    vm.conf_disable = false;
    });
  }
  vm.update_consumption_qty = function (dat) {
    if (dat != "" && dat != undefined) {
      var temp_cq = (vm.csData["Current Available Stock"] - parseFloat(dat))
      vm.current_consumption_qty = vm.temp_current_consumption_qty + temp_cq;
      vm.current_consumption_value = vm.temp_consumption_value + ((temp_cq/vm.csData["sku_pcf"])*vm.csData["sku_avg_price"]);

    } else {
      vm.current_consumption_qty = vm.temp_current_consumption_qty;
      vm.current_consumption_value = vm.temp_consumption_value;
    }
  }
  vm.cancel = function (data) {
    temp_dict = {
      'status': 'cancel'
    }
    $modalInstance.close(temp_dict);
  };
});
