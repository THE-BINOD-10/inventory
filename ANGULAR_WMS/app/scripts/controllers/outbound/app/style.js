;(function(){

'use strict';

function AppStyle($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.styleId = "";
  vm.tax_type = Session.roles.tax_type;
  vm.central_order_mgmt = Session.roles.permissions.central_order_mgmt;
  vm.order_exceed_stock = Boolean(Session.roles.permissions.order_exceed_stock);
  vm.user_type = Session.roles.permissions.user_type;
  vm.service = Service;
  vm.dis_video = false;
  vm.y_video_flag = false;
  if($stateParams.styleId){
    vm.styleId = $stateParams.styleId;
  }

  if(Session.roles.permissions.user_type == 'customer') {
    vm.wish_list = {}
  } else {
    vm.wish_list = Data.styles_data;
  }

  vm.style_headers = {};
  vm.style_detail_hd = [];
  vm.client_logo = Session.parent.logo;
  vm.api_url = Session.host;

  if (Session.roles.permissions["style_headers"]) {

    vm.en_style_headers = Session.roles.permissions["style_headers"].split(",");
  } else {

    vm.en_style_headers = [];
  }

  if(vm.en_style_headers.length == 0) {

    vm.en_style_headers = ["wms_code", "sku_desc"]
  }

  vm.style_open = false;
  vm.stock_quantity = 0;
  vm.style_data = [];
  vm.style_details = {};
  vm.style_total_counts = {};
  vm.data_loading = false;
  vm.page_loading = true;
  vm.levels_data = {};

  vm.open_style = function(user_type) {

    if (vm.old_selLevel == "") {

      console.log(vm.old_selLevel);
    } else if(Number(vm.old_selLevel) >= 0 && Number(vm.old_selLevel) != Number(vm.selLevel)){

      vm.levels_data[vm.old_selLevel] = vm.style_data;
    }

    if(vm.levels_data[vm.selLevel]){

      vm.style_data = vm.levels_data[vm.selLevel];
      vm.old_selLevel = vm.selLevel;
      return false;
    }

    vm.data_loading = true;
    vm.style_data = [];
    var send = {sku_class:vm.styleId, customer_id: Session.userId, is_catalog: true, level:vm.selLevel,
                is_style_detail: true}
    Service.apiCall("get_sku_variants/", "POST", send).then(function(data) {

      if(data.message) {
        vm.style_open = true;
        vm.check_stock=true;
        var style_data = data.data.data;
        vm.sku_spl_attrs = data.data.sku_spl_attrs;
        var total_stocks = {};
        vm.charge_remarks = data.data.charge_remarks;
        vm.generic_wharehouse_level = data.data.gen_wh_level_status;

        if (data.data.freight_charges == 'true') {
          vm.freight_charges = data.data.freight_charges;
        }

        if (Object.keys(vm.style_details).length === 0) {
          vm.style_details = style_data[0];
        }
        vm.y_video_flag = vm.style_details.youtube_url ? true : false;
        $('.youtube_thumbnaile_elem').html('<object width="100" height="70" data="'+vm.style_details.youtube_url+'"></object>');
        $('.youtube_video_play_elem').html('<object style="margin-top:49px" width="100%" height="100%" data="'+vm.style_details.youtube_url+'"></object>');
        $('.youtube_video_play_mb_elem').html('<object width="100%" height="100%" data="'+vm.style_details.youtube_url+'"></object>');
        vm.style_total_counts = data.data.total_qty;
        var wish_status = false;
        if(style_data.length > 0) {

          angular.forEach(style_data, function(record, index){

            var stock = 0;
            angular.forEach(data.data.lead_times, function(lead_time) {
              if(index == 0) {

                total_stocks[lead_time] = 0;
              }

              total_stocks[lead_time] += Number(record[lead_time]);
              stock += Number(record[lead_time]);
            });

            vm.total_quantity = 0;
            record['unit_rate'] = record.price;
            record['row_total_price'] = record.price * 0;
            record['level'] = vm.selLevel;
            record['overall_sku_total_quantity'] = stock;

            record['org_price'] = record.price;

            if (vm.total_quantity > 0 || Session.roles.permissions.user_type == 'customer') {

              record['quantity_status'] = true;
            }

            vm.stock_quantity = vm.stock_quantity + Number(record.physical_stock) + Number(record.all_quantity);

            if(Session.roles.permissions.user_type != 'customer' && vm.wish_list[record.wms_code+":"+vm.selLevel]){
              wish_status = true;
              record.quantity = vm.wish_list[record.wms_code+":"+vm.selLevel].quantity;
            }
          });

          vm.levels_data[vm.selLevel] = {
                                          'data': style_data,
                                          'lead_times': data.data.lead_times,
                                          'total_stocks': total_stocks,
                                          'total_price': 0
                                        };

          vm.style_data = vm.levels_data[vm.selLevel];
          vm.old_selLevel = vm.selLevel;

          vm.page_loading = false;
        }

        // vm.freight_charges = data.data.freight_charges;
        vm.style_headers = data.data.style_headers;

        if (data.data.gen_wh_level_status == 'true') {

          vm.gen_wh_lead_tm = true;
          vm.style_detail_hd = data.data.lead_times;
        } else{

          vm.def_lead_tm = true;
          wish_status = false;
          vm.style_detail_hd = Object.keys(vm.style_headers);
        }

        if(wish_status) {
          vm.update_levels(0);
        } else {
          vm.cal_wish_list();
        }
      }
      vm.data_loading = false;
    });
    vm.style_total_quantity = 0;
  }

  vm.old_selLevel = '';
  vm.getLevelData = function(){

    vm.service.apiCall('get_levels/', 'GET', {sku_class:vm.styleId, customer_id: Session.userId}).then(function(data){

      vm.levels = data.data;
      vm.selLevel = Number(data.data[0].warehouse_level);
      vm.open_style();
    });
  }

  vm.getLevelData();

  vm.get_total_level_quantity = function(index) {

    var total_quantity = 0;

    angular.forEach(vm.levels_data, function(record, key){

      angular.forEach(record.data,function(sku){
        if (sku.quantity) {
          total_quantity += Number(sku.quantity);
        }
      });

      // if (record.data[index].quantity) {

      //   total_quantity += Number(record.data[index].quantity);
      // }
    });
    return total_quantity;
  }

  vm.sel_items_total_price = 0;
  vm.sel_items_tax = 0;
  vm.wish_list_total_qty = 0;
  vm.update_levels = function(index){

    vm.sel_items_total_price = 0;
    vm.sel_items_tax = 0;
    vm.sel_items_total_quantity = 0;
    var total_quantity = vm.get_total_level_quantity(index);
    angular.forEach(vm.levels_data, function(level_data, level_name) {
      if (level_data.data[index].quantity) {

        if (Session.roles.permissions.user_type == 'reseller' && vm.selLevel==0 && level_name!=vm.selLevel) {
          level_data.data[index].quantity = 0;
          Service.showNoty('Level-'+level_name+' quantity removed', 'warning');
        }
        level_data.data[index].price = vm.priceRangesCheck(level_data.data[index], total_quantity);
        level_data.data[index].unit_rate = level_data.data[index].price;
        level_data.data[index].row_total_price = level_data.data[index].price * level_data.data[index].quantity;
        vm.wish_list[level_data.data[index].wms_code+":"+level_name] = level_data.data[index];
      } else {
        if (vm.wish_list[level_data.data[index].wms_code+":"+level_name]){
          delete vm.wish_list[level_data.data[index].wms_code+":"+level_name];
        }
      }
      Data.styles_data = vm.wish_list;

      level_data.quantity = 0;
      level_data.total_price = 0;
      angular.forEach(level_data.data, function(data){

        var quantity = (data.quantity) ? data.quantity : 0;
        level_data.quantity += Number(quantity);
        level_data.total_price += data.row_total_price;
        data.price = vm.priceRangesCheck(data, total_quantity);
        data.unit_rate = data.price;
        data.row_total_price = data.price * data.quantity;
      });
      vm.sel_items_total_price += level_data.total_price;
      vm.sel_items_total_quantity += level_data.quantity;
      vm.sel_items_tax = 0;
      if (Number(level_data.data[0].quantity) && level_data.data[0].taxes[0]) {
        vm.sel_items_tax = (vm.sel_items_total_price / 100) * (level_data.data[0].taxes[0].cgst_tax + level_data.data[0].taxes[0].sgst_tax + level_data.data[0].taxes[0].igst_tax);
      }
    });
    vm.sel_items_total_price += vm.sel_items_tax;
    vm.cal_wish_list()
  }

  vm.wish_data = {total_tax: 0, total_amount: 0};
  vm.cal_wish_list = function() {

    vm.wish_data = {total_tax: 0, total_amount: 0, total_qty: 0};
    angular.forEach(vm.wish_list, function(data, key){

      var temp_amount = data.row_total_price;
      if(data.taxes[0]) {
        vm.wish_data.total_tax  += (temp_amount / 100) * (data.taxes[0].cgst_tax + data.taxes[0].sgst_tax + data.taxes[0].igst_tax);
      }
      vm.wish_data.total_amount += temp_amount;
      vm.wish_data.total_qty += Number(data.quantity);
    });
    vm.wish_data.total_amount += vm.wish_data.total_tax;
  }

  vm.check_quantity = function(sku){
    if (sku.quantity > sku.overall_sku_total_quantity) {

      vm.full_quantity = true;
      sku.quantity = sku.overall_sku_total_quantity;
      vm.service.showNoty("You can add "+sku.overall_sku_total_quantity+" items only", "success", "topRight");
    } else {
      vm.full_quantity = false;
    }
  }

  vm.style_total_quantity = 0;
  vm.change_style_quantity = function(data, row, index){
    if (Boolean(Session.roles.permissions.order_exceed_stock)) {
      if ((row.all_quantity - row.blocked_quantity) < parseInt(row.quantity)) {
        vm.service.showNoty("Order quantity can't exceed the stock available");
        row.quantity = 0;//(row.all_quantity - row.blocked_quantity).toString();
        return;
      }
    }
    if (Number(row.quantity) == 0) {

      row.unit_rate = row.org_price;
      row.row_total_price = 0;
      vm.sel_items_tax = 0;
    }

    if (Session.roles.permissions.user_type != 'customer') {

      if (Session.roles.permissions.user_type == 'reseller' && vm.selLevel  != 0) {

        if (vm.selLevel >= 1 && vm.selLevel != 3) {
        // if (vm.selLevel == 1 && vm.selLevel != 2) {

          if ((vm.levels_data[0].data[index].overall_sku_total_quantity != 0 && !vm.levels_data[0].data[index].quantity) ||
            vm.levels_data[0].data[index].overall_sku_total_quantity > Number(vm.levels_data[0].data[index].quantity)) {

            var available_qty = 0;
            if (vm.levels_data[0].data[index].quantity) {

              available_qty = Number(vm.levels_data[0].data[index].overall_sku_total_quantity) -
              Number(vm.levels_data[0].data[index].quantity);
            } else {

              available_qty = Number(vm.levels_data[0].data[index].overall_sku_total_quantity);
            }
            vm.service.showNoty("The <b>"+vm.levels_data[0].data[index].wms_code+"</b> SKU having <b>"+available_qty+"</b> quantity in <b>Level-0</b>. Please consider it.", "success", "topRight");
            var level = Number(row.level);
            vm.levels_data[level].data[index].quantity = 0;
            vm.selLevel  = level;
            return false;
          }
        } else if (vm.selLevel == 3) {

            var level_0_1_ovr_sku_tot_qty = 0;
            var level_0_1_qty = 0;
            var level_0_1_available_qty = 0;

            angular.forEach(vm.levels_data, function(sku){

              if (sku.data[index].level == 0 || sku.data[index].level == 1) {

                if (!sku.data[index].quantity) {

                  sku.data[index]['quantity'] = 0;
                }
                level_0_1_ovr_sku_tot_qty += Number(sku.data[index].overall_sku_total_quantity);
                level_0_1_available_qty += Number(sku.data[index].overall_sku_total_quantity) - Number(sku.data[index].quantity);
                level_0_1_qty += Number(sku.data[index].quantity);
              }
            });

            if ((level_0_1_ovr_sku_tot_qty != 0 && !level_0_1_qty) || level_0_1_available_qty > level_0_1_qty) {

              vm.service.showNoty("The <b>"+vm.levels_data[0].data[index].wms_code+"</b> SKU having <b>"+level_0_1_available_qty+"</b> quantity in <b>Level-0 or Level-1</b>. Please consider it.", "success", "topRight");
              var level = Number(row.level);
              vm.levels_data[level].data[index].quantity = 0;
              vm.selLevel  = level;
              return false;
            }
        }
      }
      vm.check_quantity(row);
    } else {
      console.log(index);
    }
    vm.update_levels(index);
  }



  vm.priceRangesCheck = function(record, quantity){

    if (record.price_ranges) {

      var prices = record.price_ranges;

      for (var priceRng = 0; priceRng < prices.length; priceRng++) {

        if(quantity >= prices[priceRng].min_unit_range && quantity <= prices[priceRng].max_unit_range) {

          return prices[priceRng].price;
        }
      }

      if (priceRng >= prices.length ) {

        return prices[prices.length-1].price;
      }
    } else {

      return record.price;
    }
  }

  var empty_data = {data: []}

  vm.add_to_cart = function(levels_data) {

    // if(vm.sel_items_total_price > 0) {
    if(vm.wish_data.total_qty > 0) {

      var send = [];

      //angular.forEach(vm.levels_data, function(level_data, level_name) {

      //  angular.forEach(level_data.data, function(data){
        angular.forEach(vm.wish_list, function(data, name) {
          if (data['quantity']) {

            var temp = {sku_id: data.wms_code, quantity: Number(data.quantity), invoice_amount: data.price * Number(data.quantity), price: data.price, tax: vm.tax, image_url: data.image_url, level: data.level, overall_sku_total_quantity: data.overall_sku_total_quantity}
            temp['total_amount'] = ((temp.invoice_amount / 100) * vm.tax) + temp.invoice_amount;
            send.push(temp);
          }
        });
      //});

      vm.insert_customer_cart_data(send);
    } else {

      vm.service.showNoty("Please Enter Quantity", "success", "bottomRight");
    }
  }

  vm.insert_customer_cart_data = function(data){

    var send = JSON.stringify(data);
    vm.place_order_loading = true;

    vm.service.apiCall('insert_customer_cart_data/?data='+send).then(function(data){

       if (data.message) {

        Data.styles_data = {};
        vm.service.showNoty("Succesfully Added to Cart", "success", "bottomRight");
        $state.go('user.App.Cart');
        Data.styleId = vm.styleId;
       }
    });

    vm.place_order_loading = true;
  };

  vm.tax = 0
  /*vm.get_create_order_data = function(){
    vm.service.apiCall("create_orders_data/").then(function(data){

      if(data.message) {
          if (vm.tax_type == '' || (! data.data.taxes[vm.tax_type])) {
            vm.tax =  data.data.taxes['DEFAULT'];
          }
          else {
            vm.tax =  data.data.taxes[vm.tax_type];
          }
      }
    })
  }
  vm.get_create_order_data();*/

  vm.includeDesktopTemplate = false;
  vm.includeMobileTemplate = false;
  vm.screenSize = function() {

    var screenWidth = $window.innerWidth;

    if (screenWidth < 768){

      vm.includeMobileTemplate = true;
      vm.includeDesktopTemplate = false;
    }else{

      vm.includeDesktopTemplate = true;
      vm.includeMobileTemplate = false;
    }
  }
  vm.screenSize();
  angular.element($window).bind('resize', function(){

    vm.screenSize();
  });
}

angular
  .module('urbanApp')
  .controller('AppStyle', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', AppStyle]);


})();
