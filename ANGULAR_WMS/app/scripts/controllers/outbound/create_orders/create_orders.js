'use strict';

function CreateOrders($scope, $filter, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Data, SweetAlert) {

  $scope.msg = "start";
  var vm = this;
  vm.order_type_value = "offline";
  vm.service = Service;
  vm.g_data = Data.create_orders
  vm.company_name = Session.user_profile.company_name;
  vm.order_exceed_stock = Boolean(Session.roles.permissions.order_exceed_stock);
  vm.permissions = Session.roles.permissions;
  vm.model_data = {}
  vm.dispatch_data = []
  vm.auto_shipment = false;
  vm.date = new Date();
  vm.payment_status = ['To Pay', 'VPP', 'Paid'];
  var empty_data = {data: [{sku_id: "", quantity: "", invoice_amount: "", price: "", tax: "", total_amount: "", unit_price: "",
                            location: "", serials: [], serial: "", capacity: 0, discount: ""
                          }],
                    customer_id: "", payment_received: "", order_taken_by: "", other_charges: [],  shipment_time_slot: "",payment_modes:[],
                    tax_type: "", vehicle_num: "",blind_order: false, mode_of_transport: "", payment_status: ""};

  angular.copy(empty_data, vm.model_data);


  vm.from_custom_order = false;
  if(Data.create_orders.custom_order_data.length > 0) {
    vm.model_data.data = [];
    angular.forEach(Data.create_orders.custom_order_data, function(sku_data){
      vm.model_data.data.push({sku_id: sku_data.sku_id, quantity: sku_data.quantity, description: sku_data.sku_desc,
                               invoice_amount: "", price: "", tax: "", total_amount: "", unit_price: "",location: "",
                               serials: [], serial: "", capacity: 0, extra: sku_data.extra, discount: ""})
    })
    Data.create_orders.custom_order_data = [];
    vm.from_custom_order = true;
    vm.custom_order = true;
  }

  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last && (!vm.model_data.data[index].sku_id)) {
      return false;
    }
    if (last) {
      vm.model_data.data.push({sku_id: "", quantity: "", invoice_amount: "", price: "", tax: vm.tax, total_amount: "", unit_price: "", discount: ""});
    } else {
      vm.model_data.data.splice(index,1);
      vm.cal_total();
    }
  }

  vm.selected = {}
  vm.get_customer_data = function(item, model, label, event) {
    vm.model_data["customer_id"] = item.customer_id;
    vm.model_data["customer_name"] = item.name;
    vm.model_data["telephone"] = parseInt(item.phone_number);
    vm.model_data["email_id"] = item.email;
    vm.model_data["address"] = item.address;
    vm.model_data["ship_to"] = item.ship_to;
    if(item.tax_type) {

      vm.model_data["tax_type"] = item.tax_type;
    } else {

      vm.model_data["tax_type"] = '';
    }
    vm.add_customer = false;
    angular.copy(item, vm.selected)
    vm.change_sku_prices();
    vm.change_tax_type();
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
  vm.insert_order_data = function(event, form, is_sample='') {
    if (event.keyCode != 13) {
      if (form.$valid && vm.model_data.shipment_date && vm.model_data.shipment_time_slot) {
        if (vm.model_data.blind_order) {
          for (var i = 0; i < vm.model_data.data.length; i++) {

            if (vm.model_data.data[i].sku_id && (!vm.model_data.data[i].location)) {

              colFilters.showNoty("Please locations");
              return false;
              break;
            }
          }
        }
        vm.bt_disable = true;
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        if(!vm.model_data.payment_amounts)
        {
          vm.model_data.payment_amounts = {}
        }
        elem.push({'name':'payment_modes','value':JSON.stringify(vm.model_data.payment_amounts)})
        if (is_sample == 'sample') {
          elem.push({'name':'is_sample', 'value':true});
        }
        vm.service.apiCall('insert_order_data/', 'POST', elem).then(function(data){
          if(data.message) {
            if(data.data.indexOf("Success") != -1) {
              angular.copy(empty_data, vm.model_data);
              vm.final_data = {total_quantity:0,total_amount:0};
              vm.from_custom_order = false;
            }
            colFilters.showNoty(data.data);
          }
          vm.bt_disable = false;
        })
      } else {
        colFilters.showNoty("Fill Required Fields");
      }
    }
  }

  vm.catlog = false;
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
	'Star - 11': 'star-11.jpg','Super Sigma': 'super-sigma-dryfit.jpg', 'Sulphur Cotton': 'sulphur-cottnt.jpg', 'Sulphur Dryfit': 'sulphur-dryfit.jpg', 'Spring': 'spring.jpg', '100% Cotton': '100cotton.jpg', 'Sprint': 'sprint.jpg', 'Supreme': 'supreme.jpg'}

        vm.brands_logos = {'6 Degree': 'six-degrees-1.png', 'AWG (All Weather Gear)': 'awg-1.png', 'BIO WASH': 'bio-wash-1.png',
        'Scala': 'scala-1.png','Scott International': 'scott-1.png', 'Scott Young': 'scott-young-1.png', 'Spark': 'spark-1.png',
        'Star - 11': 'star-11-1.png','Super Sigma': 'super-sigma-dryfit-1.png', 'Sulphur Cotton': 'sulphur-cottnt-1.png',                             'Sulphur Dryfit': 'sulphur-dryfit-1.png', 'Spring': 'spring-1.png', '100% Cotton': '100-cotton-1.png', 'Sprint': 'sprint-1.png',
        'Supreme': 'supreme-1.png'}
        vm.get_category(true);
      }
    });
  }
  change_filter_data();

  vm.style = "";
  vm.catlog_data = {data: [], index: ""}

  vm.tag_details_loading = false;
  vm.data_loading = "not done"

  vm.tag_details = function(cat_name, brand, scroll, status) {

    if(scroll && vm.data_loading == "done") {

      return false;
    } else {

      vm.data_loading = "not done";
    }

    if(vm.tag_details_loading) {

      vm.cancel();
      //return false;
    } else {

      vm.tag_details_loading = true
    }

    vm.category = cat_name;
    if(cat_name == "All") {
      cat_name = "";
    }
    if(!scroll) {
      vm.catlog_data.index = "";
    }
    var data = {brand: vm.brand, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true,
                sale_through: vm.order_type_value, customer_data_id: vm.model_data.customer_id};
    vm.catlog_data.index = ""
    vm.scroll_data = false;
    //vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(data) {

  	//  if(data.message) {

    vm.getingData(data).then(function(data) {
      console.log(data);
      vm.scroll_data = true;
      if(data == 'done') {
          var data = {data: vm.gotData};
          if(!scroll) {
            angular.copy([], vm.catlog_data.data);
          } else {
            if(vm.gotData.data.length == 0){
              vm.data_loading = "done";
            }
          }
          if(status) {
            angular.copy([], vm.catlog_data.data);
          }
          vm.catlog_data.index = data.data.next_index;
	      angular.forEach(data.data.data, function(item){
            vm.catlog_data.data.push(item);
          })
    	//  }
        vm.tag_details_loading = false;
      }
    })

  }

  vm.gotData = {};
  vm.getingData = function(data) {

    vm.loading = true;
    var canceller = $q.defer();
    vm.service.apiCall("get_sku_catalogs/", "POST", data).then(function(response) {
      if(response.message) {
        vm.gotData = response.data;
        canceller.resolve("done");
      }
      vm.loading = false;
    });
    vm.cancel = function() {
      canceller.resolve("cancelled");
    };
    return canceller.promise;
  }

  vm.get_category = function(status, scroll) {
    vm.scroll_data = false;
    var cat_name = vm.category;
    //if(vm.category == "All") {
    //  cat_name = "";
    //}
    var data = {brand: vm.brand, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true,
                sale_through: vm.order_type_value, customer_data_id: vm.model_data.customer_id}

    vm.tag_details(vm.category, vm.brand, scroll, status);
    //vm.service.apiCall("get_sku_catalogs/", "GET", data).then(function(data) {

    //  if(data.message) {

    //    if(status) {

    //      vm.catlog_data.index = "";
    //      angular.copy([], vm.catlog_data.data);
    //    }
    //    vm.catlog_data.index = data.data.next_index;
    //    angular.forEach(data.data.data, function(item){
    //      vm.catlog_data.data.push(item);
    //    })
    //  }
    //  vm.scroll_data = true;
    //})

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
    angular.copy(vm.empty_custom, vm.custom_data);
    $state.go('app.outbound.CreateOrders.CreateCustomSku');
  }

 vm.base = function() {
    vm.title = "Create Custom SKU";
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

  vm.vendors = {}
    vm.service.apiCall("get_vendors_list/").then(function(data) {

       if(data.message)  {

          vm.vendors = data.data.data;
       }
    })

  vm.pop_btn = true;
  vm.check_quantity = function(){

    vm.pop_btn = true;
    angular.forEach(vm.custom_data.sku_data, function(record){
      if(Number(record.total)> 0) {
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
              if(response.message == "Success") {

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
    angular.forEach(data, function(record, index){

      var temp = {sku_id: record.sku_code, description: record.description, quantity: Number(record.quantity), invoice_amount: "", price: Number(sizes.unit_price), tax: vm.tax, total_amount: '', extra: record, remarks: record.remarks, discount: ""};
      temp.invoice_amount = temp.quantity*temp.price;
      temp.total_amount = ((temp.invoice_amount/100)*temp.tax)+temp.invoice_amount;
      vm.model_data.data.push(temp);
      if(data.length-1 == index) {

        vm.change_tax_type();
      }
    });

    vm.cal_total();
  }

 vm.close = function() {

    //angular.copy(empty_data, vm.model_data);
    vm.customer_data = {}
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
  vm.style_total_counts = {}
  vm.style_headers = {};
  vm.style_detail_hd = [];
  if (Session.roles.permissions["style_headers"]) {
    vm.en_style_headers = Session.roles.permissions["style_headers"].split(",");
  } else {
    vm.en_style_headers = [];
  }
  if(vm.en_style_headers.length == 0) {

    vm.en_style_headers = ["wms_code", "sku_desc"];
  }
  vm.stock_quantity = 0;
  vm.open_style = function(data) {

    vm.stock_quantity = data.style_quantity;
    vm.service.apiCall("get_sku_variants/", "POST", {sku_class: data.sku_class, is_catalog: true, customer_data_id: vm.model_data.customer_id}).then(function(data) {

      if(data.message) {
        vm.style_open = true;
        vm.check_stock=true;
        vm.style_data = data.data.data;
        vm.style_total_counts = data.data.total_qty;
        vm.style_headers = data.data.style_headers;
        vm.sku_spl_attrs = data.data.sku_spl_attrs;
        vm.style_detail_hd = Object.keys(vm.style_headers);
        //var quant_len = data.data.data.length-1;
        //vm.stock_quantity = vm.style_data[quant_len].style_quantity;
      }
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
      angular.forEach(vm.style_data, function(data, index){

        if (data['quantity']) {
          vm.check_item(data.wms_code).then(function(stat){
            console.log(stat)
            if(vm.model_data.blind_order && vm.permissions.use_imei) {
              data.quantity = 0;
            }
            if(stat == "true") {
              if(vm.model_data.data[0]["sku_id"] == "") {
                vm.model_data.data[0].sku_id = data.wms_code;
                vm.model_data.data[0]['description'] = data.sku_desc;
                vm.model_data.data[0].quantity = Number(data.quantity);
                vm.model_data.data[0]['price'] = Number(data.price);
                vm.model_data.data[0].invoice_amount = data.price*Number(data.quantity);
                vm.model_data.data[0]['tax'] = vm.tax;
                vm.model_data.data[0]['total_amount'] = ((vm.model_data.data[0].invoice_amount/100)*vm.tax)+vm.model_data.data[0].invoice_amount;
              } else {
                var temp = {sku_id: data.wms_code, description: data.sku_desc, quantity: Number(data.quantity), invoice_amount: data.price*Number(data.quantity), price: data.price, tax: vm.tax, discount: ""}
                temp['total_amount'] = ((temp.invoice_amount/100)*vm.tax)+temp.invoice_amount;
                vm.model_data.data.push(temp)
              }
            } else {
              if(!(vm.model_data.blind_order && vm.permissions.use_imei)) {
                var temp = Number(vm.model_data.data[Number(stat)].quantity);
                vm.model_data.data[Number(stat)].quantity = temp+Number(data.quantity);
                vm.model_data.data[Number(stat)].invoice_amount = Number(data.price)*vm.model_data.data[Number(stat)].quantity;
                var invoice = vm.model_data.data[Number(stat)].invoice_amount;
                vm.model_data.data[Number(stat)].total_amount = ((invoice/100)*vm.tax)+invoice;
              }
            }
            vm.cal_total();
          });
        }
        if(vm.style_data.length-1 == index){

          $timeout(function() {
            vm.change_tax_type();
          }, 1000);
        }
      });
      vm.service.showNoty("Succesfully Added to Cart");
    } else {
      vm.service.showNoty("Please Enter Quantity");
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
    record["description"] = item.sku_desc;
    vm.service.apiCall("get_sku_variants/", "POST", {sku_code: sku, customer_id: vm.model_data.customer_id, is_catalog: true}).then(function(data) {

      if(data.message) {
        if(data.data.data.length == 1) {
          record["price"] = data.data.data[0].price;
          record["description"] = data.data.data[0].sku_desc;
          if(!(record.quantity)) {
            record.quantity = 1
          }
          record.invoice_amount = Number(record.price)*Number(record.quantity)
          vm.cal_percentage(record);
        }
      }
    });
  }

  vm.final_data = {total_quantity:0,total_amount:0,temp_total_amount:0}
  vm.cal_total = function() {

    vm.final_data.total_quantity = 0;
    vm.final_data.total_amount = 0;
    vm.final_data.temp_total_amount = 0;
    angular.forEach(vm.model_data.data, function(record){
      vm.final_data.total_amount += Number(record.total_amount);
      vm.final_data.temp_total_amount += Number(record.total_amount);
      vm.final_data.total_quantity += Number(record.quantity);
    })
    if(vm.model_data.other_charges) {
      angular.forEach(vm.model_data.other_charges, function(record){
        if(record.amount){
          vm.cal_total_tax(record)
          vm.final_data.total_amount += Number(record.amount)+Number(record.tax_value);
          vm.final_data.temp_total_amount += Number(record.total_amount);

        }
      })
    }
    if (vm.model_data.order_discount) {
      vm.addDiscountToInv(vm.model_data.order_discount)
    }
  }
  vm.cal_percentage = function(data, no_total) {

    vm.discountPercentageChange(data, false);
    vm.get_tax_value(data);
    var per = Number(data.tax);
    data.total_amount = ((Number(data.invoice_amount - Number(data.discount))/100)*per)+(Number(data.invoice_amount)-Number(data.discount));

    if(!no_total) {
      vm.cal_total();
    }
  }
  vm.cal_total_tax = function(charge){
    charge.tax_value = (Number(charge.amount) * charge.tax_percent)/100
  }

  vm.change_unit_price = function(data) {
    data.invoice_amount = Number(data.price)*Number(data.quantity);
    vm.cal_percentage(data);
  }

  vm.discountChange = function(data) {

    vm.cal_percentage(data, false);
  }

  vm.discountPercentageChange = function(data, status) {

    if(vm.fields.indexOf('Discount Percentage') != -1) {
      return false;
    }
    if(!data.discount_percentage) {
      data.discount_percentage = "";
    }
    var temp_perc = Number(data.discount_percentage);
    data.discount = (Number(data.invoice_amount)*temp_perc)/100;
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

    angular.copy(empty_data, vm.model_data);
    vm.service.apiCall("get_customer_master_id/").then(function(data){
      if(data.message) {

        vm.customer_data["customer_id"] = data.data.customer_id;
      }
    });
    $state.go("app.outbound.CreateOrders.customer");
  }


  vm.title = "Dispatch Serial Numbers";
  vm.dispatch_data = []
  vm.dispatch_serial_numbers_pop = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go("app.outbound.CreateOrders.DispatchSerialNumbers");
  }

  // vm.elem = []
  // vm.scan_imei = function(event, field) {
  //     if ( event.keyCode == 13 && field) {
  //       field = field.toUpperCase();
  //       Service.apiCall('get_imei_data/', 'GET', {imei:field}, true).then(function(data){
  //         if(data.data.message == "Success") {
  //           vm.dispatch_data.push(data.data['dispatch_summary_imei_details'])
  //         } else {
  //           Service.showNoty(data.data.message);
  //         }
  //       })
  //       vm.imei="";
  //     }
  //   }

  vm.SerialcheckAndAdd = function(scan) {

    var status = false;
    for(var i = 0; i < vm.scan_codes.length; i++) {

      if(vm.scan_codes.indexOf(scan) > -1){
        status = true;
        break;
      }
    }
    return status;
  }

  vm.elem = []
  vm.scan_codes = []
  vm.scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field) {
        field = field.toUpperCase();
        var elem = {serial: field, cost_check:vm.model_data.blind_order};
        vm.service.apiCall('check_imei/', 'GET', elem).then(function(data){
        if(data.message) {
          if(data.data.status == "Success") {
            if(vm.SerialcheckAndAdd(field)) {
              vm.service.showNoty("Already Scanned")
            }
            else {
              vm.dispatch_data.push(data.data['dispatch_summary_imei_details'])
              vm.scan_codes.push(field)
            }
          } else {
            vm.service.showNoty(data.data.status);
          }
        }
      });
        vm.imei="";
      }
    }

    vm.submit_dispatch_data = function(event, form) {
      if (form.$valid){
        var elem = [];
        var send = vm.dispatch_data;
        elem.push({'name':'dispatch_Serial_data','value':JSON.stringify(vm.dispatch_data)})
        vm.service.apiCall('dispatch_serial_numbers/', 'POST', elem).then(function(data){
         if(data.message) {
           if(data.data.serial_data){
             vm.serial_data = data.data.serial_data;
             vm.model_data.blind_order = true;
             vm.model_data.data = []
             angular.forEach(data.data.serial_data, function(serial_data){
               vm.qty = serial_data.serial_number;
               vm.inv_amt = serial_data.selling_price;
               vm.model_data.data.push({sku_id: serial_data.sku_code, quantity: vm.qty.length, description: serial_data.sku_desc,
                                        invoice_amount: vm.inv_amt, price: "", tax: "", total_amount:vm.inv_amt, unit_price: "",location: serial_data.location,
                                        serials: vm.scan_codes, serial: "", capacity: 0, extra: '', discount: ""})
             })
           }
         }
       });
      }
      vm.model_data.blind_order = true;
      $state.go('app.outbound.CreateOrders');
    }


  vm.submit = function(data){
    if (data.$valid) {
      vm.service.apiCall('insert_customer/', 'POST', vm.customer_data, true).then(function(data){
        if(data.message) {
          if(data.data == 'New Customer Added') {
            vm.close();
            //angular.copy(vm.customer_data, vm.model_data)
            vm.model_data["customer_name"] = vm.customer_data.name;
            vm.model_data["telephone"] = vm.customer_data.phone_number;
            vm.model_data["customer_id"] = vm.customer_data.customer_id;
            vm.model_data["email_id"] = vm.customer_data.email_id;
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
        vm.model_data.order_taken_by = Session.user_profile.first_name;
        if(!Service.create_order_data.tax_type) {
          vm.model_data.tax_type = '';
        }
        vm.change_tax_type();
      }
    })
  }
  vm.get_create_order_data();

  vm.order_extra_fields = []
  vm.extra_fields = false;
  vm.get_order_extra_fields = function(){
    vm.service.apiCall("get_order_extra_fields/").then(function(data){
      if(data.message) {
        vm.order_extra_fields = data.data.data;
        if(vm.order_extra_fields[0] == '')
        {
          vm.extra_fields = false
        }
        else{
          vm.exta_model ={}
          vm.extra_fields = true
           for(var i =0 ; i< vm.order_extra_fields.length; i++)
           {
              vm.exta_model[vm.order_extra_fields[i]] = '';

           }
          }
        }
      })
    }

  vm.get_order_extra_fields();
  vm.get_extra_order_options  = function()
  {
    vm.service.apiCall("get_order_extra_options/").then(function(data){
      if(data.message) {
        vm.extra_order_options = data.data;
      }

    })

  }
  vm.get_extra_order_options();

  vm.change_tax_type = function() {

    var tax_name = vm.model_data.tax_type;
    if(!(vm.model_data.tax_type)) {
      tax_name = 'DEFAULT';
      angular.forEach(vm.model_data.data, function(record) {
        if(record.sku_id) {
          record.tax = 0;
          record.sgst = 0;
          record.cgst = 0;
          record.igst = 0;
          record.taxes = [];
          vm.cal_percentage(record, false);
        }
      })
    } else {

      angular.forEach(vm.model_data.data, function(record) {

        if(record.sku_id) {
          vm.get_customer_sku_prices(record.sku_id).then(function(data){
            if(data.length > 0) {
              console.log(data);
              record.taxes = data[0].taxes;
              vm.cal_percentage(record, false);
            }
          })
        }
      })
    }
    //vm.cal_total();
  }

  vm.field_perm = {};
  vm.min_width = "";
  if(Session.roles.permissions["order_headers"]) {
    vm.min_width = "";
  } else {
    vm.min_width = "mw75";
  }

  vm.fields = Session.roles.permissions["order_headers"];
  if(!(vm.fields)) {
    vm.fields = [];
  } else {
    vm.fields = vm.fields.split(",")
  }

  vm.get_tax_value = function(data) {

    var tax = 0;
    for(var i = 0; i < data.taxes.length; i++) {

      if(data.price <= data.taxes[i].max_amt && data.price >= data.taxes[i].min_amt) {

        if(vm.model_data.tax_type == "intra_state") {

          tax = data.taxes[i].sgst_tax + data.taxes[i].cgst_tax;
          data.sgst_tax = data.taxes[i].sgst_tax;
          data.cgst_tax = data.taxes[i].cgst_tax;
          data.igst_tax = 0;
        } else if (vm.model_data.tax_type == "inter_state") {

          data.sgst_tax = 0;
          data.cgst_tax = 0;
          data.igst_tax = data.taxes[i].igst_tax;
          tax = data.taxes[i].igst_tax;
        }
        break;
      }
    }

    data.tax = tax;
    return tax;
  }

  function check_exist(sku_data, index) {

    for(var i = 0; i < vm.model_data.data.length; i++) {

      if((vm.model_data.data[i].sku_id == sku_data.sku_id) && (index != i)) {

        sku_data.sku_id = "";
        vm.service.showNoty("It is already exist in index");
        return false;
      }
    }
    return true;
  }

  vm.update_availabe_stock = function(sku_data) {

     var send = {sku_code: sku_data.sku_id, location: ""}
     vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
      sku_data["capacity"] = 0
      if(data.message) {

        if(data.data.available_quantity) {

          sku_data["capacity"] = data.data.available_quantity;
        }
      }
    });
  }

  vm.get_sku_data = function(record, item, index) {

    record.sku_id = item.wms_code;
    if(!vm.model_data.blind_order && !(check_exist(record, index))){
      return false;
    }
    angular.copy(empty_data.data[0], record);
    record.sku_id = item.wms_code;
    record["description"] = item.sku_desc;

    vm.get_customer_sku_prices(item.wms_code).then(function(data){
      if(data.length > 0) {
        data = data[0]
        record["price"] = data.price;
        record["description"] = data.sku_desc;
        if (! vm.model_data.blind_order) {
          if(!(record.quantity)) {
            record.quantity = 1
          }
        }
        record["taxes"] = data.taxes;
        record["mrp"] = data.mrp;
        record.invoice_amount = Number(record.price)*Number(record.quantity);
        record["priceRanges"] = data.price_bands_map;
        vm.cal_percentage(record);
        vm.update_availabe_stock(record)
      }
    })
  }

  vm.get_customer_sku_prices = function(sku) {

    var d = $q.defer();
    var data = {sku_codes: sku, cust_id: vm.model_data.customer_id, tax_type: vm.model_data.tax_type}
    vm.service.apiCall("get_customer_sku_prices/", "POST", data).then(function(data) {

      if(data.message) {
        d.resolve(data.data);
      }
    });
    return d.promise;
  }

  vm.change_sku_prices = function() {

    if(vm.model_data.data.length > 0) {

      var sku_codes = [];
      angular.forEach(vm.model_data.data, function(record){

        if ((sku_codes.indexOf(record.sku_id) == -1) && record.sku_id) {
          sku_codes.push(record.sku_id)
        }
      })

      sku_codes = sku_codes.join()
      if(sku_codes) {

        vm.get_customer_sku_prices(sku_codes).then(function(data){
          if(data.length > 0) {
            angular.forEach(data, function(record){
              vm.change_sku_values(record);
            })
          }
        })
      }
    }
  }

  vm.change_sku_values = function(data) {

    if(vm.model_data.data.length > 0) {
      for(var i = 0; i < vm.model_data.data.length ; i++) {

        if (vm.model_data.data[i]["sku_id"] == data.wms_code) {

          vm.model_data.data[i]["price"] = data.price;
          vm.model_data.data[i]["unit_price"] = data.price;
          if(!(vm.model_data.data[i].quantity)) {
            vm.model_data.data[i].quantity = 1
          }
          vm.model_data.data[i].invoice_amount = Number(data.price)*Number(vm.model_data.data[i].quantity)

          vm.cal_percentage(vm.model_data.data[i]);
          break;
        }
      }
    }
  }

  vm.empty_custom = {sku_data: [], cats: []}

  vm.custom_data = {};
  angular.copy(vm.empty_custom, vm.custom_data);
  //custom SKU
  vm.removeSKU = function(index) {

    vm.custom_data.sku_data.splice(index, 1);
  }

  vm.getTemplateData = function(e, name) {

    console.log(e,name);
    angular.copy(vm.empty_custom, vm.custom_data);
    if(name) {

      vm.service.apiCall('get_product_properties/?data_id='+name).then(function(data){
        if(data.message) {
          angular.copy(data.data, vm.pop_data);
          vm.pop_data.brand = "ALL";
          vm.getCategoriesList(vm.pop_data.name, vm.pop_data.brand);
          vm.pop_data.size_name = vm.pop_data.size_names[0];
          vm.pop_data.sizes = vm.sizes[vm.pop_data.size_name];
        }
      })
    }
  }

  vm.sizes = {};
  //get all size names
  vm.getSizes = function() {

    vm.service.apiCall("get_size_names/").then(function(data){

      console.log(data.data);
      if(data.message) {

        vm.sizes = data.data;
      }
    })
  }
  vm.getSizes();

  vm.selectedCat = 0;
  vm.getCategoriesList = function(name, brand){

    vm.service.apiCall("get_categories_list/", "GET", {name: name, brand: brand}).then(function(data){
      if(data.message) {
        console.log(data.data);
        vm.custom_data.cats = [];
        if(data.data.length > 0) {

          data.data.push("All");
        }
        vm.custom_data.cats = data.data;
        vm.selectedCat = vm.custom_data.cats.length - 1;
        vm.getCustomStyles(vm.custom_data.cats[vm.selectedCat]);
      }
    })
  }

  vm.changeSizes = function(name) {

    if(name) {

      if(vm.sizes[name]) {

        vm.pop_data.sizes = vm.sizes[name];

        angular.forEach(vm.custom_data.sku_data, function(data){

          data.sizes = [];
          data.total = 0;
          angular.forEach(vm.pop_data.sizes, function(size) {

            data.sizes.push({name: size, value: 0});
          })
        })
      } else {

        vm.pop_data.sizes = [];
      }
    } else {

      vm.pop_data.sizes = [];
    }
  }

  vm.calTotal = function(sku, value) {

    if(value) {

      if(!(Number(value) > -1)) {

        return false;
      }
    }

    sku.total = 0;
    angular.forEach(sku.sizes, function(size) {

      sku.total += Number(size.value);
    })

    vm.check_quantity()
  }

  vm.custom_styles_loading = false;
  vm.styles_loading = false;
  vm.getCustomStyles = function(name, index) {

    if(!vm.styles_loading) {

      vm.styles_loading = true
    } else {

      return false;
    }
    vm.custom_styles_loading = true;
    vm.pop_data.style_data = [];
    if (index > -1) {
      vm.selectedCat = index;
    }
    vm.service.apiCall("get_custom_template_styles/", "GET", {name: vm.pop_data.name, brand: vm.pop_data.brand, category: name}).then(function(data){
      if(data.message) {
        console.log(data.data);
        vm.pop_data.style_data = data.data.data;
      }
      vm.custom_styles_loading = false;
      vm.styles_loading = false;
    })
  }

  vm.addSKU = function(item){

    var status = true;
    for(var i = 0; i < vm.custom_data.sku_data.length; i++){

      if(vm.custom_data.sku_data[i].name == item.sku_class) {

        status = false;
        break;
      }
    }

    if(status) {

      var temp = {name: item.sku_class, sizes: [], total:0, remarks:'', av_sizes:[]};

      angular.forEach(vm.pop_data.sizes, function(size) {

         temp.sizes.push({name: size, value: 0});
      })
      angular.forEach(item.variants, function(data){

        if(data.sku_size) {

          temp.av_sizes.push(data.sku_size);
        }
      })
      vm.custom_data.sku_data.push(temp);
    } else {

      vm.service.showNoty("Style Already Added");
    }
  }

  vm.change_blind_order = function() {

    if(!vm.model_data.blind_order && vm.permissions.use_imei) {
      SweetAlert.swal({
        title: '',
        text: 'You Will Lose Serial Data',
        type: 'success',
        showCancelButton: true,
        confirmButtonColor: '#33cc66',
        confirmButtonText: 'Ok',
        closeOnConfirm: true,
      },
      function (status) {
        if(status) {

          if (!vm.model_data.blind_order && vm.permissions.use_imei) {
            angular.forEach(vm.model_data.data, function(data){
              data["capacity"] = 0;
              data["serials"] = 0;
              data["location"] = "";
            })
          } else if(vm.model_data.blind_order && vm.permissions.use_imei) {
            angular.forEach(vm.model_data.data, function(data){
              data["capacity"] = 0;
              data["serials"] = 0;
              data["location"] = "";
              data.quantity = 0;
            })
          }
        } else {
          vm.model_data.blind_order = true;
        }
      });
    }
  }

  vm.checkSKULoc = function(index, data) {

    var status = false;
    for(var i = 0; i < data.length; i++) {

      if(data[i].sku_id == data[index].sku_id && data[i].location.toLowerCase() == data[index].location.toLowerCase() && i != index) {

        status = true;
        break;
      }
    }
    return status;
  }

  vm.checkCapacity = function(index, sku_data, from, element) {

    if(!sku_data.location) {

      return false;
    } else if(sku_data["orig_location"] == sku_data.location) {

      return false;
    } else {

      sku_data["orig_location"] = sku_data.location;
    }

    if (! sku_data.sku_id ) {

      return false;
    }
    element.preventDefault();

    if(vm.checkSKULoc(index, vm.model_data.data)) {

      sku_data.location = "";
      sku_data.quantity = 0;
      sku_data.invoice_amount = 0;
      vm.service.showNoty("SKU Code And Location Combination Already Exist");
      angular.element(element.target).focus();
      vm.cal_percentage(sku_data);
      return false;
    } else {

    var send = {sku_code: sku_data.sku_id, location: sku_data.location}

    vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){

      if(data.message) {

        if(data.data.status == 0) {

          vm.service.showNoty(data.data.message);
          sku_data.location = "";
          angular.element(element.target).focus();
          sku_data.quantity = 0;
          sku_data.serials = [];
          sku_data["orig_location"] = "";
          sku_data["capacity"] = 0;
          sku_data.invoice_amount = 0;
        } else {

          var data = data.data.data;
          data = Object.values(data)[0];
          sku_data["capacity"] = data.total_quantity - data.reserved_quantity;
          if(vm.permissions.use_imei) {
            sku_data.quantity = 0;
          } else {

            if (sku_data.capacity < Number(sku_data.quantity)) {
              sku_data.quantity = sku_data.capacity;
            }
          }
          sku_data.invoice_amount = Number(sku_data.quantity) * Number(sku_data.price);
          sku_data.serials = [];
        }
        vm.cal_percentage(sku_data);
      }
    })
    }
  }

  vm.change_quantity = function(data) {
    var flag = false;
    if(vm.model_data.blind_order) {

      if (! data.location) {

        data.quantity = 0;
        vm.service.showNoty("Please Enter Locaton First");
      } else if(Number(data.quantity) > Number(data["capacity"])) {

        data.quantity = data["capacity"];
        vm.service.showNoty("Location capacity "+data["capacity"]);
      }
    }

    if(data.priceRanges && data.priceRanges.length > 0) {

      for(var skuRec = 0; skuRec < data.priceRanges.length; skuRec++){

        if(data.quantity >= data.priceRanges[skuRec].min_unit_range && data.quantity <= data.priceRanges[skuRec].max_unit_range){

          data.price = data.priceRanges[skuRec].price;
          flag = true;
        }
      }

      if (!flag) {

        data.price = data.priceRanges[data.priceRanges.length-1].price;
      }
    }

    data.invoice_amount = vm.service.multi(data.quantity, data.price);
    vm.cal_percentage(data);
  }

  vm.checkAndAdd = function(scan) {

    var status = false;
    for(var i = 0; i < vm.model_data.data.length; i++) {

      if(vm.model_data.data[i].serials.indexOf(scan) > -1){
        status = true;
        break;
      }
    }
    return status;
  }
  vm.serial_scan = function(event, scan, sku_data) {
    if ( event.keyCode == 13 && scan) {
      event.preventDefault();
      sku_data.serial = "";
      if(!sku_data.sku_id) {
        vm.service.showNoty("Please Select SKU Code First");
      } else if(!sku_data.location) {
        vm.service.showNoty("Please Select Location First");
      } else {
        var elem = {serial: scan, cost_check:vm.model_data.blind_order};
        vm.service.apiCall('check_imei/', 'GET', elem).then(function(data){
          if(data.message) {
            if(data.data.status == "Success") {
              if (data.data.data.sku_code != sku_data.sku_id) {
                vm.service.showNoty("IMEI Code not matching with SKU code");
              } else if(vm.checkAndAdd(scan)) {
                vm.service.showNoty("Already Scanned")
              } else {
                sku_data.serials.push(scan);
                sku_data.quantity = sku_data.serials.length;
                sku_data.invoice_amount = vm.service.multi(sku_data.quantity, sku_data.price);
                vm.cal_percentage(sku_data);
                for(var i = 0; i < vm.model_data.data.length ; i++) {
                  if (vm.model_data.data[i]["sku_id"] == data.data.data.sku_code) {
                    vm.model_data.data[i]['cost_price'] = data.data.data.cost_price;
                  }
                }
              }
            } else {
              vm.service.showNoty(data.data.status);
            }
          }
        });
      }
    }
  }

  vm.scan_ean = function(event, field) {
    if (event.keyCode == 13 && field.length > 0) {
      console.log(field);
	  vm.scan_ean_disable = true;
	  vm.service.apiCall('create_orders_check_ean/', 'GET', {'ean': field}).then(function(data) {
		$('.scan_ean').trigger('focus').val('');
        if(data.message) {
		  if(data.data.sku) {
		  vm.get_customer_sku_prices(data.data.sku).then(function(resp) {
		  if(resp.length > 0) {
			resp = resp[0]
      resp['sku_id'] = resp.wms_code;
			var foundItem = $filter('filter')(vm.model_data.data, {'sku_id':resp.wms_code}, true)[0];
			if (foundItem) {
				var index = vm.model_data.data.indexOf(foundItem);
				var exist_qty = vm.model_data.data[index]['quantity']
				vm.model_data.data[index]['quantity'] = 1 + parseInt(exist_qty)
                vm.change_quantity(vm.model_data.data[index])
			} else {
                if (vm.model_data.data.length) {
                    if (vm.model_data.data[0]['sku_id'] == '') {
                        vm.model_data.data = []
                    }
                }
                vm.model_data.data.push({ 'capacity': 0, 'description':resp.sku_desc, 'discount': 0, 'discount_percentage':'', 'invoice_amount': resp.price, 'location':'', 'price': resp.price, 'priceRanges':[], 'quantity': 1, 'serial':'', 'serials':[], 'sku_id': resp.wms_code, 'tax': 0, 'taxes':[], 'total_amount': resp.price, 'unit_price': resp.price })
                vm.change_quantity(vm.model_data.data[0])
			}
      vm.model_data.data[0]['mrp'] = resp.mrp
      vm.update_availabe_stock(vm.model_data.data[0]);
		  }
		  })
		  } else {
		    Service.showNoty("SKU Not Found");
            return false;
		  }
        }
	  })
	}
  }

  vm.assign_tab_event = '';
  var array_list = ['SKU Code', 'Description']
  if (vm.model_data.blind_order) {
	  array_list.push('Location')
  }
  if (vm.model_data.blind_order && vm.permissions.use_imei) {
	  array_list.push('Serial Scan')
  }
  var a = ['Quantity', 'Unit Price', 'Amount', 'Discount', 'Discount Percentage']
  array_list = array_list.concat(a)
  if(vm.fields.indexOf('Tax') == -1 && vm.model_data.tax_type == 'intra_state') {
	var b = ['SGST(%)', 'CGST(%)']
	array_list = array_list.concat(b)
  }
  if(vm.fields.indexOf('Tax') == -1 && vm.model_data.tax_type == 'inter_state') {
    array_list.push('IGST(%)')
  }
  var c = ['Total Amount', 'Remarks']
  array_list = array_list.concat(c)

  angular.forEach(vm.fields, function(obj) {
    var index = array_list.indexOf(obj);
    if (index > -1) {
      array_list.splice(index, 1);
    }
  })

  if (array_list) {
	vm.assign_tab_event = array_list.reverse()[0]
  }

  vm.tab_event_check = function($event, assign_tab_event, current_value, index, data) {
	if (($event.keyCode == 13 || $event.keyCode == 9) && assign_tab_event == current_value) {
		update_data(index, data, true);
    }
  }

  vm.key_event = function($event, product, item, index) {
    if ($event.keyCode == 13) {
      if (typeof(vm.model_data.customer_id) == "undefined" || vm.model_data.customer_id.length == 0){
        return false;
      } else {
        var customer_id = vm.model_data.customer_id;
        $http.get(Session.url+'get_create_order_mapping_values/?wms_code='+product.sku_id, {withCredentials : true}).success(function(data, status, headers, config) {
          if(Object.keys(data).length){
            vm.model_data.data[index].sku_id = product.sku_id;
          } else {
            Service.searched_cust_id = customer_id;
            Service.searched_wms_code = product.sku_id;
            Service.is_came_from_create_order = true;
            Service.create_order_data = vm.model_data;
            Service.sku_id_index = index;
            Service.create_order_auto_shipment = vm.auto_shipment;
            Service.create_order_custom_order = vm.custom_order;
            $state.go('app.masters.SKUMaster');
          }
        });
      }
    }
  }

  vm.assign_sku_id_from_sku_master = function() {
    if (vm.service.is_came_from_create_order) {
      vm.model_data.customer_id = vm.service.searched_cust_id;
      Service.is_came_from_create_order = false;
      vm.model_data = Service.create_order_data;
      vm.auto_shipment = Service.create_order_auto_shipment;
      vm.custom_order = Service.create_order_custom_order;
      vm.service.searched_cust_id = '';
      vm.service.searched_wms_code = '';
    }
  }
  vm.assign_sku_id_from_sku_master();

  vm.addDiscountToInv = function(discount) {
    if (discount < vm.final_data.total_amount) {
      vm.final_data.total_amount = Number(vm.final_data.temp_total_amount) - Number(discount);
    } else {
      Service.showNoty("Please enter proper discount");
      vm.model_data.order_discount = '';
      vm.final_data.total_amount = vm.final_data.temp_total_amount;
    }
  }
  vm.model_data.payment_amounts = {}
}
angular
  .module('urbanApp')
  .controller('CreateOrders', ['$scope', '$filter','$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Data', 'SweetAlert', CreateOrders]);
