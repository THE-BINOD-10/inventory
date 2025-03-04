'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('BatchLevelStockCtrl',['$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;


    vm.filters = {'datatable': 'BatchLevelStock', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':'', 'search6':'', 'search7': '', 'search8': '',
                  'search9': '', 'search10': '', 'search11': '', 'search12': '', 'search13': '', 'search14': '', 'search15': '', 'search16': '', 'search17': '',
                  'search18': '', 'search19': '', 'search20': '', 'search21': '', 'search22': '', 'search23': '', 'search24': '', 'search25': '', 'search26': ''}
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
       .withOption('order', [0, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       //.withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Receipt Number').withTitle('Receipt Number'),
        DTColumnBuilder.newColumn('Receipt Date').withTitle('Receipt Date'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
        DTColumnBuilder.newColumn('Plant Code').withTitle('Plant Code'),
        DTColumnBuilder.newColumn('Plant Name').withTitle('Plant Name'),
        DTColumnBuilder.newColumn('Zone Code').withTitle('Zone Code'),
        DTColumnBuilder.newColumn('dept_type').withTitle('Department Type'),
        DTColumnBuilder.newColumn('Batch Number').withTitle('Batch Number'),
        DTColumnBuilder.newColumn('MRP').withTitle('MRP'),
        DTColumnBuilder.newColumn('Weight').withTitle('Weight'),
        DTColumnBuilder.newColumn('Procurement Price').withTitle('Procurement Price'),
        DTColumnBuilder.newColumn('Procurement Tax Percent').withTitle('Procurement Tax Percent'),
        DTColumnBuilder.newColumn('Unit Purchase Qty Price').withTitle('Unit Purchase Qty Price'),
        DTColumnBuilder.newColumn('Manufactured Date').withTitle('Manufactured Date'),
        DTColumnBuilder.newColumn('Expiry Date').withTitle('Expiry Date'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('Location').withTitle('Location'),
        //DTColumnBuilder.newColumn('Pallet').withTitle('Pallet'),
        DTColumnBuilder.newColumn('Conversion Factor').withTitle('Conversion Factor'),
        DTColumnBuilder.newColumn('Base Uom Quantity').withTitle('Base Uom Quantity'),
        DTColumnBuilder.newColumn('Base Uom').withTitle('Base Uom'),
        DTColumnBuilder.newColumn('Purchase Uom Quantity').withTitle('Purchase Uom Quantity'),
        DTColumnBuilder.newColumn('Purchase Uom').withTitle('Purchase Uom'),
        DTColumnBuilder.newColumn('Stock Value').withTitle('Stock Value'),
        DTColumnBuilder.newColumn('Receipt Type').withTitle('Receipt Type'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date'),
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
               vm.message = "";
               vm.row_data = aData;
               $state.go('app.stockLocator.StockDetail.batch_detail');
                });
            });
        console.log(aData)
        return nRow;
        };
    vm.model_data = {}
    vm.close = close;
    function close() {

      $state.go('app.stockLocator.StockDetail');
    }
    vm.milkbasket_users = ['milkbasket_test', 'NOIDA02', 'NOIDA01', 'GGN01', 'HYD01', 'BLR01', 'GGN02', 'NOIDA03', 'BLR02', 'HYD02'];
    vm.parent_username = Session.parent.userName;
    vm.validate_weight = function(event, row_data) {
     if(vm.milkbasket_users.indexOf(vm.parent_username) >= -1){
       vm.row_data['Weight'] = vm.row_data['Weight'].toUpperCase().replace('UNITS', 'Units').replace(/\s\s+/g, ' ').replace('PCS', 'Pcs').replace('UNIT', 'Unit').replace('INCHES', 'Inches').replace('INCH', 'Inch');
       setTimeout(() => { vm.row_data['Weight'] = vm.row_data['Weight'].trim(); }, 100);
     }
   }
    vm.submit = function() {
      var elem = angular.element($('form'));
      elem = $(elem[1]).serializeArray();
      vm.service.apiCall('stock_detail_update/', 'POST', elem, true).then(function(data){
        if(data.data.status==1) {
             pop_msg(data.data.message);
             vm.close();
            }
             else {
             pop_msg(data.data.message);
          }
      });
    }
    function pop_msg(msg) {
      vm.message = "";
      vm.message = msg;
      vm.reloadData();
     }


    if(vm.permissions.add_subzonemapping) {
      vm.dtColumns.splice(13, 0, DTColumnBuilder.newColumn('Sub Zone').withTitle('Sub Zone'))
    }

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

     if (vm.permissions.pallet_switch) {
       vm.dtColumns.splice(8, 0, DTColumnBuilder.newColumn('Pallet').withTitle('Pallet'))
     }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });


}

