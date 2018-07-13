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

  vm.brand, vm.sub_category, vm.category, vm.style, vm.color, vm.fromPrice, vm.toPrice, vm.quantity, vm.delivery_date, 
  vm.hot_release = '';
  vm.marginData = {margin_type: '', margin: 0, margin_percentage: 0, margin_value: 0, is_margin_percentage: true, sale_through: vm.order_type_value};

  vm.location = $location.$$path;

  if (Session.userName == 'roopal@mieone.com') { // This condition for testing only
    if (vm.location == '/App/Brands' || vm.location == '/App/Categories' || vm.location == '/App/Products') {
      $state.go('user.App.newStyle');
    }
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

  function get_styles(){

    var data = {brand: vm.brand, sub_category: vm.sub_category, category: vm.category, sku_class: vm.style, index: '', is_catalog: true,
            sale_through: vm.order_type_value, size_filter: '', color: vm.color, from_price: vm.fromPrice,
            to_price: vm.toPrice, quantity: vm.quantity, delivery_date: vm.delivery_date, is_margin_percentage: vm.marginData.is_margin_percentage,
            margin: vm.marginData.margin, hot_release: vm.hot_release, margin_data: []};

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
        vm.gotData = response.data;
        console.log("done");
        canceller.resolve("done");
        vm.data_loading = false;
        vm.showFilter = false;

        vm.getPagenation();
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
      }
    }
  }

  vm.model_data = {'selected_styles':{}};

  vm.change_amount = function(data) {

    if (data.quantity == 0 || data.quantity == '' || !data.quantity) {

      Service.showNoty("You should select minimum one item");
    } else {

      if (data.physical_stock) {

        data.quantity = Number(data.quantity);
        vm.add_to_cart(data);
        vm.quantity_valid(data); // Maximum quantity validation
      } else {

        data.quantity = 0;
        Service.showNoty("Stock is not available of this sku");
      }
    }
  }

  vm.update_customer_cart_data = function(data){

    if (vm.model_data.selected_styles[data.id]) {

      vm.model_data.selected_styles[data.id].quantity = data.quantity;
      vm.cal_total();
    }
  }

  vm.add_to_cart = function(data){

    if (vm.model_data.selected_styles[data.id]) {

      // vm.priceRangesCheck(data, data.quantity);
      vm.update_customer_cart_data(data);
    } else {

      vm.priceRangesCheck(data, data.quantity);
      vm.model_data.selected_styles[data.id] = data;
      vm.update_customer_cart_data(data);
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
      //vm.update_customer_cart_data(record);
    } else {

      record.price = price;
    }
    record.invoice_amount = Number(price) * record.quantity;
    if (record.tax) {

      record.total_amount = ((record.invoice_amount * record.tax) / 100) + record.invoice_amount;
    } else {

      record.total_amount = record.invoice_amount;
    }
  }

  vm.add_to_cart = function(sku) {

    if(sku.quantity) {
      
      console.log(sku);
      // var send = [];
      // angular.forEach(vm.wish_list, function(data, name) {
      //   if (data['quantity']) {

      //     var temp = {sku_id: data.wms_code, quantity: Number(data.quantity), invoice_amount: data.price * Number(data.quantity), price: data.price, tax: vm.tax, image_url: data.image_url, level: data.level, overall_sku_total_quantity: data.overall_sku_total_quantity}
      //     temp['total_amount'] = ((temp.invoice_amount / 100) * vm.tax) + temp.invoice_amount;
      //     send.push(temp);
      //   }
      // });

      // vm.insert_customer_cart_data(send);
    } else {
     
      vm.service.showNoty("Please Enter Quantity");
    }
  }


  //##############################Pagenation Start##############################
  vm.getPagenation = function(){
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