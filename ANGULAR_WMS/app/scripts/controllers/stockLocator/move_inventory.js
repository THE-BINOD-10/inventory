;(function(){ 



  'use strict';

  angular.module('urbanApp', ['datatables'])
    .controller('MoveInventoryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'focus', '$timeout', '$modal', ServerSideProcessingCtrl]);

  function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, focus, $timeout, $modal) {
      var vm = this;
      vm.apply_filters = colFilters;
      vm.service = Service;
      vm.selected = {};
      vm.selectAll = false;
      vm.bt_disable = true;
      vm.service = Service;
      vm.industry_type = Session.user_profile.industry_type;
      vm.user_type = Session.user_profile.user_type;
      vm.batch_nos = [];
      vm.batches = {};

      vm.dtOptions = DTOptionsBuilder.newOptions()
         .withOption('ajax', {
                url: Session.url+'results_data/',
                type: 'POST',
                xhrFields: {
                  withCredentials: true
                },
                data: {'datatable': 'MoveInventory', 'special_key':'move'}
             })
         .withDataProp('data')
         .withOption('drawCallback', function(settings) {
           vm.service.make_selected(settings, vm.selected);
         })
         .withOption('processing', true)
         .withOption('serverSide', true)
         .withPaginationType('full_numbers')
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
          .withOption('rowCallback', rowCallback);

      vm.dtColumns = [
          DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
              .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                vm.selected[meta.row] = vm.selectAll;
                vm.seleted_rows.push(full);
                return vm.service.frontHtml + meta.row + vm.service.endHtml;
              }),
          DTColumnBuilder.newColumn('Source Location').withTitle('Source Location'),
          DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
          DTColumnBuilder.newColumn('Description').withTitle('Description'),
          DTColumnBuilder.newColumn('Destination Location').withTitle('Destination Location'),
          DTColumnBuilder.newColumn('Move Quantity').withTitle('Move Quantity')
      ];

      vm.dtInstance = {};

      vm.reloadData = reloadData;
      function reloadData() {
        vm.dtInstance.DataTable.draw();
        vm.bt_disable = true;
      }

      vm.excel = excel;
      function excel() {
        angular.copy(vm.dtColumns,colFilters.headers);
        angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
        colFilters.download_excel()
      }

      vm.seleted_rows = []
      function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
          if(vm.filter_enable){
            vm.filter_enable = false;
            vm.apply_filters.add_search_boxes();
          }
          return nRow;
      }

      vm.generate_data = []
      vm.confirm_move = confirm_move;
      function confirm_move() {
        for(var key in vm.selected){
          console.log(vm.selected[key]);
          if(vm.selected[key]) {
            vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[Number(key)]["_aData"]);
          }
        }
        if(vm.generate_data.length > 0) {
          console.log("call");
          vm.generate_filter_en = false;
          var data = '';
          for(var i=0; i< vm.generate_data.length; i++) {
            data += $(vm.generate_data[i][""]).attr("name")+"="+$(vm.generate_data[i][""]).attr("value")+"&";
          }
          vm.service.apiCall('confirm_move_inventory/?'+data.slice(0,-1)).then(function(data){
            if(data.message) {
              colFilters.showNoty(data.data);
              reloadData();
              vm.bt_disable = true;
            }
          });
          vm.generate_data = [];
        }
      }

      vm.get_sku_batches = function(sku_code){
        if(sku_code && vm.industry_type==="FMCG"){
          vm.service.apiCall('get_sku_batches/?sku_code='+sku_code).then(function(data){
            if(data.message) {
              vm.batches = data.data.sku_batches;
              vm.batch_nos = Object.keys(vm.batches);
            }
          });
        }
      }

      /*vm.batch_wise_mrps = [];
      vm.batch_num_mrp = true;
      vm.checkSearchValue = function(batch_num){
        if (batch_num) {
          vm.service.apiCall('get_batch_wise_mrps/?'+batch_num).then(function(data){
            if(data.message) {

              vm.batch_num_mrp = false;
              vm.batch_wise_mrps = data.data.mrps;
            } else {
              vm.batch_num_mrp = true;
              vm.batch_wise_mrps = [];
              Service.showNoty(data.message, 'warning');
            }
          });
        }
      }*/

      vm.add = add;
      function add() {
        angular.copy(vm.empty_data, vm.model_data);
        $state.go('app.stockLocator.MoveInventory.Inventory');
      }

      //vm.move_location_inventory = move_location_inventory;
      vm.move_location_inventory = function() {
        angular.copy(vm.empty_data, vm.model_data);
        $state.go('app.stockLocator.MoveInventory.MoveLocationInventory');
      };

      vm.close = close;
      function close() {
        vm.model_imei = {};
        $state.go('app.stockLocator.MoveInventory');
      }

      vm.message = "";
      vm.empty_data = {
                        'wms_code':'',
                        'source_loc': '',
                        'dest_loc': '',
                        'quantity': ''
                      }
      vm.model_data = {};
      angular.copy(vm.empty_data, vm.model_data);

      vm.submit =submit;
      function submit(data) {
        if(data.$valid) {
          var elem = angular.element($('form'));
          elem = elem[0];
          elem = $(elem).serializeArray();
          vm.service.apiCall('insert_move_inventory/', 'GET', elem, true).then(function(data){
            if(data.message) {
              if (data.data == "Added Successfully") {
                vm.close()
                angular.extend(vm.model_data, vm.empty_data);
              } else {
                Service.showNoty(data.data, 'warning');
              }
            }
          });
        }
      }

      vm.move_loc_submit = function move_loc_submit(data) {
        if(data.$valid) {
          var elem = angular.element($('form'));
          elem = elem[0];
          elem = $(elem).serializeArray();
          vm.service.apiCall('confirm_move_location_inventory/', 'POST', elem, true).then(function(data){
            if(data.message) {
              if(data.data == "Moved Successfully") {
                vm.close();
                angular.extend(vm.model_data, vm.empty_data);
              } else {
               Service.showNoty(data.data, 'warning');
              }
            }
          });
        }
      }

      vm.move_imei = function() {

        $state.go("app.stockLocator.MoveInventory.IMEI");
      }

      vm.model_imei = {};
      vm.scan_imei = function(event, field) {
        if ( event.keyCode == 13 && field) {

          vm.service.apiCall('get_imei_details/', 'GET', {imei:field}, true).then(function(data){

            if(!data.data.result) {
              vm.model_imei = data.data.data;
              vm.model_imei["display_details"]= true;
              if(vm.model_imei.status = "accepted") {

                vm.model_imei["show_options"] = true;
                focus('reason');
              }
              $timeout(function(){$scope.$apply()},200);
            } else {

              vm.model_imei = {}
              colFilters.showNoty(data.data.data);
            }
          })
          vm.imei="";
        }
      }

      vm.submit_imei = function(data){

        if(data.$valid) {

          var send = $("form:visible").serializeArray();
          vm.service.apiCall("change_imei_status/", 'POST', send, true).then(function(data){

            if(data.message) {
              colFilters.showNoty(data.data.message);
              vm.model_imei = {};
              focus('focusIMEI');
            }
            console.log(data);
          })
        }
      }

      //margin value
    vm.marginData = {margin_type: '', margin: 0, margin_percentage: 0, margin_value: 0, is_margin_percentage: true,
                     industry_type: vm.industry_type, user_type: vm.user_type};
    vm.add_sku_substitute = function() {

      var mod_data = vm.marginData;
      var modalInstance = $modal.open({
        templateUrl: 'views/stockLocator/toggles/update_sku_substitute.html',
        controller: 'skuSubstitute',
        controllerAs: '$ctrl',
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
         vm.marginData = selectedItem;
         if (vm.marginData.margin_type == 'Margin Percentage') {
           vm.marginData.is_margin_percentage = true;
           vm.marginData.margin = vm.marginData.margin_percentage;
         } else {
           vm.marginData.is_margin_percentage = false;
           vm.marginData.margin = vm.marginData.margin_value;
         }
      })
    }
  }

  angular.module('urbanApp').controller('skuSubstitute', function ($modalInstance, $modal, items, Service, colFilters) {
    var $ctrl = this;
    $ctrl.marginData = items;
    $ctrl.service = Service;
    $ctrl.model_data = {};
    $ctrl.industry_type = items.industry_type;
    $ctrl.user_type = items.user_type;
    $ctrl.model_data.src_available_quantity = 0;
    $ctrl.data_available = true;
    $ctrl.success_resp = false;
    $ctrl.disabled_button = false;
    $ctrl.model_data.src_quantity = 0;
    $ctrl.model_data.dest_info = [{dest_sku_code:'', dest_quantity:'', dest_location:'', batch_number:'', mrp:''}];
    $ctrl.batch_nos = [];
    $ctrl.batches = {};
    $ctrl.cols = 2;
    if (!$ctrl.industry_type) {
      $ctrl.cols = 3;
    }

    $ctrl.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

    $ctrl.get_sku_batches = function(sku_code){
        if(sku_code && $ctrl.industry_type==="FMCG"){
          $ctrl.service.apiCall('get_sku_batches/?sku_code='+sku_code).then(function(data){
            if(data.message) {
              $ctrl.batches = data.data.sku_batches;
              $ctrl.batch_nos = Object.keys($ctrl.batches);
            }
          });
        }
      }

    $ctrl.update_dest_info = update_dest_info;
    function update_dest_info(index, data, last) {
      console.log(data);
      if (last && (!data.dest_sku_code)) {
        colFilters.showNoty("Please fill existing record properly");
        return false;
      }
      if (last) {
        $ctrl.model_data.dest_info.push({dest_sku_code:'', dest_quantity:'', dest_location:'', batch_number:'', mrp:''});
      } else {
        $ctrl.model_data.dest_info.splice(index,1);
        // $ctrl.cal_total();
      }
    }

    $ctrl.empty_sku =function(){

      if (!$ctrl.model_data.src_sku_code) {
      
        $ctrl.model_data.src_location = "";
        $ctrl.model_data.src_available_quantity = 0;
        $ctrl.empty_input_fields();
      }
    }

    $ctrl.check_validation = function(){
      
      if ($ctrl.model_data.src_quantity) {

        if ($ctrl.model_data.src_quantity > $ctrl.model_data.src_available_quantity) {

          colFilters.showNoty("You have entered mote than "+$ctrl.model_data.src_available_quantity+", Please continue with available quantity");
          $ctrl.model_data.src_quantity = $ctrl.model_data.src_available_quantity;
        }
      } else {

        $ctrl.empty_input_fields();
      }
    }

    $ctrl.empty_input_fields = function(){

        $ctrl.model_data.src_quantity = "";
        $ctrl.model_data.dest_sku_code = "";
        $ctrl.model_data.dest_quantity = "";
        $ctrl.model_data.dest_location = "";
    }

    $ctrl.margin_types = ['Margin Percentage', 'Margin Value'];

    $ctrl.check_sku_code = function($items, location, sku){

      $ctrl.sku = sku;

      if (sku == 'src_sku') {

        $ctrl.data_available = false
        $ctrl.model_data.src_available_quantity = 0;
      }
      
      if (!$ctrl.model_data.src_available_quantity) {

        $ctrl.model_data.src_available_quantity = 0;
      }

      var send = {sku_code: $items.wms_code, location: location};

      $ctrl.get_avb_quantity(send, sku);
    }

    $ctrl.check_loc_wise_qty = function(sku, location, sku_type){

      var send = {sku_code: sku, location: location};
      $ctrl.get_avb_quantity(send, sku_type);
    }

    $ctrl.get_avb_quantity = function(send, sku_type){
      
      $ctrl.service.apiCall("get_sku_stock_check/", 'GET', send, true).then(function(data){
       
        if (data.data.status) {
       
          if (sku_type == "src_sku") {
       
            $ctrl.model_data.src_available_quantity = data.data.available_quantity;
          }
        } else {

          $ctrl.model_data.src_available_quantity = 0;
        }

        $ctrl.empty_input_fields();

        $ctrl.data_available = true;
        $ctrl.api_message = data.data.message;
      });

      if($ctrl.model_data.src_sku_code == $ctrl.model_data.dest_sku_code) {

        $ctrl.model_data.dest_sku_code = '';
        colFilters.showNoty("You have entered same SKU code, Please try with another SKU code");
      }
    }

    $ctrl.submit = function (data) {
      
      if(data.$valid) {

        $ctrl.disabled_button = true;  
        $ctrl.success_resp = true;
        var elem = angular.element($('form'));
        elem = $(elem).serializeArray();

        $ctrl.service.apiCall("confirm_sku_substitution/", 'POST', elem, true).then(function(response){
          
          if(response.data == 'Successfully Updated'){
          
            console.log(response);
            $modalInstance.close($ctrl.marginData);
          }

          $ctrl.api_message = response.data;
          $ctrl.success_resp = false;
        });

        $ctrl.disabled_button = false;
      }
    };

    $ctrl.close = function () {
      
      $modalInstance.dismiss('cancel');
    };
  });

})();
