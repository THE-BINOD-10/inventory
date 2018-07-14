;(function(){

'use strict';

angular.module('urbanApp')
  .factory('PagerService', PagerService)
  .controller('AppNewStyle',['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', '$rootScope', '$location', 'PagerService', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data, $rootScope, $location, PagerService) {
	
  var vm = this;
  vm.service = Service;
  vm.place_order_loading = false;
  vm.order_type_value = "offline";
  vm.show_no_data = false;
  // vm.buttons_width = (Session.roles.permissions.create_order_po)? 4: 6;

  vm.brand, vm.sub_category, vm.category, vm.style, vm.color, vm.fromPrice, vm.toPrice, vm.quantity, vm.delivery_date, 
  vm.hot_release = '';
  vm.marginData = {margin_type: '', margin: 0, margin_percentage: 0, margin_value: 0, is_margin_percentage: true, sale_through: vm.order_type_value};

  vm.location = $location.$$path;

  if (Session.roles.permissions.is_portal_lite) {
    if (vm.location == '/App/Brands' || vm.location == '/App/Categories' || vm.location == '/App/Products') {
      $state.go('user.App.newStyle');
    }
  }

  vm.get_category = function(status, scroll) {

    if(vm.showFilter) {
      return false;
    }

    if(vm.style) {

      vm.filteredStyles = [];
      vm.pagenation_count = 0;
    }

    vm.loading = true;
    vm.scroll_data = false;
    vm.show_no_data = false;
    var size_stock = "";
    var cat_name = vm.category;
    var sub_cat_name = vm.sub_category;

    if(vm.category == "All") {
      cat_name = "";
    } else if(vm.category == "") {
      vm.category = "All";
      cat_name = "";
    }

    if($.type(vm.size_filter_data) != "string"){
      size_stock = JSON.stringify(vm.size_filter_data);
    } else {
      size_stock = vm.size_filter_data;
    }

    var data = {brand: vm.brand, sub_category: sub_cat_name, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true,
                sale_through: vm.order_type_value, size_filter: size_stock, color: vm.color, from_price: vm.fromPrice,
                to_price: vm.toPrice, quantity: vm.quantity, delivery_date: vm.delivery_date, is_margin_percentage: vm.marginData.is_margin_percentage,
                margin: vm.marginData.margin, hot_release: vm.hot_release, margin_data: JSON.stringify(Data.marginSKUData.data)};

    if(status) {
      angular.copy([], vm.catlog_data.data);
    }

    getingData(data);
    /*vm.getingData(data).then(function(data) {
    if(data == 'done') {
        var data = {data: vm.gotData};
    //vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(data) {

    //  if(data.message) {

        if(status) {

          vm.catlog_data.index = "";
          angular.copy([], vm.catlog_data.data);
        }
        vm.catlog_data.index = data.data.next_index;
        
        angular.forEach(data.data.data, function(item){
          vm.required_quantity[item.variants[0].style_name] = vm.quantity;
          vm.catlog_data.data.push(item);
        });

        if(!Data.marginSKUData.category){
          Data.marginSKUData['category'] = {};
        }
        // vm.margin_add_to_categoris(data.data.data, Data.marginSKUData.category[vm.category]);
      //}
      vm.scroll_data = true;
      vm.add_scroll();
      vm.loading = false;
      if($.isEmptyObject(data.data.data)){
          vm.show_no_data = true;
      }

      if( (data.data.data).length == 0 && vm.catlog_data.index ) {
        vm.scroll_data = false;
      }
    }
    });*/
  }

  function change_filter_data() {
    var data = {brand: '', category: '', is_catalog: true, sale_through: vm.order_type_value};
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){

      if(data.message) {

        vm.main_menus = data.data.categories;
        vm.sub_menus = data.data.sub_categories;
      }
    });

    get_styles();
  }
  change_filter_data();

  vm.get_styles = get_styles;
  function get_styles(category=''){

    vm.pagenation_count = 0;
    vm.filteredStyles = [];
    vm.category = category;
    var data = {brand: vm.brand, sub_category: vm.sub_category, category: category, sku_class: vm.style, index: '', 
        is_catalog: true, sale_through: vm.order_type_value, size_filter: '', color: vm.color, from_price: vm.fromPrice,
        to_price: vm.toPrice, quantity: vm.quantity, delivery_date: vm.delivery_date, 
        is_margin_percentage: vm.marginData.is_margin_percentage, margin: vm.marginData.margin, 
        hot_release: vm.hot_release, margin_data: []};

    getingData(data);
  }

  vm.gotData = {};
  // vm.data_loading = true;
  function getingData(data) {

    vm.catDisplay = false;
    vm.data_loading = true;
    var canceller = $q.defer();
    vm.service.apiCall("get_sku_catalogs/", "POST", data).then(function(response) {
      if(response.message) {
        // response.data = {};
        vm.gotData = response.data;
        canceller.resolve("done");
        vm.data_loading = false;
        vm.showFilter = false;

        if($.isEmptyObject(response.data) || !response.data.data.length){

          vm.show_no_data = true;
        } else {

          vm.show_no_data = false;
          vm.getPagenation();
        }
      }
    });

    vm.cancel = function() {
      console.log("cancel")
      canceller.resolve("cancelled");
    };
    return canceller.promise;
  }

  vm.change_cart_quantity = function(data, stat) {

    if (stat) {
      
      if (data.quantity) {
        
        if (data.physical_stock) {

          data.quantity = Number(data.quantity) + 1;
          vm.update_customer_cart_data(data);
        } else {

          data.quantity = 0;
          Service.showNoty("Stock is not available of this sku");
        }
      } else {

        data['quantity'] = 1;
      }
      vm.change_amount(data);
    } else {

      if (Number(data.quantity)> 1) {

        data.quantity = Number(data.quantity) - 1;
        vm.change_amount(data);
        vm.update_customer_cart_data(data);
      } else {

        Service.showNoty("Sorry, Please check your quantity");
      }
    }
  }

  vm.update_customer_cart_data = function(data) {

    var send = {'sku_code': data.sku_id, 'quantity': data.quantity, 'level': 0, 'price': data.price}
    vm.service.apiCall("update_customer_cart_data/", "POST", send).then(function(response){

    });
  }

  vm.model_data = {'selected_styles':{}};

  vm.change_amount = function(data) {

    if (data.quantity == 0 || data.quantity == '' || !data.quantity) {

      Service.showNoty("You should select minimum one item");
    } else {

      if (data.physical_stock) {

        data.quantity = Number(data.quantity);
        vm.add_to_price_details(data);
      } else {

        data.quantity = 0;
        Service.showNoty("Stock is not available of this sku");
      }
    }
  }

  vm.cal_customer_cart_data = function(data){

    if (vm.model_data.selected_styles[data.id]) {

      vm.model_data.selected_styles[data.id].quantity = data.quantity;
      vm.cal_total();
    }
  }

  vm.add_to_price_details = function(data){

    if (vm.model_data.selected_styles[data.id]) {

      // vm.priceRangesCheck(data, data.quantity);
      vm.cal_customer_cart_data(data);
    } else {

      vm.priceRangesCheck(data, data.quantity);
      vm.model_data.selected_styles[data.id] = data;
      vm.cal_customer_cart_data(data);
    }
  }

  var empty_final_data = {total_quantity: 0, amount: 0, tax_amount: 0, total_amount: 0}
  vm.final_data = {};
  angular.copy(empty_final_data, vm.final_data);

  vm.cal_total = function() { // Last function

    angular.copy(empty_final_data, vm.final_data);
    angular.forEach(vm.model_data.selected_styles, function(record){

      vm.priceRangesCheck(record, record.quantity);

      vm.final_data.total_amount += Number(record.total_amount);
      vm.final_data.total_quantity += Number(record.quantity);
      vm.final_data.amount += Number(record.invoice_amount);
    })
    vm.final_data.tax_amount = vm.final_data.total_amount - vm.final_data.amount;
  };

  vm.priceRangesCheck = function(record, quantity){

    var price = record.price;
    if (record.prices) {
      
      var prices = record.prices;

      for (var priceRng = 0; priceRng < prices.length; priceRng++) {

        if(quantity >= prices[priceRng].min_unit_range && quantity <= prices[priceRng].max_unit_range) {

          price = prices[priceRng].price;
          break;
        }
      }

      if (priceRng >= prices.length ) {

        price = prices[prices.length-1].price;
      }
    }

    if (record.price != price) {

      record.price = price;
    } else {

      record.price = price;
    }
    record.invoice_amount = Number(price) * record.quantity;

    if (Number(record.quantity) && record.taxes[0]) {
      record.tax = Number(record.taxes[0].cgst_tax) + Number(record.taxes[0].sgst_tax) + Number(record.taxes[0].igst_tax);
    } else {
      record.tax = 0;
    }

    record.total_amount = ((record.invoice_amount * record.tax) / 100) + record.invoice_amount;
  }

  vm.price_details_flag = true;
  vm.add_to_cart = function(sku) {

    if(sku.quantity) {

      if (vm.model_data.selected_styles[sku.id]) {

        vm.model_data.selected_styles[sku.id]['add_to_cart'] = true;
      }

      vm.price_details_flag = false;
      if (!sku.tax) {
        sku.tax = 0;
      }
      sku['overall_sku_total_quantity'] = sku.physical_stock;

      sku['sku_id'] = sku.wms_code;
      var temp = {sku_id: sku.sku_id, quantity: Number(sku.quantity), invoice_amount: Number(sku.invoice_amount), price: sku.price, tax: sku.tax, image_url: sku.image_url, level: 0, overall_sku_total_quantity: sku.overall_sku_total_quantity}
      temp['total_amount'] = ((temp.invoice_amount / 100) * temp.tax) + temp.invoice_amount;

      vm.insert_customer_cart_data([temp]);
    } else {

      if (vm.model_data.selected_styles[sku.id]) {

        vm.model_data.selected_styles[sku.id]['add_to_cart'] = false;
      }
     
      vm.service.showNoty("Please enter quantity first");
    }

    console.log(sku);
  }

  vm.insert_customer_cart_data = function(send){

    var send = JSON.stringify(send);
    // vm.place_order_loading = true;
    
    vm.service.apiCall('insert_customer_cart_data/?data='+send).then(function(data){

      if (data.message) {



        vm.service.showNoty("Succesfully Added to Cart");
      }
    });

    // vm.place_order_loading = true;
  };

  vm.update_cartdata_for_approval = function() {
    var send = {}
    vm.service.apiCall("update_orders_for_approval/", "POST", send).then(function(response){
        if(response.message) {
          if(response.data.message == "success") {
            Data.my_orders = [];
            swal({
              title: "Success!",
              text: "Your Order Has Been Sent for Approval",
              type: "success",
              showCancelButton: false,
              confirmButtonText: "OK",
              closeOnConfirm: true
              // },
              // function(isConfirm){
              //   $state.go("user.App.Brands");
              }
            )
          } else {
            vm.insert_cool = true;
            vm.data_status = true;
            vm.service.showNoty(response.data, "danger", "bottomRight");
          }
        }
    });
  }

  //##############################Pagenation Start##############################
  vm.getPagenation = function(){

    if(vm.category == "") {
    
      vm.category = "All";
    }

    vm.pagenation_count = 0;
    vm.pagenation_data = [];

    for (var sku_var = 0; sku_var < vm.gotData.data.length; sku_var++) {
      
      vm.pagenation_count += Number(vm.gotData.data[sku_var].variants.length);
      
      for (var sku = 0; sku < vm.gotData.data[sku_var].variants.length; sku++) {

        vm.pagenation_data.push(vm.gotData.data[sku_var].variants[sku]);
      }
    }

    vm.pager = {};
    vm.setPage = setPage;

    vm.setPage(1);

    function setPage(page) {
        if (page < 1 || page > vm.pager.totalPages) {
            return;
        }

        // get pager object from service
        vm.pager = PagerService.GetPager(vm.pagenation_data.length, page);

        // get current page of items
        vm.filteredStyles = vm.pagenation_data.slice(vm.pager.startIndex, vm.pager.endIndex + 1);
    }  

  }
  
  //##############################Pagenation End##############################
} // End of funciton

//################################Pagenation Services################################
function PagerService() {
  // service definition
  var service = {};

  service.GetPager = GetPager;

  return service;

  // service implementation
  function GetPager(totalItems, currentPage, pageSize) {
      // default to first page
      currentPage = currentPage || 1;

      // default page size is 10
      pageSize = pageSize || 10;

      // calculate total pages
      var totalPages = Math.ceil(totalItems / pageSize);

      var startPage, endPage;
      if (totalPages <= 7) {
          // less than 10 total pages so show all
          startPage = 1;
          endPage = totalPages;
      } else {
          // more than 10 total pages so calculate start and end pages
          if (currentPage <= 3) {
              startPage = 1;
              endPage = 7;
          } else if (currentPage + 3 >= totalPages) {
              startPage = totalPages - 6;
              endPage = totalPages;
          } else {
              startPage = currentPage - 3;
              endPage = currentPage + 3;
          }
      }

      // calculate start and end item indexes
      var startIndex = (currentPage - 1) * pageSize;
      var endIndex = Math.min(startIndex + pageSize - 1, totalItems - 1);

      // create an array of pages to ng-repeat in the pager control
      var pages = _.range(startPage, endPage + 1);

      // return object with all pager properties required by the view
      return {
          totalItems: totalItems,
          currentPage: currentPage,
          pageSize: pageSize,
          totalPages: totalPages,
          startPage: startPage,
          endPage: endPage,
          startIndex: startIndex,
          endIndex: endIndex,
          pages: pages
      };
  }
}
})();