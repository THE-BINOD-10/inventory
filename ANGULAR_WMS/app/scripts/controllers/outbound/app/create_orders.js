'use strict';

function appCreateOrders($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth) {

  $scope.msg = "start";
  var vm = this;

  vm.catlog_display = false;
  vm.brand_display = true;
  vm.style_display = false;
  vm.cart_disply = false;
  vm.your_order_display = false;
  vm.order_detail_display = false;

  vm.order_type_value = "offline";
  vm.service = Service;
  vm.company_name = Session.user_profile.company_name;
  vm.model_data = {}
  var empty_data = {data: [{sku_id: "", quantity: "", invoice_amount: "", price: "", tax: "", total_amount: "", unit_price: ""}], 
                            customer_id: "", payment_received: "", order_taken_by: "", other_charges: []};

  angular.copy(empty_data, vm.model_data);
  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      vm.model_data.data.push({sku_id: "", quantity: "", invoice_amount: "", price: "", tax: vm.tax, total_amount: "", unit_price: ""});
    } else {
      vm.model_data.data.splice(index,1);
    }
  }

  vm.selected = {}
  vm.get_customer_data = function(item, model, label, event) {
    vm.model_data["customer_id"] = item.customer_id;
    vm.model_data["customer_name"] = item.name;
    vm.model_data["telephone"] = parseInt(item.phone_number);
    vm.model_data["email_id"] = item.email;
    vm.model_data["address"] = item.address;
    vm.add_customer = false;
    angular.copy(item, vm.selected)
  }

  vm.check_id = function(id) {
    if(Number(id) > 0) {
      if (!(vm.model_data["customer_name"])) {
        vm.add_customer = true;
      }
    }
    if(!(Number(id)) && id) {
      vm.model_data["customer_name"] = id;
      vm.model_data["customer_id"] = "";
      vm.add_customer = true;
    }
  }

  function make_empty() {
    vm.model_data["customer_name"] = "";
    vm.model_data["telephone"] = "";
    vm.model_data["email_id"] = "";
    vm.model_data["address"] = "";
  }

  vm.bt_disable = false;
  vm.insert_order_data = function(form) {
    if (vm.model_data.shipment_date) {
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('insert_order_data/', 'GET', elem).then(function(data){
        if(data.message) {
          if("Success" == data.data) {
            angular.copy(empty_data, vm.model_data);
            vm.final_data = {total_quantity:0,total_amount:0}
          }
            swal({
              title: "Success!",
              text: "Your Order Has Been Placed Successfully",
              type: "success",
              showCancelButton: false,
              confirmButtonText: "OK",
              closeOnConfirm: true
              },
              function(isConfirm){
                vm.brand_display = true;
                vm.cart_display = false;
              }
            )
           //swal("Success!", "Your Order Has Been Placed Successfully", "success")
          //vm.service.showNoty("Order Created Successfully", "success", "bottomRight");
        }
        vm.bt_disable = false;
      })
    } else {
      vm.service.showNoty("Please Select Shipment Date", "success", "bottomRight");
    }
  }

  //vm.catlog = true;
  //vm.details = true;
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
	/*vm.brands_images = {'6 Degree': '6degree.png', 'AWG (All Weather Gear)': 'awg.jpg', 'BIO WASH': 'biowash.jpg', 'Scala': 'scala.png',
        'Scott International': 'scott.jpg', 'Scott Young': 'scottyoung.png', 'Spark': 'spark.jpg', 'Star - 11': 'star11.png',
	 'Super Sigma': 'supersigma.jpg', 'Sulphur Cotton': 'dflt.jpg', 'Sulphur Dryfit': 'dflt.jpg'}*/
        vm.brands_images = {'6 Degree': 'six-degrees.jpg', 'AWG (All Weather Gear)': 'awg.jpg', 'BIO WASH': 'bio-wash.jpg', 
	'Scala': 'scala.jpg','Scott International': 'scott.jpg', 'Scott Young': 'scott-young.jpg', 'Spark': 'spark.jpg', 
	'Star - 11': 'star-11.jpg','Super Sigma': 'super-sigma-dryfit.jpg', 'Sulphur Cotton': 'sulphur-cottnt.jpg', 'Sulphur Dryfit': 'sulphur-dryfit.jpg', 'Spring': 'spring.jpg', '100% Cotton': '100cotton.jpg', 'Sprint': 'sprint.jpg', 'Supreme': 'supreme.jpg', 'Sport': 'sport.jpg'}

        vm.brands_logos = {'6 Degree': 'six-degrees-1.png', 'AWG (All Weather Gear)': 'awg-1.png', 'BIO WASH': 'bio-wash-1.png',
        'Scala': 'scala-1.png','Scott International': 'scott-1.png', 'Scott Young': 'scott-young-1.png', 'Spark': 'spark-1.png',
        'Star - 11': 'star-11-1.png','Super Sigma': 'super-sigma-dryfit-1.png', 'Sulphur Cotton': 'sulphur-cottnt-1.png',                             'Sulphur Dryfit': 'sulphur-dryfit-1.png', 'Spring': 'spring-1.png', '100% Cotton': '100-cotton-1.png', 'Sprint': 'sprint-1.png',
        'Supreme': 'supreme-1.png', 'Sport': 'sport-1.png'}
        vm.get_category(true);
      }
    });
  }
  change_filter_data();

  vm.style = "";
  vm.catlog_data = {data: [], index: ""}

  vm.tag_details = function(cat_name, brand) {

    vm.category = cat_name;
    if(cat_name == "All") {
      cat_name = "";
    }
    vm.catlog_data.index = "";
    var data = {brand: vm.brand, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true,
                sale_through: vm.order_type_value} 
    vm.catlog_data.index = ""
    vm.scroll_data = false;
    vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(data) {
    
	if(data.message) {
        
        angular.copy([], vm.catlog_data.data);
        vm.catlog_data.index = data.data.next_index;
	angular.forEach(data.data.data, function(item){
          vm.catlog_data.data.push(item);
        })
        vm.scroll_data = true;
	}
    })

  }

  vm.get_category = function(status, scroll) {
    vm.scroll_data = false;
    var cat_name = vm.category;
    if(vm.category == "All") {
      cat_name = "";
    }
    var data = {brand: vm.brand, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true,
                sale_through: vm.order_type_value}
    vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(data) {

      if(data.message) {

        if(status) {

          vm.catlog_data.index = "";
          angular.copy([], vm.catlog_data.data);
        }
        vm.catlog_data.index = data.data.next_index;
        angular.forEach(data.data.data, function(item){
          vm.catlog_data.data.push(item);
        })
      }
      vm.scroll_data = true;
      vm.add_scroll();
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
    var all = $(".cat-tags");
    var data = {brand: vm.brand, sale_through: vm.order_type_value}
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){
      if(data.message) {

        vm.all_cate = data.data.categories; 
        if(vm.all_cate.length> 0) {
          vm.all_cate.push("All")
          vm.category = vm.all_cate[0];
          vm.get_category(true);
        }
      }
    })
  }

  vm.show = function() {
  
    vm.base();
    vm.model_data.template_value = "";
    vm.model_data.template_type = ""
    $state.go('app.outbound.CreateOrders.CreateCustomSku');
  }

 vm.base = function() {

    vm.title = "Create Custom SKU";
    //vm.update = false;
    //angular.copy(empty_data, vm.model_data);
    vm.service.apiCall('get_sku_field_names/','GET',{'field_type':'create_orders'}).then(function(data){

      if(data.message) {
	vm.template_types = data.data.template_types;
        //vm.template_types = data.data.template_types;
        //vm.model_data.template_type = vm.template_types[0].field_name;
        //vm.template_values = vm.template_types[0].field_data;
        vm.model_data.template_type = vm.template_types[0].field_value;
        vm.pop_data.sizes_list = data.data.sizes_list;
      }
    })
  }

  vm.change_template_values = function(){
    angular.forEach(vm.template_types, function(data) {
      var property_name = vm.model_data.template_type.split(':')[0];
      var template_name = vm.model_data.template_type.split(':')[1];
      if((property_name == data.field_value) && (template_name == data.template_name)){
        vm.template_values = data.field_data;
	vm.template_name = data.template_name;
	vm.property_type = data.field_name;
        //vm.model_data.property_name = vm.template_values[0];
      }
    })
  }

  vm.image = "";
  vm.change_category_values = function(){

    vm.service.apiCall('get_product_properties/',"GET",{'property_type':vm.property_type,'property_name':vm.model_data.template_value,'template_name':vm.template_name}).then(function(data){
        if (data.data.data.length > 0) {

          vm.attributes = data.data.data[0].attributes;
          if (data.data.data[0].images.length) {

            vm.image = data.data.data[0].images[0];
          } else {

            vm.image = "";
          }
        } else {
          vm.attributes = [];
          vm.image = "";
        }
  })
}

  vm.pop_btn = true;
  vm.check_quantity = function(data){

    vm.pop_btn = true;
    angular.forEach(data, function(record){
      if(Number(record.quantity)> 0) {
        vm.pop_btn = false;
      }
    });
  }

  vm.add_custom_sku = function (data) {
    if (data.$valid && vm.pop_data.unit_price) {

      var elem = $('#create_form').serializeArray()
    var formData = new FormData()
    var files = $("form").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });

    $.each(elem, function(i, val) {
        formData.append(val.name, val.value);
    });

    $.ajax({url: Session.url+'create_custom_sku/',
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              var response = JSON.parse(response);
              if(response.message == "SKU Created Successfully") {
              
                colFilters.showNoty("Custom SKU Created And Also Added In Order");
                vm.add_to_order(response.data, vm.pop_data);
                vm.attributes = [];
                vm.image = "";
                vm.model_data.template_value = "";
                vm.model_data.template_type = "";
                vm.close(); 
              } else {
                vm.service.pop_msg(response.message);
              }
            }});

	/*vm.service.apiCall('create_custom_sku/','GET',$('#create_form').serializeArray()).then(function(data) {
          if(data.message) {

            if(data.data.message == "SKU Created Successfully") {
              
              colFilters.showNoty("Custom SKU Created And Also Added In Order");
              vm.add_to_order(data.data.data, vm.pop_data);
              vm.attributes = [];
              vm.image = "";
              vm.model_data.template_value = "";
              vm.model_data.template_type = "";
              vm.close(); 
            } else {
              vm.service.pop_msg(data.data.message);
            }
          }	
	})*/
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

  vm.add_to_order = function(data, sizes) {

    if (vm.model_data.data.length==1) {
      if (!(vm.model_data.data[0].sku_id)) {
        vm.model_data.data = [];
      }
    }
    angular.forEach(data, function(record){

      var temp = {sku_id: record.sku_code, quantity: Number(record.quantity), invoice_amount: "", price: Number(sizes.unit_price), tax: vm.tax, total_amount: ''}
      temp.invoice_amount = temp.quantity*temp.price;
      temp.total_amount = ((temp.invoice_amount/100)*5.5)+temp.invoice_amount;
      vm.model_data.data.push(temp);
    });

    vm.cal_total();
    /*if (vm.model_data.data[0].sku_id) {
      vm.model_data.data.push({sku_id: data, quantity: "", invoice_amount: "", price: "", tax: vm.tax}); 
    } else {
      vm.model_data.data[0].sku_id = data;
      vm.model_data.data[0].quantity = "1";
      vm.model_data.data[0].invoice_amount = "";
      vm.model_data.data[0].price = "";
    }*/
  }

 vm.close = function() {

    //angular.copy(empty_data, vm.model_data);
    vm.attributes = [];
    vm.image = "";
    angular.copy(empty_pop_data, vm.pop_data);
    vm.pop_btn = true;
    $state.go('app.outbound.CreateOrders');
  }

  vm.brand_details = function(brand_data) {

    vm.brand = brand_data;
    vm.filter_change();
    /*vm.service.apiCall("get_sku_catalogs/", "GET", {brand: brand_data}).then(function(data) {

      if(data.message) {

        if(brand_data) {   

	  vm.catlog_data.details = [];
	  vm.catlog_data.brand = brand_data;
        }
        
	angular.forEach(data.data.data, function(item){

	  vm.catlog_data.details.push(item);
        });
      }	
    });*/
  }


  vm.style_open = false;
  vm.style_data = [];
  vm.open_style = function(data, item) {

    vm.style_data = [];
    var quantity = item.style_quantity;
    vm.service.apiCall("get_sku_variants/", "GET", {sku_class: data, is_catalog: true}).then(function(data) {

      if(data.message) {
        vm.style_open = true;
        vm.check_stock=true;
        vm.style_data = data.data.data;
        vm.stock_quantity = quantity;
      }
      vm.add_scroll();
    });
    vm.style_total_quantity = 0;
  }

  vm.style_total_quantity = 0;
  vm.change_style_quantity = function(data){
    vm.style_total_quantity = 0;
    angular.forEach(data, function(record){

      if(record.quantity) {
        vm.style_total_quantity += Number(record.quantity);
      }
    })
  }

  vm.check_item = function(sku) {

    var d = $q.defer();
    if(vm.model_data.data.length == 0) {
        d.resolve('true');
    }
    angular.forEach(vm.model_data.data, function(data, index){
      if(data.sku_id == sku) {
        d.resolve(String(index));
      } else if ((vm.model_data.data.length-1) == index) {
        d.resolve('true');
      }
    })
    return d.promise;
  }

  vm.add_to_cart = function() {
    if(vm.style_total_quantity > 0) {
      angular.forEach(vm.style_data, function(data){

        if (data['quantity']) {
          vm.check_item(data.wms_code).then(function(stat){
            console.log(stat)
            if(stat == "true") {
              if(vm.model_data.data.length > 0 && vm.model_data.data[0]["sku_id"] == "") {
                vm.model_data.data[0].sku_id = data.wms_code;
                vm.model_data.data[0].quantity = Number(data.quantity);
                vm.model_data.data[0]['price'] = Number(data.price);
                vm.model_data.data[0].invoice_amount = data.price*Number(data.quantity);
                vm.model_data.data[0]['tax'] = vm.tax;
                vm.model_data.data[0]['image_url'] = data.image_url;
                vm.model_data.data[0]['total_amount'] = ((vm.model_data.data[0].invoice_amount/100)*vm.tax)+vm.model_data.data[0].invoice_amount;
              } else {
                var temp = {sku_id: data.wms_code, quantity: Number(data.quantity), invoice_amount: data.price*Number(data.quantity), price: data.price, tax: vm.tax, image_url: data.image_url}
                temp['total_amount'] = ((temp.invoice_amount/100)*vm.tax)+temp.invoice_amount;
                vm.model_data.data.push(temp)
              }
            } else {
               var temp = Number(vm.model_data.data[Number(stat)].quantity);
               vm.model_data.data[Number(stat)].quantity = temp+Number(data.quantity);
               vm.model_data.data[Number(stat)].invoice_amount = Number(data.price)*vm.model_data.data[Number(stat)].quantity;
               var invoice = vm.model_data.data[Number(stat)].invoice_amount;
               vm.model_data.data[Number(stat)].total_amount = ((invoice/100)*vm.tax)+invoice;
            }
            vm.cal_total();
          });
        }
      });
      vm.service.showNoty("Succesfully Added to Cart", "success", "bottomRight");
    } else {
      vm.service.showNoty("Please Enter Quantity", "success", "bottomRight");
    }
  }

  vm.check_stock = true;
  vm.enable_stock = function(){
    if(vm.check_stock) {
      vm.check_stock = false;
    } else {
      vm.check_stock = true;
    }
  }

  vm.get_invoice = function(record, item) {

    var sku = item.wms_code;
    record.sku_id = sku;
    vm.service.apiCall("get_sku_variants/", "GET", {sku_code: sku, customer_id: vm.model_data.customer_id, is_catalog: true}).then(function(data) {

      if(data.message) {
        if(data.data.data.length == 1) {
          record["price"] = data.data.data[0].price;
          if(!(record.quantity)) {
            record.quantity = 1
          }
          record.invoice_amount = Number(record.price)*Number(record.quantity)
          vm.cal_percentage(record);
        }
      }
    });
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

  vm.add_customer = false;
  vm.create_customer = function() {

    if(vm.model_data.customer_id == "") {

      colFilters.showNoty("Please Fill Customer ID");
    } else if (!(vm.model_data.customer_name)) {

      colFilters.showNoty("Please Fill Customer Name");
    } else if(!(vm.model_data.email_id)) {

      colFilters.showNoty("Please Fill Email");
    } else {

      var data = {customer_id: vm.model_data.customer_id, name: vm.model_data.customer_name,
                  email_id: vm.model_data.email_id, phone_number: vm.model_data.telephone,
                  address: vm.model_data.address}
      vm.service.apiCall("insert_customer/","POST", data).then(function(data){
        if(data.message)  {
          if(data.data == 'New Customer Added') {
            vm.add_customer = false;
          }
          colFilters.showNoty(data.data);
        }
      })
    }
  }

  var empty_pop_data = {sizes_list: [], list:[], unit_price:''}
  vm.pop_data = {};
  angular.copy(empty_pop_data, vm.pop_data);

  vm.change_sizes_list = function(item) {

    vm.pop_data.list = []
    angular.forEach(vm.pop_data.sizes_list, function(data){

      if(data.size_name == item) {

        angular.forEach(data.size_values, function(record) {

          vm.pop_data.list.push({name: record, quantity: 0});
        })
      }
    })
  }

  vm.tax = 0;
  vm.model_data.data[0].tax = vm.tax;
  empty_data.data[0].tax = vm.tax;

  /*Create customer */
  vm.status_data = ["Inactive", "Active"];
  vm.title = "Create Customer";
  vm.customer_data = {};
  vm.open_customer_pop = function() {

    vm.service.apiCall("get_customer_master_id/").then(function(data){
      if(data.message) {

        vm.customer_data["customer_id"] = data.data.customer_id;
      }
    });
    $state.go("app.outbound.CreateOrders.customer");
  }
  vm.submit = function(data){
    if (data.$valid) {
      vm.service.apiCall('insert_customer/', 'POST', vm.customer_data).then(function(data){
        if(data.message) {
          if(data.data == 'New Customer Added') {
            vm.close();
            angular.copy(vm.customer_data, vm.model_data)
            vm.model_data["customer_name"] = vm.customer_data.name;
            vm.model_data["telephone"] = vm.customer_data.phone_number;
          } else {
            vm.service.pop_msg(data.data);
          }
        }
      });
    } else if (!(data.phone_number.$valid)) {
      vm.service.pop_msg('Invalid phone number');
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

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

  vm.create_order_data = {}
  vm.get_create_order_data = function(){
    vm.service.apiCall("create_orders_data/").then(function(data){

      if(data.message) {
        vm.create_order_data = data.data;
        vm.model_data.tax_type = 'VAT'
        vm.change_tax_type();
      }
    })
  }
  vm.get_create_order_data();

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
  vm.change_cart_quantity = function(data, stat) {

    if (stat) {
      data.quantity = Number(data.quantity) + 1 
      vm.change_amount(data);
    } else {
      if (Number(data.quantity)> 1) {
        data.quantity = Number(data.quantity) - 1 
        vm.change_amount(data);
      }   
    }   
  }

  vm.change_amount = function(data) {

    var find_data=data;
    data.quantity = Number(data.quantity);
    data.invoice_amount = Number(data.price)*data.quantity;
   
  }

  vm.remove_item = function(index) {

    vm.model_data.data.splice(index,1);
  }

  vm.date_changed = function(){
    $('.datepicker').hide();
  }
  /*
  $($window).on('hashchange', function(event) {
    if(confirm("Do you really want to logout from mieone?") == true) {
      Auth.logout();
      $state.go("user.sagarfab");
    } else {
      event.preventDefault();
    }
  });*/

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
      var cart = $(".cart").height();
      $(".app_body").css('height',height-header-menu-cart);
      $(".app_body").css('overflow-y', 'auto');
    }
    }, 500)
  }
  vm.add_scroll();

  $scope.$watch(function(){
    vm.add_scroll();
  });

  //you orders
  vm.you_orders = false;
  vm.orders_loading = false
  vm.order_data = {}
  vm.get_orders = function(){

    vm.orders_loading = true;
    vm.order_data = {}
    vm.service.apiCall("get_customer_orders/").then(function(data){
      if(data.message) {

        console.log(data.data);
        angular.copy(data.data, vm.order_data);
      }
      vm.orders_loading = false;
    })
  }

  vm.order_details = {}
  vm.open_order_detail = function(order){

    vm.order_details = {}
    vm.order_detail_display = true;
    vm.you_order_display = false;
    vm.service.apiCall("get_customer_order_detail/?order_id="+order.order_id).then(function(data){
      if(data.message) {

        console.log(data.data);
        angular.copy(data.data, vm.order_details);
        vm.order_details['order'] = order;
      }
    })
  }
}

angular
  .module('urbanApp')
  .controller('appCreateOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', appCreateOrders]);
