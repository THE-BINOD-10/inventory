'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SkuClassificationTable',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.permissions = Session.roles.permissions;
    vm.service = Service;

    vm.filters = {'datatable': 'SkuClassification', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
           // .withOption('drawCallback', function(settings) {
           //   vm.service.make_selected(settings, vm.selected);
           // })
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
            .withOption('initComplete', function( settings ) {
              vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
            })
            .withPaginationType('full_numbers');


    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
                vm.selected[meta.row] = vm.selectAll;
                return vm.service.frontHtml + meta.row + vm.service.endHtml +'<input type="hidden" name="id" value="'+full.DT_RowAttr['sku_code']+'">';
            }).notSortable(),
        DTColumnBuilder.newColumn('generation_time').withTitle('Generation Date'),
        DTColumnBuilder.newColumn('sku_code').withTitle('Sku Code'),
        DTColumnBuilder.newColumn('sku_name').withTitle('Sku Name'),
        DTColumnBuilder.newColumn('sku_category').withTitle('Sku Category'),
        DTColumnBuilder.newColumn('ean_number').withTitle('Ean Number'),
        DTColumnBuilder.newColumn('sheet').withTitle('Sheet'),
        DTColumnBuilder.newColumn('vendor').withTitle('Vendor'),
        DTColumnBuilder.newColumn('reset_stock').withTitle('Reset Stock'),
        DTColumnBuilder.newColumn('searchable').withTitle('Searchable'),
        DTColumnBuilder.newColumn('aisle').withTitle('Aisle'),
        DTColumnBuilder.newColumn('rack').withTitle('Rack'),
        DTColumnBuilder.newColumn('shelf').withTitle('Shelf'),
        DTColumnBuilder.newColumn('combo_flag').withTitle('Combo Flag'),
        DTColumnBuilder.newColumn('avg_sales_day').withTitle('Avg Sales/Day Qty'),
        DTColumnBuilder.newColumn('avg_sales_day_value').withTitle('Avg Sales/Day Value'),
        DTColumnBuilder.newColumn('cumulative_contribution').withTitle('Cumulative Contribution'),
        DTColumnBuilder.newColumn('classification').withTitle('Classification'),
        DTColumnBuilder.newColumn('mrp').withTitle('MRP'),
        DTColumnBuilder.newColumn('weight').withTitle('Weight'),
        DTColumnBuilder.newColumn('replenushment_qty').withTitle('Replenushment Qty'),
        DTColumnBuilder.newColumn('sku_avail_qty').withTitle('SKU Avail Qty'),
        DTColumnBuilder.newColumn('avail_qty').withTitle('BA Avail Qty'),
        DTColumnBuilder.newColumn('min_stock_qty').withTitle('Min Stock'),
        DTColumnBuilder.newColumn('max_stock_qty').withTitle('Max Stock'),
        DTColumnBuilder.newColumn('source_location').withTitle('Source Location')
        .renderWith(function(data, type, full, meta) {
          return "<input type='text' class='form-control' name='source_location' value='"+full.source_location+"' class='smallbox' readonly>"
        }),
        DTColumnBuilder.newColumn('dest_location').withTitle('Destination Location')
        .renderWith(function(data, type, full, meta) {
          return "<input type='text' name='dest_location' value='"+full.dest_location+"' class='smallbox'>"
        }),
        DTColumnBuilder.newColumn('suggested_qty').withTitle('Suggested Qty')
        .renderWith(function(data, type, full, meta) {
          return "<input type='text' name='suggested_qty' value='"+full.suggested_qty+"' class='smallbox'>"
        }),
        DTColumnBuilder.newColumn('remarks').withTitle('Remarks')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
      vm.dtInstance.reloadData();
      vm.bt_disable = true;
    };

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    vm.process = false;
    vm.calculate_now = calculate_now;
    function calculate_now() {
      var data = [];
      vm.process = true;
      vm.service.apiCall('ba_to_sa_calculate_now/', 'POST', data).then(function(data){
        if(data.message) {
          console.log(data.data);
          colFilters.showNoty(data.data);
          reloadData();
          vm.process = false;
        }
      })
    }

    vm.process = false;
    vm.ba_to_sa_cal = ba_to_sa_cal;
    function ba_to_sa_cal() {
      console.log(vm.selected);
      var data = [];
      var rows = $($(".custom-table:visible")).find("tbody tr");
      angular.forEach(vm.selected, function(k,v){
        if(k) {
          var row = rows[v];
          data.push({name: 'data_id', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.data_id})
          data.push({name: 'sku_code', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.sku_code})
          data.push({name: 'avg_sales_day', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.avg_sales_day})
          data.push({name: 'cumulative_contribution', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.cumulative_contribution})
          data.push({name: 'classification', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.classification})
          data.push({name: 'mrp', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.mrp})
          data.push({name: 'weight', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.weight})
          data.push({name: 'source_location', value: $(row).find("input[name='source_location']").val()})
          data.push({name: 'dest_location', value: $(row).find("input[name='dest_location']").val()})
          data.push({name: 'replenushment_qty', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.replenushment_qty})
          data.push({name: 'suggested_qty', value: $(row).find("input[name='suggested_qty']").val()})
          data.push({name: 'remarks', value: vm.dtInstance.DataTable.context[0].aoData[v]._aData.remarks})
        }
      });
      vm.process = true;
      vm.service.apiCall('cal_ba_to_sa/', 'POST', data).then(function(data){
        if(data.message) {
          console.log(data.data);
          colFilters.showNoty(data.data);
          reloadData();
          vm.process = false;
        }
      })
    }
}
