'use strict';

function appCreateOrders($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth) {

  $scope.msg = "start";
  var vm = this;

  vm.brand_size_data = [];//To get Sizes for some brands
  vm.size_filter = {};//Size Filter Search
  vm.show_no_data = false;//Show No Data
  vm.size_filter_show = false;
  vm.size_filter_data = {};
  vm.size_toggle = true;
  vm.brand_size_collect = {};

  vm.order_type_value = "offline";
  vm.service = Service;
  vm.company_name = Session.user_profile.company_name;
  vm.model_data = {}

  var empty_data = {data: [{sku_id: "", quantity: "", invoice_amount: "", price: "", tax: "", total_amount: "", unit_price: ""}], 
                            customer_id: "", payment_received: "", order_taken_by: "", other_charges: [], shipment_time_slot: "", remarks: ""};

  angular.copy(empty_data, vm.model_data);


  vm.selected = {}

  vm.categories = [];
  vm.category = "";
  vm.brand = "";

  function change_filter_data() {
    var data = {brand: vm.brand, category: vm.category, is_catalog: true, sale_through: vm.order_type_value};
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){

      if(data.message) {

        vm.categories = data.data.categories;

	vm.brands = data.data.brands;
	if (vm.brands.length === 0){
	  vm.details = false;
	}
        vm.brands_images = {'6 Degree': 'six-degrees.jpg', 'AWG (All Weather Gear)': 'awg.jpg', 'BIO WASH': 'bio-wash.jpg', 
	'Scala': 'scala.jpg','Scott International': 'scott.jpg', 'Scott Young': 'scott-young.jpg', 'Spark': 'spark.jpg', 
	'Star - 11': 'star-11.jpg','Super Sigma': 'super-sigma-dryfit.jpg', 'Sulphur Cotton': 'sulphur-cottnt.jpg', 'Sulphur Dryfit': 'sulphur-dryfit.jpg', 'Spring': 'spring.jpg', '100% Cotton': '100cotton.jpg', 'Sprint': 'sprint.jpg', 'Supreme': 'supreme.jpg', 'Sport': 'sport.jpg'}

        vm.brands_logos = {'6 Degree': 'six-degrees-1.png', 'AWG (All Weather Gear)': 'awg-1.png', 'BIO WASH': 'bio-wash-1.png',
        'Scala': 'scala-1.png','Scott International': 'scott-1.png', 'Scott Young': 'scott-young-1.png', 'Spark': 'spark-1.png',
        'Star - 11': 'star-11-1.png','Super Sigma': 'super-sigma-dryfit-1.png', 'Sulphur Cotton': 'sulphur-cottnt-1.png',                             'Sulphur Dryfit': 'sulphur-dryfit-1.png', 'Spring': 'spring-1.png', '100% Cotton': '100-cotton-1.png', 'Sprint': 'sprint-1.png',
        'Supreme': 'supreme-1.png', 'Sport': 'sport-1.png'}
        vm.change_brand('');
      }
    });
  }
  change_filter_data();

  vm.style = "";
  vm.catlog_data = {data: [], index: ""}

  vm.loading = true;

  vm.size_form_data = function() {
    var formdata = $('#size_form').serializeArray();
    var size_stock = {};
    $(formdata).each(function(index, obj) {
        if(obj.value) {
          size_stock[obj.name] = obj.value;
        }
    });
    size_stock = JSON.stringify(size_stock);
    return size_stock;
  }

  vm.tag_details = function(cat_name, brand) {

    //angular.copy([], vm.catlog_data.data);

    if (vm.category == cat_name) {

      return false;
    }

    vm.loading = true;
    vm.category = cat_name;

    if (cat_name == "All") {
      cat_name = "";
    }

    var size_stock = "";

    if($.type(vm.size_filter_data) != "string"){
      size_stock = JSON.stringify(vm.size_filter_data);
    } else {
      size_stock = vm.size_filter_data;
    }

    vm.catlog_data.index = ""
    var data = {brand: vm.brand, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true,
                sale_through: vm.order_type_value, size_filter:size_stock}
    vm.scroll_data = false;

    vm.getingData(data).then(function(data) {
      if(data == 'done') {
        var data = {data: vm.gotData};
    //vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(data) {

	//  if(data.message) {

        angular.copy([], vm.catlog_data.data);
        vm.catlog_data.index = data.data.next_index;
	    angular.forEach(data.data.data, function(item){
          vm.catlog_data.data.push(item);
        })
        vm.scroll_data = true;
  	//  }
	  vm.loading = false;
    //})
      }
    })

  }

  vm.gotData = {};
  vm.data_loading = false;
  vm.getingData = function(data) {

    if(vm.data_loading) {

      vm.cancel();
      vm.data_loading = false;
    }

    vm.data_loading = true;
    var canceller = $q.defer();
    vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(response) {
      if(response.message) {
        vm.gotData = response.data;
        console.log("done");
        canceller.resolve("done");
        vm.data_loading = false;
      }
    });
    vm.cancel = function() {
      console.log("cancel")
      canceller.resolve("cancelled");
    };
    return canceller.promise;
  }

  vm.get_category = function(status, scroll) {

    vm.loading = true;
    vm.scroll_data = false;
    vm.show_no_data = false;
    var size_stock = "";
    var cat_name = vm.category;

    if(vm.category == "All") {
      cat_name = "";
    }

    if($.type(vm.size_filter_data) != "string"){
      size_stock = JSON.stringify(vm.size_filter_data);
    } else {
      size_stock = vm.size_filter_data;
    }

    var data = {brand: vm.brand, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true,
                sale_through: vm.order_type_value, size_filter: size_stock }

    vm.getingData(data).then(function(data) {
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
          vm.catlog_data.data.push(item);
        })
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
    })
  }

  vm.scroll_data = true;
  vm.scroll = function(e) {

    console.log("scroll")
    if($(".render-items:visible").length && vm.scroll_data) {

      if(vm.catlog_data.index) {
        var data = vm.catlog_data.index.split(":");
        if((Number(data[1])-Number(data[0])) == 20){
          vm.get_category(false, true);
        }
      }
    }
  }

  vm.filter_change = function() {

    vm.catlog_data.index = "";
    angular.copy([], vm.catlog_data.data);
    vm.category = '';
    var all = $(".cat-tags");
    vm.get_category(true);
  }

  vm.all_cate = [];
  vm.change_brand = function(data) {

    vm.brand = data;
    vm.catlog_data.index = "";
    angular.copy([], vm.catlog_data.data);
    vm.category = '';
    vm.style='';
    vm.size_filter_show=false;

    //vm.sizeform('clear');
        $('#size_form').trigger('reset');
        vm.size_filter = ""; 
        vm.size_filter_show = false;
        vm.size_filter_data = {}; 
        vm.catlog_data.index = ""; 
        vm.catlog_data.data = []; 
        var size_stock = {}; 
        var stock_qty = {}; 
        var formdata = $('#size_form').serializeArray();
        $(formdata).each(function(index, obj) {
          if(obj.value) {
            size_stock[obj.name] = obj.value;
          }
        })

        vm.size_filter = size_stock;
        //stock_qty['size_filter'] = JSON.stringify(size_stock);


    var all = $(".cat-tags");
    var data = {brand: vm.brand, sale_through: vm.order_type_value, size_filter: JSON.stringify(size_stock)}
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){
      if(data.message) {

        vm.all_cate = data.data.categories;
        if(vm.all_cate.length> 0) {
          vm.all_cate.push("All")
          vm.category = "All"
          vm.get_category(true);
        }
        vm.brand_size_collect = data.data.size;
        vm.brand_size_data = $.unique(data.data.size.type1)
      }
    })
  }

  vm.change_size_type = function(toggle) {
      vm.brand_size_data = vm.brand_size_collect.type1;
      if (toggle == true && !$.isEmptyObject(vm.brand_size_collect.type2)){
        vm.brand_size_data = vm.brand_size_collect.type2;
      }
    vm.size_toggle = !(toggle)
  }

  vm.show = function() {

    vm.base();
    vm.model_data.template_value = "";
    vm.model_data.template_type = ""
    $state.go('app.outbound.CreateOrders.CreateCustomSku');
  }

 vm.base = function() {

    vm.title = "Create Custom SKU";
    vm.service.apiCall('get_sku_field_names/','GET',{'field_type':'create_orders'}).then(function(data){

      if(data.message) {
    	vm.template_types = data.data.template_types;
        vm.model_data.template_type = vm.template_types[0].field_value;
        vm.pop_data.sizes_list = data.data.sizes_list;
      }
    })
  }


  vm.check_stock = true;
  vm.enable_stock = function(){
    if(vm.check_stock) {
      vm.check_stock = false;
    } else {
      vm.check_stock = true;
    }
  }

  vm.final_data = {total_quantity:0,total_amount:0}
  vm.cal_total = function() {

    vm.final_data.total_quantity = 0;
    vm.final_data.total_amount = 0;
    angular.forEach(vm.model_data.data, function(record){
      vm.final_data.total_amount += Number(record.total_amount);
      vm.final_data.total_quantity += Number(record.quantity);
    })
    if(vm.model_data.other_charges) {
      angular.forEach(vm.model_data.other_charges, function(record){
        if(record.amount){
          vm.final_data.total_amount += Number(record.amount);
        }
      })
    }
  }
  vm.cal_percentage = function(data) {

    var per = Number(data.tax);
    data.total_amount = ((Number(data.invoice_amount)/100)*per)+Number(data.invoice_amount);
    vm.cal_total();
  }

  vm.change_unit_price = function(data) {
    data.invoice_amount = Number(data.price)*Number(data.quantity);
    vm.cal_percentage(data);
  }

  vm.lions = false;

  vm.tax = 0;
  vm.model_data.data[0].tax = vm.tax;
  empty_data.data[0].tax = vm.tax;

  //Order type 
  vm.order_type = false;
  vm.order_type_value = "offline"
  vm.change_order_type = function() {

    vm.catlog_data.index = "";
    vm.get_order_type();
    var data = {is_catalog: true, sale_through: vm.order_type_value};
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){

      if(data.message) {

        vm.brands = data.data.brands;
      }
    })
  }
  vm.get_order_type = function() {

    if(vm.order_type) {
      vm.order_type_value = "Online";
    } else {
      vm.order_type_value = "Offline";
    }
  }

  vm.change_tax_type = function() {

    vm.tax = vm.create_order_data.taxes[vm.model_data.tax_type];
    angular.forEach(vm.model_data.data, function(record) {
      record.tax = vm.create_order_data.taxes[vm.model_data.tax_type];
      vm.cal_percentage(record)
    })
    vm.cal_total();
  }
  vm.logout = function(){

     Auth.logout().then(function(){
       $state.go("user.sagarfab");
     })  
   }

  vm.date_changed = function(){
    //$('.datepicker').hide();
    $(this);
  }

  $( window ).resize(function() {
    vm.add_scroll();
  })

  vm.add_scroll = function(){
    $timeout(function() {
    var height = $(window).height()
    if(angular.element(".app_scroll")) {

      var header = $(".layout-header").height();
      var menu = $(".style-menu").height();
      //var search = $(".search-box").height();
      //search = (search)? search+25 : 0;
      var cart = $(".cart_button").outerHeight();
      $(".app_body").css('height',height-header-menu-cart);
      $(".app_body").css('overflow-y', 'auto');
    }
    }, 500)
  }
  vm.add_scroll();

  $scope.$watch(function(){
    vm.add_scroll();
  });

  vm.sizeform = function(form) {
    var config = {};
    vm.show_no_data = false;
    if (form == "clear") {
        $('#size_form').trigger('reset');
        vm.size_filter = "";
        vm.size_filter_show = false;
        vm.size_filter_data = {};
        vm.catlog_data.index = "";
        vm.catlog_data.data = [];
        var size_stock = {};
        var stock_qty = {};
        var formdata = $('#size_form').serializeArray();
        $(formdata).each(function(index, obj) {
        if(obj.value) {
          size_stock[obj.name] = obj.value;
        }
    });
    vm.size_filter = size_stock;
    stock_qty['size_filter'] = JSON.stringify(size_stock);
    stock_qty['brand'] = vm.brand;
    stock_qty['sale_through'] = vm.order_type_value;
    angular.copy(size_stock, vm.size_filter_data);
    vm.service.apiCall("get_sku_categories/", "GET", stock_qty).then(function(data) {
            if(data.message) {
            vm.all_cate = data.data.categories;
            if(vm.all_cate.length> 0) {
                vm.all_cate.push("All")
                vm.get_category(true);
                }
            }
    });

    } else {
    var size_stock = {};
    var stock_qty = {};
    var formdata = $('#size_form').serializeArray();
    $(formdata).each(function(index, obj) {
        if(obj.value) {
          size_stock[obj.name] = obj.value;
        }
    });
    vm.size_filter = size_stock;
    stock_qty['size_filter'] = JSON.stringify(size_stock);
    stock_qty['brand'] = vm.brand;
    stock_qty['sale_through'] = vm.order_type_value;
    vm.size_filter_show = true;
    if(angular.equals(size_stock, {})){
    vm.size_filter_show = false;
    }
    vm.catlog_data.index = "";
    vm.catlog_data.data = [];

    angular.copy(size_stock, vm.size_filter_data);
    vm.service.apiCall("get_sku_categories/", "GET", stock_qty).then(function(data) {
      if(data.message) {
        vm.all_cate = data.data.categories;
        if(vm.all_cate.length> 0) {
          vm.all_cate.push("All")
          vm.get_category(true);
        }
      }
    });
    }
  }

}

angular
  .module('urbanApp')
  .controller('appCreateOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', appCreateOrders]);
