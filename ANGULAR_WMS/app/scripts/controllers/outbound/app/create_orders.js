;(function() {

'use strict';

function appCreateOrders($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $modal, $rootScope, Data, $location) {

  $scope.msg = "start";
  var vm = this;

  vm.brand_size_data = [];//To get Sizes for some brands
  vm.size_filter = {};//Size Filter Search
  vm.show_no_data = false;//Show No Data
  vm.size_filter_show = false;
  vm.size_filter_data = {};
  vm.size_toggle = true;
  vm.brand_size_collect = {};
  vm.user_type = Session.roles.permissions.user_type;

  vm.order_type_value = "offline";
  vm.service = Service;
  vm.company_name = Session.user_profile.company_name;
  vm.model_data = {};
  vm.required_quantity = {};
  vm.margin_types = ['Margin Percentage', 'Margin Value'];
  Data.styles_data = {};
  vm.location = $location.$$path;

  var empty_data = {data: [{sku_id: "", quantity: "", invoice_amount: "", price: "", tax: "", total_amount: "", unit_price: ""}], 
                            customer_id: "", payment_received: "", order_taken_by: "", other_charges: [], shipment_time_slot: "", remarks: ""};

  angular.copy(empty_data, vm.model_data);


  vm.selected = {}

  vm.categories = [];
  vm.category = "";
  vm.brand = "";
  vm.filterData = {};
  
  vm.goBack = function(){

    $state.go('user.App.Brands');
  }

  function change_filter_data() {
    var data = {brand: vm.brand, category: vm.category, is_catalog: true, sale_through: vm.order_type_value};
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){

      if(data.message) {

        vm.categories = data.data.categories;
        vm.filterData = data.data;
        console.log(data.data);
        vm.filterData.brand_size_data = [];
        if(["reseller", "dist_customer"].indexOf(Session.roles.permissions.user_type) == -1) {
          if(data.data.size.type1) {
            vm.filterData.brand_size_data = $.unique(data.data.size.type1)
          }
          vm.filterData.brand_size_data = ['XS','S','M', 'L', 'XL', '2XL', '3XL', '4XL'];
        }
        vm.filterData.brands.push("All");
        vm.filterData.categories.push("All");
        vm.filterData.colors.push("All");
        vm.filterData.primary_details = data.data.primary_details;
        vm.filterData.selectedBrands = {};
        vm.filterData.subCats = {};

	vm.brands = data.data.brands;
	if (vm.brands.length === 0){
	  vm.details = false;
	}
        vm.brands_images = {'6 Degree': 'six-degrees.jpg', 'AWG (All Weather Gear)': 'awg.jpg', 'BIO WASH': 'bio-wash.jpg', 
	'Scala': 'scala.jpg','Scott International': 'scott.jpg', 'Scott Young': 'scott-young.jpg', 'Spark': 'spark.jpg', 
	'Star - 11': 'star-11.jpg','Super Sigma': 'super-sigma-dryfit.jpg', 'Sulphur Cotton': 'sulphur-cottnt.jpg', 'Sulphur Dryfit': 'sulphur-dryfit.jpg', 'Spring': 'spring.jpg', '100% Cotton': '100cotton.jpg', 'Sprint': 'sprint.jpg', 'Supreme': 'supreme.jpg', 'Sport': 'sport.jpg', 'Swiss Military': 'sm-brand.jpg',
        'A-one gold': 'A-ONE.jpg',
        'Agni': 'AGNI.jpg',
        'Apex': 'APEX.jpg',
        'Beekay': 'BEEKAY.jpg',
        'Bhuwalka': 'BHUWALKA.jpg',
        'I Steel Gold': 'I STEEL GOLD.jpg',
        'Indus': 'INDUS.jpg',
        'Primegold': 'PRIME GOLD.jpg',
        'FE500':'FE500.jpg',
        'FE500D':'FE500D.jpg',
        'FE550':'FE550.jpg',
        'FE600':'FE600.jpg',
        'MARSH':'MARSH.jpg',
        }

        vm.brands_logos = {'6 Degree': 'six-degrees-1.png', 'AWG (All Weather Gear)': 'awg-1.png', 'BIO WASH': 'bio-wash-1.png',
        'Scala': 'scala-1.png','Scott International': 'scott-1.png', 'Scott Young': 'scott-young-1.png', 'Spark': 'spark-1.png',
        'Star - 11': 'star-11-1.png','Super Sigma': 'super-sigma-dryfit-1.png', 'Sulphur Cotton': 'sulphur-cottnt-1.png',                             'Sulphur Dryfit': 'sulphur-dryfit-1.png', 'Spring': 'spring-1.png', '100% Cotton': '100-cotton-1.png', 'Sprint': 'sprint-1.png',
        'Supreme': 'supreme-1.png', 'Sport': 'sport-1.png', 'Swiss Military': 'sm-brand.jpg',
        'A-one gold': 'A-ONE.jpg',
        'Agni': 'AGNI.jpg',
        'Apex': 'APEX.jpg',
        'Beekay': 'BEEKAY.jpg',
        'Bhuwalka': 'BHUWALKA.jpg',
        'I Steel Gold': 'I STEEL GOLD.jpg',
        'Indus': 'INDUS.jpg',
        'Primegold': 'PRIME GOLD.jpg',
        'FE500':'FE500.jpg',
        'FE500D':'FE500D.jpg',
        'FE550':'FE550.jpg',
        'FE600':'FE600.jpg',
        'MARSH':'MARSH.jpg',
        }
        if (vm.location == '/App/Products') {
          // vm.change_brand('');
          vm.change_category('');
        } else if(vm.location == '/App/Categories'){
          // vm.change_category('');
          vm.change_brand('');
        }
      }
    });
  }
  change_filter_data();

  vm.style = "";
  vm.catlog_data = {data: [], index: ""}

  vm.loading = true;

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

    angular.copy([], vm.catlog_data.data);
    vm.getingData(data).then(function(data) {
      if(data == 'done') {
        var data = {data: vm.gotData};
    //vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(data) {

	//  if(data.message) {

        angular.copy([], vm.catlog_data.data);
        vm.catlog_data.index = data.data.next_index;
	      angular.forEach(data.data.data, function(item){
          vm.catlog_data.data.push(item);
        });
        vm.scroll_data = true;
  	//  }
	  vm.loading = false;
    //})
      }
    })

  }

  vm.picked_items_obj = {};
  vm.picked_items_data = {};
  vm.picked_item_info = function(item){

    if (vm.picked_items_obj[item.sku_desc]) {

      vm.picked_items_data[item.sku_desc] = item;
    } else {

      delete vm.picked_items_data[item.sku_desc];
    }
  }

  vm.gotData = {};
  vm.data_loading = false;
  vm.getingData = function(data) {
    vm.catDisplay = false;
    if(vm.data_loading) {

      vm.cancel();
      vm.data_loading = false;
    }

    vm.data_loading = true;
    var canceller = $q.defer();
    vm.service.apiCall("get_sku_catalogs/", "POST", data).then(function(response) {
      if(response.message) {
        vm.gotData = response.data;
        console.log("done");
        canceller.resolve("done");
        vm.data_loading = false;
        vm.showFilter = false;
      }
    });

    vm.cancel = function() {
      console.log("cancel")
      canceller.resolve("cancelled");
    };
    return canceller.promise;
  }

  vm.redirect_from_orders = function(status, scroll){
    if (!vm.catlog_data.data) {
      vm.get_category(status, scroll);
    }
  }

  vm.get_category = function(status, scroll) {

    if(vm.showFilter) {
      return false;
    }

    vm.loading = true;
    vm.scroll_data = false;
    vm.show_no_data = false;
    var size_stock = "";
    var cat_name = vm.category;
    // vm.required_quantity = {};

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

    var data = {brand: vm.brand, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true,
                sale_through: vm.order_type_value, size_filter: size_stock, color: vm.color, from_price: vm.fromPrice,
                to_price: vm.toPrice, quantity: vm.quantity, is_margin_percentage: vm.marginData.is_margin_percentage,
                margin: vm.marginData.margin, hot_release: vm.hot_release, margin_data: JSON.stringify(Data.marginSKUData.data)};

    if(status) {
      angular.copy([], vm.catlog_data.data);
    }
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
    });
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

  vm.hot_release = false;
  vm.get_hot_release = function() {

    vm.clearFilterData();
    vm.hot_release = true;
    vm.showFilter = false;
    vm.filterData.hotRelease = vm.hot_release;
    vm.get_category(true);
    $state.go('user.App.Products');
  }

  vm.catDisplay = false;
  vm.all_cate = [];
  vm.categories_details = {};
  vm.change_brand = function(data) {

    vm.brand = data;
    vm.catlog_data.index = "";
    vm.required_quantity = {};
    angular.copy([], vm.catlog_data.data);
    vm.category = '';
    vm.style='';
    vm.size_filter_show=false;
    vm.filterData.selectedBrands = {};
    vm.filterData.selectedBrands[vm.brand] = true;

    angular.forEach(vm.filterData.selectedCats, function(value, key) {
      vm.filterData.selectedCats[key] = false;
    });

    angular.forEach(vm.filterData.selectedColors, function(value, key) {
      vm.filterData.selectedColors[key] = false;
    });
    angular.forEach(vm.filterData.size_filter, function(value, key) {
      vm.filterData.size_filter[key] = "";
    })

    vm.category = "";
    vm.color = "";
    vm.filterData.fromPrice = "";
    vm.filterData.toPrice = "";
    vm.filterData.quantity = "";
    vm.fromPrice = vm.filterData.fromPrice;
    vm.toPrice = vm.filterData.toPrice;
    vm.quantity = vm.filterData.quantity;
    vm.size_filter_data = vm.filterData.size_filter;

    vm.showFilter = false;
    //vm.get_category(true);

    vm.pdfDownloading = true;
    vm.catDisplay = true;
    var data = {brand: vm.brand, sale_through: vm.order_type_value};
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){
      if(data.message) {
        vm.all_cate = data.data.categories;
        vm.categories_details = data.data.categories_details;
        $state.go('user.App.Categories');
      }
      vm.pdfDownloading = false;
    });
  }

  vm.change_category = function(category) {

    vm.category = category;
    if (vm.filterData.selectedCats){
      vm.filterData.selectedCats[category] = true;
    } else {
      vm.filterData.selectedCats = {};
      vm.filterData.selectedCats[category] = true;
    }

    if(!vm.filterData.subCats[category]) {
      vm.filterData.subCats[category] = {};
    }
    vm.filterData.subCats[category][category] = true;
    vm.showFilter = false;
    vm.from_cats = true;
    vm.required_quantity = {};
    vm.get_category(true);
    $state.go('user.App.Products');
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
    vm.showFilter = false;
    change_filter_data();
    /*var data = {is_catalog: true, sale_through: vm.order_type_value};
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){

      if(data.message) {

        vm.brands = data.data.brands;
      }
    })*/
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
    var user_name = Session.parent.userName;
    var sm_user_type = Session.roles.permissions.user_type;
    Data.my_orders = [];
    Data.enquiry_orders = [];

    Auth.logout().then(function(){
      if (user_name == 'sagar_fab') {
        $state.go("user.sagarfab");
      } else if(sm_user_type == 'reseller'){
        $state.go("user.smlogin");
      } else {
        $state.go("user.signin");
      }
    })
   }

  vm.date_changed = function(){
    //$('.datepicker').hide();
    $(this);
  }

  $( window ).resize(function() {
    vm.add_scroll();
  })

  $rootScope.$on('$stateChangeSuccess', function () {
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
      var cart = $(".cart_button:visible").outerHeight();
      
      // if(vm.location != '/App/Categories'){
        $(".app_body").css('height',height-header-menu-cart);
      // }
      
      $(".app_body").css('overflow-y', 'auto');
    }
    }, 500)
  }
  vm.add_scroll();

  //$scope.$watch(function(){
    //vm.add_scroll();
  //});

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


  vm.getQuantityList = function(data){

    var quantityList = "";
    angular.forEach(data, function(size){
      quantityList = quantityList + size.sku_size + "-" + size.physical_stock + ",";
    });
    return quantityList;
  }

  //filters
  vm.showFilters = false;

  vm.applyFilters = function(){
    console.log(vm.filterData, $state);
    var brand= [];
    var category= [];
    var color = [];
    angular.forEach(vm.filterData.selectedBrands, function(value, key) {
      if (value) {
        brand.push(key);
      }
    });

    var temp_primary_data = [];
    angular.forEach(vm.filterData.selectedCats, function(value, key) {
      if (value) {
        category.push(key);
        temp_primary_data[key] = [];
        angular.forEach(vm.filterData.subCats[key], function(stat, sub_cat){
          if(stat && sub_cat != 'All') {
            temp_primary_data.push(sub_cat);
          }
        })
      }
    });

    angular.forEach(vm.filterData.selectedColors, function(value, key) {
      if (value) {
        color.push(key);
      }
    });

    if(brand.indexOf("All") != -1) {
      brand.splice(brand.indexOf("All"),1)
    }
    if(category.indexOf("All") != -1) {
      category.splice(category.indexOf("All"),1)
    }
    if(color.indexOf("All") != -1) {
      color.splice(color.indexOf("All"),1)
    }

    vm.catlog_data.index = "";
    vm.brand = brand.join(",");
    vm.category = temp_primary_data.join(","); //category.join(",");
    vm.color = color.join(",");
    vm.size_filter_data = vm.filterData.size_filter
    //vm.primary_data = JSON.stringify(temp_primary_data);
    vm.fromPrice = vm.filterData.fromPrice;
    vm.toPrice = vm.filterData.toPrice;
    vm.quantity = vm.filterData.quantity;
    vm.showFilter = false;
    vm.from_cats = false;
    vm.hot_release = vm.filterData.hotRelease;
    vm.get_category(true);
    if( $state.$current.name == "user.App.Brands" || $state.$current.name == "user.App.Categories") {
      $state.go('user.App.Products');
    }
    $window.scrollTo(0, angular.element(".app_body").offsetTop);
  }

  vm.filterData.brandShow = false;
  vm.filterData.catShow = false;
  vm.filterData.colorShow = false;
  vm.showFilters = function() {

    vm.filterData.brandShow = false;
    vm.filterData.catShow = false;
    vm.filterData.colorShow = false;
    vm.showFilter = true;
  }

  vm.checkPrimaryFilter = function(primary_cat) {

    if(!vm.filterData.selectedCats[primary_cat]) {

      angular.forEach(vm.filterData.subCats[primary_cat], function(value ,sub_cat){
        vm.filterData.subCats[primary_cat][sub_cat] = false;
      })
    }
  }

  vm.clearFilterData = function() {

    angular.forEach(vm.filterData.size_filter, function(value, key) {
        vm.filterData.size_filter[key] = "";
      })

      angular.forEach(vm.filterData.selectedBrands, function(value, key) {
        vm.filterData.selectedBrands[key] = false;
      });

      angular.forEach(vm.filterData.selectedCats, function(value, key) {
        vm.filterData.selectedCats[key] = false;
        vm.checkPrimaryFilter(key);
      });

      angular.forEach(vm.filterData.selectedColors, function(value, key) {
        vm.filterData.selectedColors[key] = false;
      });
      vm.brand = "";
      vm.category = "";
      vm.color = "";
      vm.filterData.fromPrice = "";
      vm.filterData.toPrice = "";
      vm.filterData.quantity = "";
      vm.filterData.hotRelease = false;
      vm.hot_release = vm.filterData.hotRelease;
      vm.fromPrice = vm.filterData.fromPrice;
      vm.toPrice = vm.filterData.toPrice;
      vm.quantity = vm.filterData.quantity;

    vm.catlog_data.index = "";
    vm.size_filter_data = vm.filterData.size_filter
  }

  vm.clearFilters = function(data) {

    vm.clearFilterData();
    vm.required_quantity = {};
    if( $state.$current.name == "user.App.Brands") {
      return false;
    } else {
      vm.showFilter = false;
    }
    vm.get_category(true);
    $window.scrollTo(0, angular.element(".app_body").offsetTop);
  }

  vm.checkFilterBrands = function(value, data) {

    var all = data['All'];
    if (value != 'All') {
      data['All'] = false;
    } else {
      angular.forEach(data, function(value, key) {
        if(key != 'All') {
          data[key] = false;
        }
      })
    }
  }

  vm.checkFilters = function(value, data, primary) {

    var all = data['All'];
    if (value != 'All') {
      data['All'] = false;
      var all_true = true;
      for(var i=0;i<vm.filterData.primary_details.data[primary].length; i++) {
        if(!data[vm.filterData.primary_details.data[primary][i]]) {
          all_true = false;
          break;
        }
      }
      data['All'] = (all_true)? true: false;
    } else if(value == 'All' && data['All']) {
      angular.forEach(vm.filterData.primary_details.data[primary], function(key) {
        data[key] = true;
      })
    } else {
      angular.forEach(data, function(value, key) {
        if(key != 'All') {
          data[key] = false;
        }
      })
    }
  }

  /*
  vm.pdfDownloading = false;
  vm.downloadPdf = function() {
    var size_stock = JSON.stringify(vm.size_filter_data);
    var data = {brand: vm.brand, category: vm.category, sku_class: vm.style, index: "", is_catalog: true,
                sale_through: vm.order_type_value, size_filter:size_stock, share: true, file: true,
                color: vm.color, from_price: vm.fromPrice, to_price: vm.toPrice,
                is_margin_percentage: vm.marginData.is_margin_percentage, margin: vm.marginData.margin,
                hot_release: vm.hot_release}
    vm.pdfDownloading = true;
    vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(response) {
      if(response.message) {
        window.open(Session.host + response.data, '_blank');
        //http://ultd-dev.mieone.com:9022/#/App/Products;
      }
      vm.pdfDownloading = false;
    });
  }*/

  vm.cat_level_margin = {};

  //margin value
  vm.marginData = {margin_type: '', margin: 0, margin_percentage: 0, margin_value: 0, is_margin_percentage: true, sale_through: vm.order_type_value};
  vm.addMargin = function() {
 
    var mod_data = vm.marginData;
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/app/create_orders/add_margin.html',
      controller: 'addMarginCtrl',
      controllerAs: '$ctrl',
      size: 'md',
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

      Data.marginSKUData.is_margin_percentage = vm.marginData.is_margin_percentage;
      Data.marginSKUData.margin = vm.marginData.margin;
      Data.marginSKUData.data = [];

      vm.catlog_data.index = '';
      vm.get_category(true, true);

    })
  }

  vm.margin_add_to_categoris = function(data, default_margin){
    vm.checked_margin = default_margin;
    if (data.length) {
      angular.forEach(data, function(item){

        if (Data.marginSKUData.category[vm.category] && vm.checked_margin) {

          if (Data.marginSKUData.category[vm.category] != vm.checked_margin) {

            item.variants[0].your_price = vm.changed_margin;
            Data.marginSKUData.category[vm.category] = vm.checked_margin;
          }
          else {
            item.variants[0].your_price = Data.marginSKUData.category[vm.category];
          }
        } else {
          if (Data.marginSKUData.margin) {
            item.variants[0].your_price = Data.marginSKUData.margin;
          } else {
            vm.catlog_data.data.push(item);
          }
        }
      });

      // angular.forEach(data, function(item){
      //   vm.catlog_data.data.push(item);
      // });
    } else {
      Data.marginSKUData.category = {};
      default_margin = Data.marginSKUData.margin;
    }
  }

  vm.addSKUinData = function(data_list) {
    var flag = 1;
    if (Data.marginSKUData.data.length) {
      for (let index = 0; index < Data.marginSKUData.data.length; index++) {
        if(Data.marginSKUData.data[index].wms_code == data_list.wms_code) {
          Data.marginSKUData.data[index].price = data_list.price;
          Data.marginSKUData.data[index].margin = data_list.margin;
          flag=0;
          break;
        }
      }
      if(flag) {
        Data.marginSKUData.data.push(data_list);  
      }
    } else {
      Data.marginSKUData.data.push(data_list);
    }
  }

  vm.marginData = {margin_type: '', margin: 0, margin_percentage: 0, margin_value: 0, is_margin_percentage: true, sale_through: vm.order_type_value};

  vm.modifyMarginEachSKU = function(item, $index) {
    vm.catlog_data.data[$index].loading = true
    var dict_values = {};
    dict_values['margin_data'] = { 'wms_code':item.wms_code, 'price':item.your_price, 'margin' : item.margin }
    dict_values['margin_values'] = { 'brand':item.sku_brand, 'category':item.sku_category, 'sku_class':item.sku_class,
      'index':$index, 'is_catalog':true, 'sale_through':item.sale_through, 'size_filter':item.sku_size, 
      'color':'', 'from_price': '', 'to_price': '', 'is_margin_percentage': vm.marginData.is_margin_percentage, 
      'margin':item.margin };
    var data_list = [];
    data_list.push(dict_values['margin_data']);
    vm.addSKUinData(dict_values['margin_data']);
    var data = dict_values['margin_values'];
    data['margin_data'] = JSON.stringify(data_list);
    var index_value = data['index'];
    data['index'] = '';
    Service.apiCall("get_sku_catalogs/", "POST", data).then(function(data) {
      if(data.message) {
        vm.catlog_data.data[index_value] = data.data.data[0];
      } else {
        Service.showNoty("Something Went Wrong", "danger")
      }
    });
  };

  vm.downloadPDF = function() {

    var size_stock = JSON.stringify(vm.size_filter_data);
    var data = {data: {brand: vm.brand, category: vm.category, sku_class: vm.style, index: "", is_catalog: true,
                sale_through: vm.order_type_value, size_filter:size_stock, share: true, file: true,
                color: vm.color, from_price: vm.fromPrice, to_price: vm.toPrice, quantity: vm.quantity,
                is_margin_percentage: vm.marginData.is_margin_percentage, margin: vm.marginData.margin,
                margin_data: JSON.stringify(Data.marginSKUData.data)}, required_quantity: vm.required_quantity,
                checked_items: vm.picked_items_data, checked_item_value: vm.picked_items_obj}

    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/app/create_orders/download_pdf.html',
      controller: 'downloadPDFCtrl',
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
      console.log(selectedItem);
    });
  }

  vm.category_image_map = {'Denim Shirt': 'software-catagaies-final_08.png',
                           'Formal Shirt': 'software-catagaies-final_34.png',
                           'Gents Polo': 'software-catagaies-final_11.png',
                           'Hoodie': 'software-catagaies-final_44.png',
                           'Hoodie - 300 GSM': 'software-catagaies-final_21.png',
                           'Hoodie - 300 GSM ZIP': 'software-catagaies-final_24.png',
                           'Hoodie - 400 GSM': 'software-catagaies-final_22.png',
                           'Hoodie - 400 GSM ZIP': 'software-catagaies-final_25.png',
                           'Ladies Polo': 'software-catagaies-final_06.png',
                           'Polo': 'software-catagaies-final_52.png', 
                           'Round Neck': 'software-catagaies-final_46.png',
                           'Scott Basic - RN': 'software-catagaies-final_57.png',
                           'V Neck T Shirt': 'software-catagaies-final_37.png',
                           //'T Shirt': 'software-catagaies-final_06.png',
                           'Sleeve Less Jacket': 'software-catagaies-final_13.png',
                           'Sleeveless': 'software-catagaies-final_13.png',
                           'Round Neck T Shirt': 'software-catagaies-final_35.png',
                           'Slub Round Neck': 'software-catagaies-final_32.png',
                           'Best Sellers|Electronics ': 'electronics-bs.jpg',
                           'Best Sellers|Travel Accessories ': 'travel-acc-bs.jpg',
                           'Best Sellers|Travel Gear ': 'travel-gear-bs.jpg',
                           'Electronics ': 'electronics.jpg',
                           'Leather Collections ': 'leather.jpg',
                           'Sunglasses ': 'sunglasses.jpg',
                           'Travel Accessories ': 'travel-acc.jpg',
                           'Travel Gear ': 'travel-gear.jpg',
                           'Writing Instruments ': 'writing.jpg',
                           'TMT Steel': 'TMT_category.jpg',

                           //swiss military

                           'ACCESSORIES': 'ACCESSORIES.jpg',
                           'APPARELS': 'APPARELS.jpg',
                           'ELECTRONICS': 'ELECTRONICS.jpg',
                           'GARMENTS': 'GARMENTS.jpg',
                           'LEATHER ITEMS': 'LEATHER ITEMS.jpg',
                           'PENS': 'PENS.jpg',
                           'PU ITEMS': 'PU ITEMS.jpg',
                           'SUNGLASSES': 'SUNGLASSES.jpg',
                           'TRAVEL GEAR-LAPTOP BACKPACKS': 'TG-BACKPACKS.jpg',
                           'TRAVEL GEAR-CANVAS BAGS': 'TG-CANVAS BAGS.jpg',
                           'TRAVEL GEAR-FOLDABLE BAGS': 'TG-FOLDABLE BAGS.jpg',
                           'TRAVEL GEAR-GYM BAGS': 'TG-GYM BAGS.jpg',
                           'TRAVEL GEAR-HARD LUGGAGE': 'TG-HARD LUGGAGE.jpg',
                           'TRAVEL GEAR-LAPTOP TROLLEY BAGS': 'TG-LAPTOP STROLLYS.jpg',
                           'TRAVEL GEAR-SLING BAGS': 'TG-SLING BAGS.jpg',
                           'TRAVEL GEAR-SOFT LUGGAGE': 'TG-SOFT LUGGAGE.jpg',
                           'TRAVEL GEAR-TOILETRY BAGS': 'TG-TOILETARY BAGS.jpg',
                           'TRAVEL GEAR-TRAVEL WALLETS': 'TG-TRAVEL WALLETS.jpg',
                           'TOYS': 'TOYS.jpg',
                           'TRAVEL GEAR': 'TRAVEL GEAR.jpg',

                           'ACCESSORIES': 'ACCESSORIES.jpg',
                           'APPARELS': 'APPARELS.jpg',
                           'ELECTRONICS-CHARGERS': 'ELECTRONICS-CHARGERS.jpg',
                           'ELECTRONICS-MISC.': 'ELECTRONICS-MISC.jpg',
                           'ELECTRONICS-SPEAKERS': 'ELECTRONICS-SPEAKERS.jpg',
                           'LEATHER-BELTS': 'LEATHER-BELTS.jpg',
                           'LEATHER-WALLETS': 'LEATHER-WALLETS.jpg',
                           'PENS-BALL PENS': 'PENS-BALL PENS.jpg',
                           'PENS-FOUNTAIN PENS': 'PENS-FOUNTAIN PENS.jpg',
                           'PENS-ROLLER BALL PENS': 'PENS-ROLLER BALL PENS.jpg',
                           'PU-BELTS': 'PU-BELTS.jpg',
                           'PU-WALLETS': 'PU-WALLETS.jpg',
                           'SUNGLASS-AVIATOR': 'SUNGLASS-AVIATOR.jpg',
                           'SUNGLASS-LADIES AVIATORS': 'SUNGLASS-LADIES AVIATORS.jpg',
                           'SUNGLASS-LADIES WAYFARER': 'SUNGLASS-LADIES WAYFARER.jpg',
                           'SUNGLASS-WAYFARER': 'SUNGLASS-WAYFARER.jpg',

                           //SAILESH
                           'FULL SLEEVE SHIRT': 'FULL SLEEVE SHIRT.png',
                           'HONEY COMBED DRY FIT': 'HONEY COMBED DRY FIT.png',
                           'HOODIES WITHOUT ZIP': 'HOODIES WITHOUT ZIP.png',
                           'HOODIES WITH ZIP': 'HOODIES WITH ZIP.png',
                           'POLO': 'POLO.png',
                           'ROUND NECK': 'ROUND NECK.png',
                           };

  vm.get_category_image = function(category) {

    if(vm.category_image_map[category]) {
      return '/images/categories/'+vm.category_image_map[category];
    } else {
      return '/images/categories/default.png'
    }
  }

  vm.changePWDData = {};
  vm.changePWD = function() {
 
    var mod_data = vm.changePWDData;
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/app/create_orders/change_pwd.html',
      controller: 'changePWDCtrl',
      controllerAs: '$ctrl',
      size: 'md',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return mod_data;
        }
      }
    });

    modalInstance.result.then(function (selectedItem) {
      vm.changedData = selectedItem;
    })
  }
}

angular
  .module('urbanApp')
  .controller('appCreateOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$modal', '$rootScope', 'Data', '$location', appCreateOrders]);

angular.module('urbanApp').controller('addMarginCtrl', function ($modalInstance, $modal, items, Service, Data, Session) {
  var $ctrl = this;
  $ctrl.marginData = {};
  angular.copy(items, $ctrl.marginData);
  $ctrl.sku_data = [];
  angular.copy(Data.marginSKUData.data, $ctrl.sku_data);
  $ctrl.user_type = Session.roles.permissions.user_type;

  $ctrl.margin_types = ['Margin Percentage', 'Margin Value'];

  if ($ctrl.marginData.is_margin_percentage) {
    $ctrl.marginData.margin_type = $ctrl.margin_types[0];
  } else {
    $ctrl.marginData.margin_type = $ctrl.margin_types[1];
  }

  $ctrl.ok = function (form) {

    if(form.$invalid) {
      return false;
    }
    var margin = ($ctrl.marginData.is_margin_percentage)? $ctrl.marginData.margin_percentage: $ctrl.marginData.margin_value;
    angular.copy({data: $ctrl.sku_data}, Data.marginSKUData);
    $modalInstance.close($ctrl.marginData);
  };

  $ctrl.cancel = function () {
    $modalInstance.dismiss('cancel');
  };


  $ctrl.category = '';
  $ctrl.categories = [];
  $ctrl.categories_loading = true;
  $ctrl.get_categories = function() {

    var data = {brand: '', sale_through: $ctrl.marginData.sale_through};
    Service.apiCall("get_sku_categories/", "GET",data).then(function(data){
      if(data.message) {
        $ctrl.categories = data.data.categories;
        $ctrl.category = "";
      }
      $ctrl.categories_loading = false;
    });
  }
  $ctrl.get_categories();

  $ctrl.style = '';
  $ctrl.styles = [];
  $ctrl.get_styles = function(category){

    if(!category) {
      $ctrl.style = "";
      $ctrl.styles = [];
      $ctrl.sku = "";
      $ctrl.skus = [];
      return false;
    }

    var data = {category: category, sale_through: $ctrl.marginData.sale_through, is_catalog:true, customer_id: Session.userId}
    $ctrl.styles_loading = true;
    $ctrl.styles = [];
    Service.apiCall("get_sku_catalogs/", "POST", data).then(function(data) {
      if(data.message) {
        $ctrl.styles = data.data.data;
        $ctrl.style = "";
        $ctrl.sku = "";
        $ctrl.skus = [];
      }
      $ctrl.styles_loading = false;
    });
  }

  $ctrl.sku = '';
  $ctrl.skus = [];
  $ctrl.get_skus = function(style){

    if(!$ctrl.style) {
      $ctrl.sku = "";
      $ctrl.skus = [];
      return false;
    }

    var data = {sku_class: style, is_catalog:true, customer_id: Session.userId}
    $ctrl.skus_loading = true;
    $ctrl.skus = [];
    Service.apiCall("get_sku_variants/", "POST", data).then(function(data) {
      if(data.message) {
        $ctrl.skus = data.data.data;
        $ctrl.sku = "";
      }
      $ctrl.skus_loading = false;
    });
  }

  $ctrl.addSKUData = function() {

    if(!$ctrl.sku) {
      return false;
    }
    var sku = {};
    for(let index = 0; index < $ctrl.skus.length; index++){
      if($ctrl.skus[index].wms_code == $ctrl.sku) {
        sku = $ctrl.skus[index];
        break;
      }
    }

    for(let index = 0; index < $ctrl.sku_data.length; index++) {
      if($ctrl.sku_data[index].wms_code == sku.wms_code){
        Service.showNoty("SKU Already Added")
        return false;
      }
    }
    $ctrl.sku_data.push({wms_code: sku.wms_code, price: sku.price});
  }

  $ctrl.removeSkuData = function(index) {

    $ctrl.sku_data.splice(index,1);
  }
});

angular.module('urbanApp').controller('downloadPDFCtrl', function ($modalInstance, $modal, items, Service, Session) {
  var vm = this;
  vm.user_type = Session.roles.permissions.user_type;
  vm.pdfData = items
  vm.pdfData.display_stock = true;
  vm.pdfData.remarks = '';
  if (Session.roles.permissions.customer_pdf_remarks) {
    vm.pdfData.remarks = Session.roles.permissions.customer_pdf_remarks;
  }

  vm.pdfDownloading = false;
  vm.downloadPDF = function(form) {

    var data = {};
    // var data = vm.pdfData.data;
    angular.copy(vm.pdfData.data, data);
    if (!vm.pdfData.display_total_amount) {
        delete data.required_quantity;
    }
    vm.pdfDownloading = true;
    var terms_list = [];
    angular.forEach(vm.terms, function(value, key) {
      if(value.is_checked){
        terms_list.push(value.terms);
      }
    });

    data['checked_items'] = JSON.stringify(vm.pdfData.checked_items);
    data['required_quantity'] = JSON.stringify(vm.pdfData.required_quantity);

    data['terms_list'] = terms_list.join('<>');
    data['user_type'] = Session.roles.permissions.user_type;
    Service.apiCall("get_sku_catalogs/", "POST", data).then(function(response) {
      if(response.message) {
        window.open(Session.host + response.data, '_blank');
      }
      vm.pdfDownloading = false;
    });

    data = $("form").serialize();
    Service.apiCall("switches/?"+data);
    Session.roles.permissions.customer_pdf_remarks = vm.pdfData.remarks;
  }

  vm.clear_quantities = function(){

    vm.pdfData.required_quantity = {};
  }

  vm.remove_item = function(item){

    delete vm.pdfData.checked_item_value[item];
    delete vm.pdfData.checked_items[item];
  }

  vm.cancel = function () {
    $modalInstance.dismiss('cancel');
  };

  vm.terms = []

  vm.get_terms = function(data) {
    var data = {tc_type: 'sales'}
    Service.apiCall("get_terms_and_conditions/", "GET",data).then(function(data){
      if(data.message) {
        vm.terms = data.data.tc_list;
      }
      vm.pdfDownloading = false;
    });
  }

  vm.get_terms();


});

angular.module('urbanApp').controller('changePWDCtrl', function ($modalInstance, $modal, items, Service, Session) {
  var vm = this;
  vm.user_type = Session.roles.permissions.user_type;
  vm.model_data = items;
  vm.service = Service;

  vm.check_validation = function(){
    if (vm.confirm_pwd) {
      if (vm.new_pwd !== vm.confirm_pwd) {
        vm.service.showNoty("New password does not match with confirm password plase check it once");
      }
    }
  }

  vm.ok = function (form) {

    if(form.$invalid) {
      return false;
    }
    if (vm.new_pwd !== vm.confirm_pwd) {
      return false;
    }
    if (vm.exe_pwd == vm.new_pwd && vm.new_pwd == vm.confirm_pwd) {
      vm.service.showNoty('Sorry, Your old password and new password is same. Please try again.');
      return false;
    }

    var data = {old_password: vm.exe_pwd,  new_password: vm.new_pwd,  retype_password: vm.confirm_pwd}
    Service.apiCall("change_user_password/", "POST", data).then(function(response) {
      if (response.message) {
        if(response.data.msg) {
          vm.service.showNoty(response.data.data);

          $modalInstance.close(response.data.msg);
        } else {
          vm.service.showNoty(response.data.data);
        }
      } else {
        vm.service.showNoty('Something went wrong');
      }
    });
  };

  vm.cancel = function () {
    $modalInstance.dismiss('cancel');
  };
});


})();
