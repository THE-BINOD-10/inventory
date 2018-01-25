;(function (angular) {
    "use strict";
  
   angular.module("sku", ["ngMaterial"])
           .component("sku", {
             "templateUrl": "/app/sku/sku.template.html",
             "controller"  : ["$http", "$scope", "$timeout", "$q", "$log", "urlService",
                              "manageData","printer", "$rootScope", "$location", "$window",
      function ($http, $scope, $timeout, $q, $log, urlService, manageData, printer, $rootScope, $location, $window) {
        var self = this;
        self.tax_inclusive = false;
  
      self.simulateQuery = false;
      self.isDisabled    = false;
      $scope.onlyNumbers = /^\d+$/;
  
      self.repos;
      self.querySearch   = querySearch;
      self.selectedItemChange = selectedItemChange;
      self.searchTextChange   = searchTextChange;
      self.searchText
      
      self.table_headers = false;
  
      self.submit_enable = false;
      self.qty_switch;
  
      self.names = ['Delivery Challan', 'Pre Order'];//['Delivery Challan', 'sample', 'R&D']
      self.nw_status = "";
      self.sku_data_filtered = [];

      $http.get(urlService.mainUrl+'rest_api/get_file_content/?name=sku_master&user='+urlService.userData.parent_id)
           .then( function(data) {
				self.sku_data_filtered = data.data.file_content.slice(0,500);
				self.sku_data = data.data.file_content;
				self.slice_from = 0;
				self.slice_to = 500;
                self.selected_skus = [];
            },function(error){
              getData("").then(function(data){
                if(data.length==0){
                  urlService.show_toast("offline has no sku's");
                }else{
                  self.sku_data = data;
                  intialiseMultiSelectData(self.sku_data);
                  self.selected_skus = [];
                }
              });
            });

    self.change_config = change_config;
    function change_config(switch_value, switch_name) {
      var temp_url=urlService.mainUrl+"rest_api/switches/?"+switch_name+"="+String(switch_value);
      $http({
        method: 'GET',
        url:temp_url,
        withCredential: true,
        }).success(function(data, status, headers, config) {
          $(".preloader").removeClass("ng-show").addClass("ng-hide");
          if (data == "Success") {
            angular.forEach(self.skus, function(value, index) {
              self.changeQuantity(value);
            });
          }
        }).error(function() {
          $(".preloader").removeClass("ng-show").addClass("ng-hide");
        });
      //Session.roles.permissions[switch_name] = switch_value;
    }

    var temp_url=urlService.mainUrl+"rest_api/pos_tax_inclusive/";
    $http({
      method: 'GET',
      url:temp_url,
      withCredential: true,
      }).success(function(data, status, headers, config) {
        self.tax_inclusive = data.tax_inclusive_switch;
        $(".preloader").removeClass("ng-show").addClass("ng-hide");
      }).error(function() {
        $(".preloader").removeClass("ng-show").addClass("ng-hide");
    });

	  //check sku
	  self.check_sku = check_sku;
	  self.checked_sku = false;
	  function check_sku(sku_code) {
		var check_box = $("input[name='selected_sku'][value='"+sku_code+"']");
		if(check_box.prop("checked")) {
			check_box.prop("checked", false);
            var indx = self.selected_skus.indexOf(sku_code);
            self.selected_skus.splice(indx, 1);
            for (var sk in self.sku_data_filtered) {
                if(self.sku_data_filtered[sk]["SKUCode"] === sku_code) {
                    self.sku_data_filtered[sk]["quantity"] = 0;
                    self.sku_data_filtered[sk]["sku_code"] = sku_code;
                    changeQuantity(self.sku_data_filtered[sk]);
                }
            }
            console.log(self.selected_skus);
		} else {
			check_box.prop("checked", true);
            self.selected_skus.push(sku_code);
            console.log(self.selected_skus);
			for (var sk in self.sku_data_filtered) {
				if(self.sku_data_filtered[sk]["SKUCode"] === sku_code) {
                    self.sku_data_filtered[sk]["checked"] = true;
					update_search_results([self.sku_data_filtered[sk]], sku_code);
                    cal_total();
				}
			}
		}
	  }

	  //sku pagination
	  self.sku_pagination = sku_pagination;
	  function sku_pagination(type) {
		//$(".preloader").removeClass("ng-hide").addClass("ng-show");
		if(type === "next") {
      if(self.slice_from < self.sku_data.length){
  			self.slice_from += 500;
  			self.slice_to += 500;
      }else{
        urlService.show_toast("No more SKUs to show");
      }
		} else {
      if(self.slice_from != 0){
  			self.slice_from -= 500;
  			self.slice_to -= 500;
      }else{
        urlService.show_toast("Already at begining");
      }
		}

		self.sku_data_filtered = self.sku_data.slice(self.slice_from, self.slice_to);
        for (var sk in self.sku_data_filtered) {
            if(self.selected_skus.indexOf(self.sku_data_filtered[sk]["SKUCode"]) === -1) {
                self.sku_data_filtered[sk]["checked"] = false;
            } else {
                self.sku_data_filtered[sk]["checked"] = true;
            }
        }
	  }

    //uncheck all the select sku fields
    function uncheckMultiSelectSkus(){
       for(var sk in self.sku_data_filtered) {
          self.sku_data_filtered[sk]["checked"] = false;
       }
       for (var sk in self.sku_data) {
          $('input[name="selected_sku"][value="'+self.sku_data[sk]["SKUCode"]+'"]').prop("checked", false);
       }
       self.selected_skus = [];
    }
     //intialise first data
     function intialiseMultiSelectData(data){
      self.slice_from = 0;
      self.slice_to = 500;
      self.sku_data_filtered=data.slice(self.slice_from,self.slice_to );
     }
    
	  self.hide_load = hide_load;
	  function hide_load(last) {
		//last ? $(".preloader").addClass("ng-hide") : $(".preloader").removeClass("ng-hide");
	  }
	  self.checkbox_click = checkbox_click;
	 function checkbox_click($event, sku_code, index) {
		//$event.stopPropagation();
		var check_box = $("input[name='selected_sku'][value='"+sku_code+"']");
		if(check_box.prop("checked")) {
			check_box.prop("checked", false);
		} else {
			check_box.prop("checked", true);
		}
	 }

      //calculate total items
      self.cal_total = cal_total;
      function cal_total(){
        urlService.current_order.summary.total_amount = 0;
        urlService.current_order.summary.total_quantity = 0;
        urlService.current_order.summary.total_discount = 0;
        urlService.current_order.summary.total_returned = 0;
        urlService.current_order.summary.subtotal = 0;
        urlService.current_order.summary.sgst = 0;
        urlService.current_order.summary.cgst = 0;
        urlService.current_order.summary.igst = 0;
        urlService.current_order.summary.utgst = 0;
        urlService.current_order.summary.gst_based = {};
        for (var i = 0; i < self.skus.length; i++){
    		  if(self.skus[i].return_status === "true") {
      			self.skus[i].unit_price = self.skus[i].unit_price < 0 ? self.skus[i].unit_price : -self.skus[i].unit_price;
      			self.skus[i].sgst = self.skus[i].cgst = self.skus[i].igst = self.skus[i].utgst = 0;
  		    }
          self.skus[i].price = self.skus[i].quantity * self.skus[i].unit_price;
          
          urlService.current_order.summary.total_amount += self.skus[i].price;
          urlService.current_order.summary.subtotal += self.skus[i].price;
          urlService.current_order.summary.sgst += (self.skus[i].sgst * self.skus[i].quantity);
          urlService.current_order.summary.cgst += (self.skus[i].cgst * self.skus[i].quantity);
          urlService.current_order.summary.igst += (self.skus[i].igst * self.skus[i].quantity);
          urlService.current_order.summary.utgst += (self.skus[i].utgst * self.skus[i].quantity);
          if (!self.tax_inclusive) {
            urlService.current_order.summary.sgst = -urlService.current_order.summary.sgst;
            urlService.current_order.summary.cgst = -urlService.current_order.summary.cgst;
            urlService.current_order.summary.igst = -urlService.current_order.summary.igst;
            urlService.current_order.summary.utgst = -urlService.current_order.summary.utgst;
          }
          urlService.current_order.summary.total_quantity += self.skus[i].quantity;

          if(Object.keys(urlService.current_order.summary.gst_based).includes(self.skus[i].cgst_percent.toString())) {
              urlService.current_order.summary.gst_based[self.skus[i].cgst_percent]["taxable_amt"] += self.skus[i].price;
              
              if (self.tax_inclusive) {
                urlService.current_order.summary.gst_based[self.skus[i].cgst_percent]["cgst"] += (self.skus[i].cgst_percent *
                                                 (self.skus[i].price)/100);
                urlService.current_order.summary.gst_based[self.skus[i].cgst_percent]["sgst"] += (self.skus[i].sgst_percent *
                                                 (self.skus[i].price)/100);
              } else {
                urlService.current_order.summary.gst_based[self.skus[i].cgst_percent]["cgst"] -= (self.skus[i].cgst_percent *
                                                 (self.skus[i].price)/100);
                urlService.current_order.summary.gst_based[self.skus[i].cgst_percent]["sgst"] -= (self.skus[i].sgst_percent *
                                                 (self.skus[i].price)/100);
              }

          } else {
              urlService.current_order.summary.gst_based[self.skus[i].cgst_percent] =
                            {"taxable_amt": self.skus[i].price,
                             "cgst_percent" : self.skus[i].cgst_percent,
                             "sgst_percent" : self.skus[i].sgst_percent,
                             "cgst": (self.skus[i].cgst_percent * (self.skus[i].price)/100),
                             "sgst": (self.skus[i].sgst_percent * (self.skus[i].price)/100)
                            }
          }
          urlService.current_order.summary.cgst = Math.abs(urlService.current_order.summary.cgst);
          urlService.current_order.summary.sgst = Math.abs(urlService.current_order.summary.sgst);
          if (self.tax_inclusive) {
            self.skus[i].price = self.skus[i].price + (self.skus[i].cgst * self.skus[i].quantity) + (self.skus[i].sgst * self.skus[i].quantity);
          }
		  if (self.skus[i].return_status === "true" ) {
			    urlService.current_order.summary.total_discount += 0;
          urlService.current_order.summary.total_returned += -self.skus[i].price;
          }
		  else
            if (!self.tax_inclusive) {
              urlService.current_order.summary.total_discount += (self.skus[i].selling_price * self.skus[i].quantity) - self.skus[i].price;
            }

          if ((self.skus.length-1) == i) {
            urlService.current_order.summary.total_amount = urlService.current_order.summary.total_amount;

            urlService.current_order.summary.total_amount = urlService.current_order.summary.total_amount + urlService.current_order.summary.sgst + urlService.current_order.summary.cgst + urlService.current_order.summary.igst + urlService.current_order.summary.utgst;
          }
        }
        urlService.current_order.summary.issue_type = self.issue_selected;
        var date=new Date();
        urlService.current_order.summary.invoice_number = "TI/"+(date.getMonth()+1)+date.getFullYear().toString().substr(2)+"/";
        self.table_headers = (self.skus.length > 0) ? true : false;
      }

	  //select customer first
	  self.isCustomer = isCustomer;
	  function isCustomer() {
		if(Object.keys(urlService.current_order.customer_data).length===0 && self.issue_selected === "Pre Order") {
			alert("Please select a customer");
		}
	  }
      //customer order
      self.submit_data = submit_data;
      function submit_data() {
        self.payment = {}
        angular.forEach(urlService.current_order.summary.paymenttype_values, function (index_value, index) {
          self.payment[index_value['type_name']] = index_value['type_value'];
        })
        delete(urlService.current_order.summary.paymenttype_values);
        $rootScope.$broadcast('empty_payment_values');
        urlService.current_order.summary.payment = self.payment;
        if(self.issue_selected !== "Pre Order") {
            if (urlService.current_order.sku_data.length > 0) {
                if (urlService.current_order.customer_data.Number == null) {
                    urlService.current_order.customer_data.Number = "";
                }
                if (urlService.current_order.customer_data.value == null) {
                    urlService.current_order.customer_data.value = "";
                }
                urlService.current_order["user"] = urlService.userData
                urlService.current_order.summary.issue_type = self.issue_selected;
                self.customer_order(urlService.current_order);
            } else {
                self.submit_enable = false;
            }
        } else {
            if (urlService.current_order.sku_data.length > 0 && urlService.current_order.customer_data.FirstName.length > 0) {
                if (urlService.current_order.customer_data.Number == null) {
                    urlService.current_order.customer_data.Number = "";
                }
                if (urlService.current_order.customer_data.value == null) {
                    urlService.current_order.customer_data.value = "";
                }
                urlService.current_order["user"] = urlService.userData
                urlService.current_order.summary.issue_type = self.issue_selected;
                self.customer_order(urlService.current_order);
            } else {
                self.submit_enable = false;
            }
        }
      }

      //print order
      self.print_order = print_order;
      function print_order(data,user) {
  
        var date = new Date().toDateString();

        if (data.summary.issue_type == 'Delivery Challan') {
           printer.print('/app/views/print.html', {'data': urlService.current_order, 'user':urlService.userData, 'print': '',
                        'date': date, 'print_type': ''});
         } else {
           printer.print('/app/views/pre_order_print.html', {'data': urlService.current_order, 'user':urlService.userData, 'print': '',
                       'date': date, 'print_type': ''});
         }
      }
  
      self.store_data = store_data;
      function store_data(data, state) {
  
        data['status'] = state;
        if (urlService.hold_data.length == 5) {
          urlService.hold_data.splice(0,1);
          urlService.hold_data.push(data);
        } else {
          urlService.hold_data.push(data);
        }
      }
  
      //clear all fields
      self.clear_fields = clear_fields;
      function clear_fields() {
  
        self.searchText = '';
        self.table_headers = false;
        urlService.current_order = {"customer_data" : {"FirstName": "", "Number": "", "value": ""},
                                    "sku_data" : [],
                                    "summary":{"total_quantity": 0 , "total_amount": 0, "total_discount": 0, "subtotal": 0, "VAT": 0,
                                    "issue_type": self.issue_selected, "order_id": 0, "nw_status": "online", 'invoice_number': '',
                                    "order_date":''},
                                    "money_data": {}};
        self.skus= urlService.current_order.sku_data;
        manageData.prepForBroadcast("clear");

        //clear the selected skus in multi select
        uncheckMultiSelectSkus();
      }

      //change issue type
      self.change_issue_type = change_issue_type;
      function change_issue_type(issue_type){
        $rootScope.issue_type = issue_type;
        $rootScope.$broadcast('change_issue_type');

      }
      /*self.change_issue_type = change_issue_type;
      function change_issue_type(){
       // debugger;
        if (urlService.current_order.sku_data.length !== 0) {
           var old_type = urlService.current_order.summary.issue_type;
           var sure = confirm("Changing issue type will discard current orders.\nPress OK to continue.");//self.issue_selected
           sure ? clear_fields() : self.change_issue_type = old_type;
        } else {
           //debugger;
        }
      }*/
  
      // unhold holded customer order
      $scope.$on('change_current_order', function(){

        self.skus = urlService.current_order.sku_data;
        self.table_headers = ( self.skus.length>0 )? true : false;
      })
  
      // ajax call to send data to backend
      self.customer_order = customer_order;
      function customer_order(data) {
 
        data["summary"]["nw_status"] = 'online';
        self.submit_enable = true;

        //adding order date
        var date_order=new Date();
        var temp_date=date_order.getDate() +"-"+date_order.getMonth()+"-"+date_order.getFullYear().toString();
        urlService.current_order.summary.order_date=temp_date;
        //change the status for preorder0
        if(data.summary.issue_type=="Pre Order"){
            data.status="1";
        }else{
            data.status="0";
        }
  
              data.summary.nw_status = ONLINE;
              var order_data=data;
            var data = $.param({
                    order : JSON.stringify(data)
                });

       $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";

          $http.post( urlService.mainUrl+'rest_api/customer_order/', data).
          then(function(data) {

            data=data.data;
            if(data.message === "invalid user") {
                    $window.location.reload();
            } else {
              urlService.current_order.order_id = data.order_ids[0];
              var state = 1
              store_data(urlService.current_order, state);
              print_order(urlService.current_order, urlService.userData)
              console.log(data);
              self.submit_enable = false;

              //update the current order id
              data=data.order_ids[0]+1;
              setCheckSum(setOrderID(data)).
                then(function(data){
                  console.log("order id updated");
              }).catch(function(error){
                  console.log("order id updated error "+error);
              });

          }
            clear_fields();
          },function(error){

                //change the network status
            order_data.summary.nw_status = OFFLINE;
            $rootScope.sync_status = true;
            $rootScope.$broadcast('change_sync_status');

            setSynOrdersData(order_data,self.qty_switch).
                  then(function(data){
    
                      if(data.is_all_return==true){
                        urlService.current_order.order_id = "return";
                      }else{
                      urlService.current_order.order_id = data.order_id;
                      }

                      var state = 1;
                      store_data(urlService.current_order, state);
                      print_order(urlService.current_order, urlService.userData)
                      console.log(data);
                      self.submit_enable = false;
                                 
                                       
                    }).then(function(){
  
                      clear_fields();
                       //auto sync when network available
                      syncPOSData(false).then(function(data){

                       // $rootScope.sync_status = false;
                       // $rootScope.$broadcast('change_sync_status');
                      });
  
                    }).catch(function(error){
                       console.log("order saving error "+error);
                    });

          });

          
      }
  
      self.hold_data = hold_data;
      function hold_data() {
        if (urlService.current_order.sku_data.length > 0 && urlService.current_order.customer_data.FirstName.length > 0) {
          console.log("data stored");
          var state = 0
          store_data(urlService.current_order, state);
          urlService.current_order = {"customer_data" : {},
                                      "sku_data" : [],
                                      "summary":{"total_quantity": 0 , "total_amount": 0, "total_discount": 0, "subtotal": 0, "VAT": 0,
                                      "issue_type": self.issue_selected,"order_id":0, "nw_status":"online", 'invoice_number': '',
                                      "order_date":''},
                                      "money_data": {}};
          console.log(urlService.hold_data);
          self.skus = urlService.current_order.sku_data;
          self.table_headers = false;
          manageData.prepForBroadcast("clear");
        }
      }
  
      self.get_product_data = get_product_data;

      function update_search_results(filter_data, key) {
          for (var i=0; i<filter_data.length; i++) {
           if(filter_data.length === 1) {
            if(filter_data[i].SKUCode===key) {
              self.searchText = "";
              self.repeated_data = false;
              for (var j=0; j< self.skus.length; j++) {
                if (self.skus[j].sku_code === key) {
                  var quantity = 0;

                  if (!self.qty_switch && !self.return_switch && self.issue_selected === "Delivery Challan" &&
                                            self.skus[j].stock_quantity == self.skus[j].quantity) {

                    alert("Given Quantity is more than Stock Quantity.");
                  } else {
                    quantity = 1;
                  }
                  self.skus[j].quantity = parseInt(self.skus[j].quantity) + quantity;
                  self.skus[j].price = self.skus[j].quantity * self.skus[j].unit_price;
                  self.repeated_data = true;
                  self.skus[j].return_status = self.return_switch.toString();
                  break;
                }
              }
              if (!self.repeated_data) {
             
                if (!self.qty_switch && !self.return_switch && self.issue_selected === "Delivery Challan" && filter_data[i].stock_quantity == 0) {
                  alert("Given SKU stock is empty.");
                  $("input[name='selected_sku'][value='"+filter_data[0]["SKUCode"]+"']").prop("checked", false);
                  break;
                } else {
  
                  //var quantity = (filter_data[i].stock_quantity > 0) ? 1: 0;
                  //Change the quantity to 1
                  var quantity = 1;

                  var sgst = filter_data[i].price * filter_data[i].sgst / 100;
                          var cgst = filter_data[i].price * filter_data[i].cgst / 100;
                          var igst = filter_data[i].price * filter_data[i].igst / 100;
                        var utgst= filter_data[i].price * filter_data[i].utgst / 100;
                  self.skus.push({'name': filter_data[i].ProductDescription, 'unit_price': filter_data[i].price, 'quantity': quantity,
                                  'sku_code': filter_data[i].SKUCode, 'price': filter_data[i].price ,'discount':filter_data[i].discount,
                                  'selling_price':filter_data[i].selling_price, 'stock_quantity': filter_data[i].stock_quantity,
                                  'sgst': sgst, 'cgst': cgst, 'igst': igst, 'utgst': utgst, 'sgst_percent': filter_data[i].sgst,
                                  'cgst_percent': filter_data[i].cgst, 'igst_percent': filter_data[i].igst,
                                  'utgst_percent': filter_data[i].utgst, 'return_status': self.return_switch.toString()});
                  urlService.current_order.sku_data = self.skus;
                  break;
  
                }
              }
            }
           }
          }
        }
  
      function get_product_data(key) {

          if(key.length>1){
              var deferred = $q.defer();
              $http.get(urlService.mainUrl+'rest_api/search_product_data/?user='+urlService.userData.parent_id+'&key='+key)
                .then( function(data) {
                  data=data.data;
                  if(data.message === "invalid user") {
                    $window.location.reload();
                 } else {
                  console.log("online");
                  self.repos = data;
                  if(data.length === 1){
                    update_search_results(data, data[0].SKUCode);
                  } else {
                        return self.repos.map( function (repo) {
                        repo.value = repo.search.toLowerCase();
                        return repo;
                        })
                    }
                 }
                },function(error){
                  console.log("offline");
                   getData(key).then(function(data){
                      self.repos = data;
                      //deferred.resolve(data);
                      return self.repos.map( function (repo) {
                         repo.value = repo.search.toLowerCase();
                       return repo;
                      })
                    });
                }).then(function() {
                  deferred.resolve(querySearch (key));
                  deferred.promise.then(function(data){
                    angular.forEach(self.skus, function(value, index) {
                      self.changeQuantity(value);
                    });
                  });
                });
             return deferred.promise;
        }
      return [];
    }
  
  
      self.removeProduct = removeProduct;
      function removeProduct(name) {
  
        for (i = 0; i < self.skus.length; i++) {
  
          if (name ==  self.skus[i].name) {
  
            self.skus.splice(i, 1);
            cal_total();
            break;
          }
        }
      }
  
      self.increaseQuantity = increaseQuantity;
    function increaseQuantity(code) {
  
        for (i = 0; i < self.skus.length; i++) {
  
          if (code ==  self.skus[i].sku_code) {
  
            self.skus[i].quantity += 1;
            self.skus[i].price = self.skus[i].unit_price * self.skus[i].quantity;
            cal_total();
            break;
          }
        }
      }
  
      self.decreaseQuantity = decreaseQuantity;
      function decreaseQuantity(code) {
  
        for (i = 0; i < self.skus.length; i++) {
  
          if ((code ==  self.skus[i].sku_code) && (self.skus[i].quantity > 1)) {
  
            self.skus[i].quantity -= 1;
            self.skus[i].price = self.skus[i].unit_price * self.skus[i].quantity;
            cal_total();
            break;
          } else if (self.skus[i].quantity == 1) {
  
            self.skus.splice(i, 1);
            cal_total();
            break;
          }
        }
      }
  
      self.update_quantity = 0;
      self.changeQuantity = changeQuantity;
      function changeQuantity(item) {
        console.log(item);
  
        if (!self.qty_switch && !self.return_switch && self.issue_selected === "Delivery Challan" && item.quantity > item.stock_quantity) {
          alert("Given Quantity is more than Stock Quantity.");
        item.quantity = item.stock_quantity;
        }
  
        for (var i = 0; i < self.skus.length ; i ++) {
  
          if (self.skus[i].sku_code == item.sku_code){
  
            if( (item.quantity == 0) || (item.quantity == "0")) {
  
              self.skus.splice(i, 1);
              cal_total();
            } else {

              self.skus[i].quantity = parseInt(item.quantity);
              self.skus[i].discount = (item.discount) ? parseInt(item.discount) : 0;
              self.skus[i].unit_price = (item.selling_price - ((item.selling_price/100)*item.discount));
              if(self.tax_inclusive) {
                self.skus[i].unit_price = self.skus[i].unit_price - self.skus[i].cgst - self.skus[i].sgst;
              }
              cal_total();
            }
            break;
          }
        }
      }
  
      self.changePrice = changePrice;
      function changePrice(item, prev) {
        console.log(item);
        if(item.price !== prev) {
  
            for (var i = 0; i < self.skus.length ; i ++) {
      
              if (self.skus[i].sku_code == item.sku_code){
      
                if( (item.price == 0) || (item.price == "0")) {
                  item.price = 0;
                  item.unit_price = 0;
                  item.selling_price = 0;
                  item.discount = 0;
                  item.total_discount = 0;
				  item.cgst=item.sgst=item.utgst=item.igst=0;
                  cal_total();
                } else {
     
                  item.selling_price = item.price;
                  self.skus[i].quantity = parseInt(item.quantity);
                  self.skus[i].discount = (item.discount && self.skus[i].return_status==='false') ? parseInt(item.discount) : 0;
				  self.skus[i].sgst = item.price * self.skus[i]['sgst_percent'] / 100;
				  self.skus[i].cgst = item.price * self.skus[i]['cgst_percent'] / 100;
				  self.skus[i].igst = item.price * self.skus[i]['igst_percent'] / 100;
				  self.skus[i].utgst= item.price * self.skus[i]['utgst_percent'] / 100;
                  urlService.current_order.sku_data = self.skus;
  self.skus[i].unit_price = (item.selling_price - ((item.selling_price/100)*item.discount));
                  cal_total();
                }
                break;
              }
            }
        }
      }

      
  
      // Internal methods
      function querySearch (query) {
        var results = query ? self.repos.filter( createFilterFor(query) ) : self.repos,
            deferred;
        if (self.simulateQuery) {
          deferred = $q.defer();
          $timeout(function () { deferred.resolve( results ); }, Math.random() * 1000, false);
          return deferred.promise;
        } else {
          return results;
        }
      }
  
      function searchTextChange(text) {
        $log.info('Text changed to ' + text);
      }

      //multi select sku popup
      self.all_skus_popup = all_skus_popup;
      function all_skus_popup() {
              $('#skuModal').modal('show');
      }

      self.skus = [] //urlService.current_order.sku_data;
      function selectedItemChange(item) {
        if (!(typeof(item) == "undefined")) {
          update_search_results([item], item.SKUCode);
          cal_total();
          self.searchText = "";
        }
      }
  
      // Create filter function for a query string
      function createFilterFor(query) {
        var lowercaseQuery = angular.lowercase(query);
  
        return function filterFn(item) {
        return (item.value.indexOf(lowercaseQuery) >= 0);
        };
  
      }
  
      //printer.print('/HOME1/app/views/print.html', {patient: {name: 'Ram Kumar', dateOfBirth: '1978-08-23', gender: 'M'}})
      self.print = print
      var print = function (templateUrl, data) {
      $http.get(templateUrl).success(function(template){
          var printScope = angular.extend($rootScope.$new(), data);
          var element = $compile($('<div>' + template + '</div>'))(printScope);
          var waitForRenderAndPrint = function() {
              if(printScope.$$phase || $http.pendingRequests.length) {
                  $timeout(waitForRenderAndPrint);
              } else {
                  printHtml(element.html());
                  printScope.$destroy(); // To avoid memory leaks from scope create by $rootScope.$new()
              }
          }
          waitForRenderAndPrint();
      });
     };
  
      $scope.filterValue = function($event){
              if(isNaN(String.fromCharCode($event.keyCode))){
                        $event.preventDefault();
                        }
               };
  
      }]
    })
  }(window.angular));
