'use strict';

function CreateOrders($scope, $http, $q, Session, colFilters, Service) {

  $scope.msg = "start";
  var vm = this;
  vm.service = Service;
  vm.model_data = {data: [], customer_id: ""}
  var item_data = [{sku_id: "", quantity: "", invoice_amount: ""}]
  var empty_data = {data: [], customer_id: ""};
  vm.isLast = isLast;
 // vm.offline_orders_count=0; 

    function isLast(check) {
      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      vm.model_data.data.push({sku_id: "", quantity: "", invoice_amount: ""});
    } else {
      vm.model_data.data.splice(index,1);
    }
  }

  vm.remove_item = function(index) {

    vm.model_data.data.splice(index,1);
   setItemDb("addtocart",vm.model_data);
  }

  vm.get_customer_data = function(id) {
    if(id && id != "") {
      vm.service.apiCall('get_customer_data/', 'GET', {id: id}).then(function(data){
        if(data.message) {
          if(data.data == "") {
            make_empty();
          } else {
            vm.model_data["customer_name"] = data.data.name;
            vm.model_data["telephone"] = parseInt(data.data.phone_number);
            vm.model_data["email_id"] = data.data.email_id;
            vm.model_data["address"] = data.data.address;
          }
        }
      })
    } else {
      make_empty()
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
    
    if(vm.model_data.shipment_date) {
  
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
  
      
      if(navigator.onLine){  
        vm.service.apiCall('insert_order_data/', 'GET', elem).then(function(data){
          if(data.message) {
            if("Success" == data.data) {
              angular.copy(empty_data, vm.model_data);
            }
           colFilters.showNoty(data.data);
          }
        vm.bt_disable = false;
      })
     }else{
      
      local_pending_orders.setItem(new Date().getTime(),JSON.stringify(elem)).then(function(vlaue){
    
       localforage.removeItem("addtocart").then(function(){
 
         if(navigator.serviceWorker.controller) {
           navigator.serviceWorker.ready.then(function(reg) {
           if(reg.sync) {
             reg.sync.register('place_order')
              .then(function(event) {
                console.log('Sync registration successful', event);

                $scope.$apply(function () {
                angular.copy(empty_data, vm.model_data);
                });  

                colFilters.showNoty("order placed in offline mode ");
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
      });

      }).catch(function(err){
         console.log("order is not stored in local");
      });
     }         
    }else{
      colFilters.showNoty("Fill Required Fields");
   }
 }

  vm.catlog = true;
  vm.categories = [];
  vm.service.apiCall("get_sku_categories/").then(function(data){
  
    if(data.message) {

      vm.categories = data.data.categories;
     // vm.category = vm.categories[0];
      //set to local db
      setItemDb('categories',vm.categories);
      vm.get_category();
    }else{

    localforage.getItem('categories',function (err,value) {
     // Do other things once the value has been saved.
     if(err){
          console.log("getting categories values are "+err);
    } else{
          if(value!=null){
          console.log("getting categories values are "+value);
          vm.categories =JSON.parse(value);
         // vm.category = vm.categories[0];
          vm.get_category();

     }}});

  }});

  vm.category = "";
  vm.style = "";
  vm.catlog_data = {data: [], index: ""}
  vm.get_category = function(status, scroll) {
   
   if(vm.catlog && !(vm.style_open)) {
      var data = {brand: vm.brand,category: vm.category, sku_class: vm.style, index: vm.catlog_data.index}
      //$(window).off("scroll")0;
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

        // set to local db   
          if(vm.catlog_data.data.length>0){
            setItemDb(vm.brand+"_"+vm.category,vm.catlog_data);
          }
        }else{

          localforage.getItem(vm.brand+"_"+vm.category,function(err,value){

          if(err){
             console.log(vm.brand+"_"+vm.category +"getting error "+err)
          }else{
            if(value!=null){
              console.log(vm.brand+"_"+vm.category +"getting data "+value)

              vm.catlog_data.index = "";
              angular.copy([], vm.catlog_data.data);

              var data=JSON.parse(value);
              vm.catlog_data.index=data.index;

	      $scope.$apply(function () {

                angular.forEach(data.data, function(item){
                  vm.catlog_data.data.push(item);
                });
              });

            }

         }
       });
      }

      if(scroll) {
        $(window).scroll(scrollHandler);
      }
    })
   }
  }

  $(window).scroll(scrollHandler);

  function scrollHandler(e) {
      e.stopImmediatePropagation();
      if($(window).scrollTop() + $(window).height() > $(document).height() - 100) {
          $(window).off("scroll");
          vm.get_category(false, true);
      }
  }

  vm.category_change = function() {

    vm.catlog_data.index = "";
    angular.copy([], vm.catlog_data.data);
    vm.get_category(true);
  }
  vm.style_change = function() {

    vm.catlog_data.index = "";
    angular.copy([], vm.catlog_data.data);
    vm.get_category(true);
  }

  vm.style_open = false;
  vm.style_data = [];
  vm.open_style = function(data) {
  var sel_style=data;

    vm.service.apiCall("get_sku_variants/", "GET", {sku_class: data}).then(function(data) {

      if(data.message) {
        vm.style_open = true;
        vm.check_stock=false
        vm.style_data = data.data.data;
        angular.forEach(vm.style_data, function(record){
          record["quantity"] = 0;
        })

       //set to local db
       setItemDb(sel_style,data);  

      }else{

        localforage.getItem(sel_style,function(err,value){

          if(err){
            console.log(sel_style +" geting error "+err);
          }else{
           
            if(value!=null){
              console.log(sel_style+"getting values are "+value);
              data=JSON.parse(value);

             if(data.message) {
               vm.style_open = true;
               vm.check_stock=false
               vm.style_data = data.data.data;
          
               angular.forEach(vm.style_data, function(record){
                 record["quantity"] = 0;
               })
             }
          }
        }
     });
    }});
  }

  vm.check_item = function(sku) {

    var d = $q.defer();
    if (vm.model_data.data.length == 0) {
      d.resolve('true');
    } else {
      angular.forEach(vm.model_data.data, function(data, index){
        if(data.sku_id == sku) {
          d.resolve(String(index));
        } else if ((vm.model_data.data.length-1) == index) {
          d.resolve('true');
        }
      })
    }
    return d.promise;
  }

  vm.add_to_cart = function() {

    angular.forEach(vm.style_data, function(data){

      if (data['quantity']) {
        vm.check_item(data.wms_code).then(function(stat){
          console.log(stat)
          if(stat == "true") {
            /*if(vm.model_data.data[0]["sku_id"] == "") {
              vm.model_data.data[0].sku_id = data.wms_code;
              vm.model_data.data[0].quantity = Number(data.quantity);
              vm.model_data.data[0].invoice_amount = data.price*Number(data.quantity);
              vm.model_data.data[0]["sku_desc"] = data.sku_desc
              vm.model_data.data[0]["image_url"] = data.image_url
              vm.model_data.data[0]["price"] = data.price
            } else {*/
              vm.model_data.data.push({sku_id: data.wms_code, quantity: Number(data.quantity), invoice_amount: data.price*Number(data.quantity), sku_desc: data.sku_desc, image_url: data.image_url, price: data.price})
     
          } else {
             var temp = Number(vm.model_data.data[Number(stat)].quantity);
             vm.model_data.data[Number(stat)].quantity = temp+Number(data.quantity);
             vm.model_data.data[Number(stat)].invoice_amount = Number(data.price)*vm.model_data.data[Number(stat)].quantity;
             vm.model_data.data[Number(stat)]["sku_desc"] = data.sku_desc
             vm.model_data.data[Number(stat)]["image_url"] = data.image_url
          }
            setItemDb("addtocart",vm.model_data);
        });
      }
    });
    vm.service.showNoty("Succesfully Added to Cart");
  }

  vm.check_stock = false;
  vm.enable_stock = function(){
    if(vm.check_stock) {
      vm.check_stock = false;
    } else {
      vm.check_stock = true;
    }
  }

  vm.change_quantity = function(data, stat) {

    if (stat) {

      data.quantity = Number(data.quantity) + 1
    } else {
      if (Number(data.quantity)> 0) {
        data.quantity = Number(data.quantity) - 1
      }
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

    setItemDb("addtocart",vm.model_data);
  }

  vm.shipment_date = ""
  vm.lions = false

  vm.filter_change = function() {

    vm.catlog_data.index = "";
    angular.copy([], vm.catlog_data.data);
    //change_filter_data();
    vm.get_category(true);
  }

  vm.categories = [];
  vm.category = "";
  vm.brand = "";
  function change_filter_data() {
    var data = {brand: vm.brand, category: vm.category};
    vm.service.apiCall("get_sku_categories/", "GET",data).then(function(data){

      if(data.message) {

        vm.categories = data.data.categories;
        vm.brands = data.data.brands;
        vm.get_category(true);

        setItemDb('categories',vm.categories);
        setItemDb('brands',vm.brands);
      }else{
         
        localforage.getItem('brands',function(err,data){
         
            if(err){
               console.log("brands data getting error "+err);
            }else{
               console.log("brands data is "+data);
               if(data!=null){
                  vm.brands=JSON.parse(data);
               }
             }
        });     

        localforage.getItem('categories',function(err,data){
         
            if(err){
               console.log("category local data getting error "+err);
            }else{
               console.log("category local data is "+data);
               if(data!=null){
                  vm.categories=JSON.parse(data);
               }
              
              vm.get_category(true);
             }
        });     
 
      }
    });
  }

  function offlineOrders(){

    local_pending_orders.length().then(function(offline_count){

      $scope.$apply(function () {
        vm.offline_orders_count=offline_count;    
      });  
   });   
  };


 function offlineData(){

   var data = {name:"sku_master"};
    vm.service.apiCall("get_file_checksum/", "GET",data).then(function(data){

      if(data.message) {
         if(Object.keys(data.data).length>0)  
           var file_data=data.data.file_data;
           var file_content=data.data.file_content;
            if(file_content.length>0 && file_content.brands_data.length>0){}
                   

       }

     });
  }

 


  offlineData();
 // change_filter_data();
}

angular
  .module('urbanApp')
  .controller('CreateOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', CreateOrders]);
