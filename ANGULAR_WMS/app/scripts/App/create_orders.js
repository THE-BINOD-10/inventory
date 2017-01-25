'use strict';

function CreateOrders($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth) {

  $scope.msg = "start";
  var vm = this;
  vm.service = Service;
  vm.auth = Auth;
  vm.order_type = false;
  vm.order_type_value = "Offline";
  vm.loading = true;
  vm.company_name = Session.user_profile.company_name;
  vm.model_data = {}
  var empty_data = {data: [{sku_id: "", quantity: "", invoice_amount: "", price: "", tax: "", total_amount: "", unit_price: ""}], 
                            customer_id: "", payment_received: "", order_taken_by: ""};
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
     
       setplaceOrder(elem);
     
        if(navigator.serviceWorker.controller) {
           navigator.serviceWorker.ready.then(function(reg) {
           if(reg.sync) {
             reg.sync.register('place_order')
              .then(function(event) {
                console.log('Sync registration successful', event);

                $scope.$apply(function(){
                angular.copy(empty_data, vm.model_data);
                });

               // colFilters.showNoty("order placed in offline mode ");
               // offlineOrders();   

              }).catch(function(error) {
                console.log('Sync registration failed', error);
              });
           }else{
             console.log(" Sync not supported");
           }
         });
       }else {
         console.log("No active ServiceWorker");
       }



     /*
     vm.service.apiCall('insert_order_data/', 'GET', elem).then(function(data){
        if(data.message) {
          if("Success" == data.data) {
            angular.copy(empty_data, vm.model_data);
            vm.final_data = {total_quantity:0,total_amount:0}
          }
          colFilters.showNoty(data.data);
        }
        vm.bt_disable = false;
      })*/
    } else {
      colFilters.showNoty("Fill Required Fields");
    }
  }

  vm.catlog = false;
  vm.categories = [];
  vm.category = "";
  vm.brand = "";
  vm.brands=[];
  vm.details = true;
  function change_filter_data() {
  
    /*db.brands.toArray().then(function(data){
      console.log("brands are "+data);
      $scope.$apply(function(){ 
     if(data.length>0){
        data.forEach(function(item){
           vm.brands.push(item.sku_brand);
        }); 
       }else{
       vm.details = false;
       }
     });
    });*/
    vm.get_brands();

  /*db.categories.toArray().then(function(data){
    $scope.$apply(function(){ 
    if(data.length>0){  
       data.forEach(function(item){ 
         vm.categories.push(item.sku_category)
       });
     }
    });
  });
  */
  vm.get_cats();
 
 /*
 vm.brands_images = {'6 Degree': 'SIX-DEGREES-1.jpg', 'AWG (All Weather Gear)': 'awg.jpg', 'BIO WASH': 'BIO-COLLECTION-1.jpg',
                   'Scala': 'SCALA-1.jpg','Scott International': 'SCOTT-1.jpg', 'Scott Young': 'SCOTT-YOUNG-1.jpg', 
                   'Spark': 'spark-1.jpg','Star - 11': 'star-11.jpg','Super Sigma': 'super-sighma.jpg', 
                   'Sulphur Cotton': 'sulphur-1.jpg', 'Sulphur Dryfit': 'sulphur-2.jpg'}

 vm.brands_logos = {'6 Degree': 'six-degrees-1.png', 'AWG (All Weather Gear)': 'awg-1.png', 'BIO WASH': 'bio-wash-1.png',
                  'Scala': 'scala-1.png','Scott International': 'scott-1.png', 'Scott Young': 'scott-young-1.png', 
                  'Spark': 'spark-1.png','Star - 11': 'star-11-1.png','Super Sigma': 'super-sigma-dryfit-1.png',
                  'Sulphur Cotton': 'sulphur-cottnt-1.png','Sulphur Dryfit': 'sulphur-dryfit-1.png', 'Spring': 'spring-1.png', 
                  '100% Cotton': '100-cotton-1.png', 'Sprint': 'sprint-1.png','Supreme': 'supreme-1.png'} 
  */

vm.brands_images = {'6 Degree': 'six-degrees.jpg', 'AWG (All Weather Gear)': 'awg.jpg', 'BIO WASH': 'bio-wash.jpg',
        'Scala': 'scala.jpg','Scott International': 'scott.jpg', 'Scott Young': 'scott-young.jpg', 'Spark': 'spark.jpg',
        'Star - 11': 'star-11.jpg','Super Sigma': 'super-sigma-dryfit.jpg', 'Sulphur Cotton': 'sulphur-cottnt.jpg', 'Sulphur Dryfit': 'sulphur-dryfit.jpg', 'Spring': 'spring.jpg', '100% Cotton': '100cotton.jpg', 'Sprint': 'sprint.jpg', 'Supreme': 'supreme.jpg', 'Sport': 'sport.jpg'}

        vm.brands_logos = {'7 Degree': 'six-degrees-1.png', 'AWG (All Weather Gear)': 'awg-1.png', 'BIO WASH': 'bio-wash-1.png',
        'Scala': 'scala-1.png','Scott International': 'scott-1.png', 'Scott Young': 'scott-young-1.png', 'Spark': 'spark-1.png',
        'Star - 11': 'star-11-1.png','Super Sigma': 'super-sigma-dryfit-1.png', 'Sulphur Cotton': 'sulphur-cottnt-1.png',                             'Sulphur Dryfit': 'sulphur-dryfit-1.png', 'Spring': 'spring-1.png', '100% Cotton': '100-cotton-1.png', 'Sprint': 'sprint-1.png',
        'Supreme': 'supreme-1.png', 'Sport': 'sport-1.png'}

 vm.get_category(true);
  
/*
  var data = {brand: vm.brand, category: vm.category, is_catalog: true};
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
   /*     vm.brands_images = {'6 Degree': 'SIX-DEGREES-1.jpg', 'AWG (All Weather Gear)': 'awg.jpg', 'BIO WASH': 'BIO-COLLECTION-1.jpg', 
	'Scala': 'SCALA-1.jpg','Scott International': 'SCOTT-1.jpg', 'Scott Young': 'SCOTT-YOUNG-1.jpg', 'Spark': 'spark-1.jpg', 
	'Star - 11': 'star-11.jpg','Super Sigma': 'super-sighma.jpg', 'Sulphur Cotton': 'sulphur-1.jpg', 'Sulphur Dryfit': 'sulphur-2.jpg'}

        vm.brands_logos = {'6 Degree': 'six-degrees-1.png', 'AWG (All Weather Gear)': 'awg-1.png', 'BIO WASH': 'bio-wash-1.png',
        'Scala': 'scala-1.png','Scott International': 'scott-1.png', 'Scott Young': 'scott-young-1.png', 'Spark': 'spark-1.png',
        'Star - 11': 'star-11-1.png','Super Sigma': 'super-sigma-dryfit-1.png', 'Sulphur Cotton': 'sulphur-cottnt-1.png',                             'Sulphur Dryfit': 'sulphur-dryfit-1.png', 'Spring': 'spring-1.png', '100% Cotton': '100-cotton-1.png', 'Sprint': 'sprint-1.png',
        'Supreme': 'supreme-1.png'}	
        vm.get_category(true);
      }
    });
   */
  }
 //change_filter_data();

  vm.style = "";
  vm.catlog_data = {data: [], index: ""}

  vm.tag_details = function(cat_name, brand) {

    vm.category = cat_name;
    if(cat_name == "All") {
      cat_name = "";
    }

    var temp_catlog_data=[];

    vm.catlog_data.index = "";
    var data = {brand: vm.brand, category: cat_name, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true} 
    vm.catlog_data.index = ""
    vm.scroll_data = false;


    var cat_Dbdata=getCategoryData(vm.brand,cat_name,vm.style, vm.order_type_value);
        cat_Dbdata.then(function(skus){
        console.log("items are "+skus);

   $scope.$apply(function(){      
          vm.catlog_data.index = "";
          angular.copy([], vm.catlog_data.data);
         
         if(skus.length>0){
              
               angular.copy(skus,vm.catlog_data.data);
             
          }
        vm.scroll_data = false;
     });
     });

    

  /*/
    db.sku_data.where("sku_brand").equalsIgnoreCase(vm.brand).and(function(sku){
        return sku.sku_category.toLowerCase()=== cat_name.toLowerCase();
     }).and(function(sku_item){
        return sku_item.sku_class.startsWith(vm.style);
     }).and(function(sku){
         if(temp_catlog_data.indexOf(sku.sku_class)==-1) {
           temp_catlog_data.push(sku.sku_class);
           return true;
         }else{
           return false;
         }
     }).toArray().then(function(skus){
       angular.copy([], vm.catlog_data.data);
       vm.catlog_data.index = "";
       $scope.$apply(function(){   
         angular.copy(skus,vm.catlog_data.data);
       });       
       vm.scroll_data = false;
     });
    
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

   */
  }

  vm.get_category = function(status, scroll) {
    vm.loading = true;
    vm.scroll_data = false;
    var cat_name = vm.category;
    if(vm.category == "All") {
      cat_name = "";
    }
    var data = {brand: vm.brand, category: vm.category, sku_class: vm.style, index: vm.catlog_data.index, is_catalog: true}
    var temp_catlog_data=[];  
    
   var cat_Dbdata=getCategoryData(vm.brand, cat_name, vm.style, vm.order_type_value);
        cat_Dbdata.then(function(skus){
        console.log("items are "+skus);
        
        $scope.$apply(function(){
         if(status) {
          vm.catlog_data.index = "";
          angular.copy([], vm.catlog_data.data);
         }
         if(skus.length>0){
            skus.forEach(function(sku_item){
               vm.catlog_data.data.push(sku_item);
            });
         }
         vm.loading = false;
         vm.scroll_data = false;      
        });  
     });
     
     /*
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
    })
   */ 
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
    vm.remove_bold(all);
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
    vm.remove_bold(all);
    var data = {brand: vm.brand}
    var category_data=[];  
    
    
   var categories_data=getCategories(vm.brand, vm.order_type_value);  
        categories_data.then(function(val){
          val.forEach(function(data){
           // console.log(data);       
            if(category_data.indexOf(data.sku_category)==-1)
              category_data.push(data.sku_category);
         });
       // console.log("list data count is "+brand_listData.length +" cat len "+caegory_data.length);
          
          if(category_data.length>0){
             vm.all_cate=category_data; 
             vm.all_cate.push("All");

             vm.category = vm.all_cate[0];
             vm.get_category(true);
             $timeout(function () {
               $(".cat-tags:first").addClass("ct-selected"); 
             }, 1000);
          }
       });

 

        
  /*
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){
      if(data.message) {

        vm.all_cate = data.data.categories; 
        if(vm.all_cate.length> 0) {
          vm.all_cate.push("All")
          vm.category = vm.all_cate[0];
          vm.get_category(true);
          $timeout(function () {
            $(".cat-tags:first").addClass("ct-selected"); 
          }, 1000);
        }
      }
    })*/
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
  vm.open_style = function(data) {
  

  var skuvarients=getskuVarients(data, vm.order_type_value);
     skuvarients.then(function(varients){
        vm.style_open = true;
          vm.catlog=true;
          vm.check_stock=true;
       $scope.$apply(function(){
         vm.style_data=[];
           angular.forEach(varients,function(varient){
             vm.style_data.push(varient);
          })
       });
     });     
 /*
  db.sku_data.where("sku_class").equalsIgnoreCase(data).toArray()
       .then(function(varients){
          vm.style_open = true;
          vm.catlog=true;
          vm.check_stock=true; 
         
          angular.forEach(varients,function(varient){
             vm.style_data.push(varient);  
          })
         
        });  
   
    vm.service.apiCall("get_sku_variants/", "GET", {sku_class: data, is_catalog: true}).then(function(data) {

      if(data.message) {
        vm.style_open = true;
        vm.catlog=true;
        vm.check_stock=true;
        vm.style_data = data.data.data;
      }
    });
   */ 
        
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
      angular.forEach(vm.style_data, function(data){

        if(data['quantity']) {
          vm.check_item(data.wms_code).then(function(stat){
            console.log(stat)
            if(stat == "true") {
              if(vm.model_data.data[0]["sku_id"] == ""){
                vm.model_data.data[0].sku_id = data.wms_code;
                vm.model_data.data[0]["image_url"] = data.image_url
                vm.model_data.data[0].quantity = Number(data.quantity);
                vm.model_data.data[0]['price'] = Number(data.price);
                vm.model_data.data[0].invoice_amount = data.price*Number(data.quantity);
                vm.model_data.data[0]['tax'] = vm.tax;
                vm.model_data.data[0]['total_amount'] = ((vm.model_data.data[0].invoice_amount/100)*vm.tax)+vm.model_data.data[0].invoice_amount;
              } else {
                var temp = {sku_id: data.wms_code,image_url:data.image_url, quantity: Number(data.quantity), invoice_amount: data.price*Number(data.quantity), price: data.price, tax: vm.tax}
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
            console.log("data is"+vm.model_data.data);
          });
        }
      });
      console.log("last data is"+vm.model_data.data);
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
  console.log(Session);
  if(Session.userName == 'sagar_fab') {
    vm.tax = 5.5;
  }
  vm.model_data.data[0].tax = vm.tax;
  empty_data.data[0].tax = vm.tax;

  vm.make_bold = function(e) {

    console.log(e);
    //var all = $(e.toElement).parent().find(".cat-tags");
    //vm.remove_bold(all);
    //$(e.toElement).addClass("ct-selected");
  }
  vm.remove_bold = function(e) {
    //angular.forEach(e, function(item){
    //  $(item).removeClass("ct-selected");
    //})
    console.log(e);
  }

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

  function checkSyncData(){
     console.log("call post message");
     return new Promise(function(resolve, reject){
        var msg_chan = new MessageChannel();

        msg_chan.port1.onmessage = function(event){
            resolve();          
         };

        if(navigator.serviceWorker.controller){
           navigator.serviceWorker.controller.postMessage("check_data",[msg_chan.port2]);
         }
    });
  }

   vm.all_brands = {Offline: [], Online: []}
   vm.get_brands = function() {

    vm.loading = true;
    vm.brands = [];
    if(vm.all_brands[vm.order_type_value].length > 0) {

      vm.brands = vm.all_brands[vm.order_type_value];
      vm.loading = false;
    } else {
      var item_data=getSkuBrands(vm.order_type_value);
      item_data.then(function(data){
 
        angular.forEach(data, function(record){
  
          vm.brands.push(record.sku_brand);
        })
        vm.all_brands[vm.order_type_value] = vm.brands;
        vm.loading = false;
      });

      var temp_brands = []
      item_data=getSkuBrands('Online');
      item_data.then(function(data){

        angular.forEach(data, function(record){

          temp_brands.push(record.sku_brand);
        })
        vm.all_brands['Online'] = temp_brands;
      });
    }
   }

   vm.get_cats = function() {

     vm.all_cate = [];
    var item_data=getSkuBrands(vm.order_type_value);
    item_data.then(function(data){

      angular.forEach(data, function(record){

        vm.all_cate.push(record.sku_category);
      })
    });
   }
   checkSyncData().then(function(){
     change_filter_data();
   });

   vm.get_order_type = function() {

    if(vm.order_type) {
      vm.order_type_value = "Online";
    } else {
      vm.order_type_value = "Offline";
    }
  }
   vm.change_order_type = function(){
     vm.order_type_value = (vm.order_type)? "Online" : "Offline";
     vm.get_brands();
     vm.get_cats();
   }

   vm.logout = function(){

     Auth.logout().then(function(){
       $state.go("user.sagarfab");
     })
   }
}

angular
  .module('urbanApp')
  .controller('CreateOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', CreateOrders]);
