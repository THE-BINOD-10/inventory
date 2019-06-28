'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SkuClassificationTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
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
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
      // DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
      //     .renderWith(function(data, type, full, meta) {
      //       if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
      //           vm.selected = {};
      //         }
      //       vm.selected[meta.row] = vm.selectAll;
      //       vm.seleted_rows.push(full);
      //       return vm.service.frontHtml + meta.row + vm.service.endHtml;
      //     }),

        DTColumnBuilder.newColumn('Sku Code').withTitle('Sku Code'),
        DTColumnBuilder.newColumn('avg_sales_day').withTitle('Avg Sales/Day'),
        DTColumnBuilder.newColumn('cumulative_contribution').withTitle('Cumulative Contribution'),
        DTColumnBuilder.newColumn('classification').withTitle('Classification'),
        DTColumnBuilder.newColumn('mrp').withTitle('MRP'),
        DTColumnBuilder.newColumn('source_location').withTitle('Source Location')
        .renderWith(function(data, type, full, meta) {
          return "<input type='text' class='form-control detectTab' readonly name='source_location' value='"+full.source_location+"' class='smallbox'>"
        }),
        DTColumnBuilder.newColumn('dest_location').withTitle('Destination Location')
        .renderWith(function(data, type, full, meta) {
          return "<input type='text' name='dest_location' value='"+full.dest_location+"' class='smallbox'>"
        }),
        DTColumnBuilder.newColumn('replenushment_qty').withTitle('Replenushment Qtyt')
        .renderWith(function(data, type, full, meta) {
          return "<input type='text' name='replenushment_qty' value='"+full.replenushment_qty+"' class='smallbox'>"
        }),
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
                vm.update = true;
                vm.title = "Update SkuClassification";
                vm.message ="";
                $state.go('app.stockLocator.SkuClassification.update');
                $timeout(function () {
                  $(".customer_status").val(vm.model_data.status);
                }, 500);
            });
        });
    }

  var empty_data = {sku_code: "", avg_sales_day: "",cumulative_contribution: "", classification: "", mrp: "", source_location : "", dest_loc: "", replenushment_qty: ""};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add SkuClassification";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.stockLocator.SkuClassification');
  }

  vm.add = add;
  function add() {

    vm.base();
    $state.go('app.stockLocator.SkuClassification.update');
  }

  vm.skuclassification_insert = function(url) {
    var send = {}
    var send = $("form").serializeArray()
    var data = $.param(send);
    vm.service.apiCall(url, 'POST', send, true).then(function(data){
      if(data.message) {
        if(data.data == 'Added Successfully' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = function(data) {

    if (data.$valid) {
      if ("Add SkuClassification" == vm.title) {
        vm.skuclassification_insert('insert_skuclassification/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.skuclassification_insert('insert_skuclassification/');
      }
    }
  }
}
