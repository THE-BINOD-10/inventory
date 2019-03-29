;(function (angular) {
    "use strict";

   angular.module("sku", ["ngMaterial"])
           .component("sku", {
             "templateUrl": "/app/sku/sku.template.html",
             "controller"  : ["$http", "$scope", "$timeout", "$q", "$log", "urlService",
                              "manageData","printer", "$rootScope", "$location", "$window",
      function ($http, $scope, $timeout, $q, $log, urlService, manageData, printer, $rootScope, $location, $window) {
        var self = this;
        self.tax_inclusive = true;
        self.send_email = false;

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
      self.style_based_sku_data = [];


      $http.get(urlService.mainUrl+'rest_api/get_file_content/?name=sku_master&user='+urlService.userData.parent_id)
           .then( function(data) {
              self.sku_data_filtered = data.data.file_content.slice(0,500);
              self.sku_data = data.data.file_content;
              self.slice_from = 0;
              self.slice_to = 500;
              self.selected_skus = [];
            },function(error){
              getOflfineSkuContent();

            });

      //get offline sku conntent
      function getOflfineSkuContent(){
        getData("").then(function(data){
                if(data.length==0){
                  if(self.sku_data.length<0)
                    urlService.show_toast("offline has no sku's");

                  //uncheck selected sku's
                  for(var sk in self.sku_data_filtered) {
                    self.sku_data_filtered[sk]["checked"] = false;
                  }

                  for (var sk in self.sku_data) {
                    $('input[name="selected_sku"][value="'+self.sku_data[sk]["SKUCode"]+'"]').prop("checked", false);
                  }
                  //clear the dialog filtered data
                  self.sku_data_filtered=[];
                  //clear the selected skus
                  self.selected_skus = [];
                  intialiseMultiSelectData(self.sku_data);
                }else{
                  self.sku_data = data;
                  intialiseMultiSelectData(self.sku_data);
                  self.selected_skus = [];
                }
              });
      }

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
        }).catch(function(error){
          angular.forEach(self.skus, function(value, index) {
            self.changeQuantity(value);
          });
          console.log("no network");
        });
    }
    var temp_url=urlService.mainUrl+"rest_api/pos_tax_inclusive/";
    $http({
      method: 'GET',
      url:temp_url,
      withCredential: true,
      }).success(function(data, status, headers, config) {
        self.tax_inclusive = data.tax_inclusive_switch;
        $(".preloader").removeClass("ng-show").addClass("ng-hide");
        setCheckSum(setCheckSumFormate(JSON.stringify(data.tax_inclusive_switch),TAX_INCLUSIVE)).
            then(function(data){
              console.log("tax_inclusive_switch saved in local db "+data);
            }).catch(function(error){
              console.log("tax_inclusive_switch saving issue in local db "+error);
            });
      }).error(function() {
          getChecsumByName(TAX_INCLUSIVE).
            then(function(result){
              $scope.$apply(function(){
                console.log("tax_inclusive_switch get data from  local db "+result);
                self.tax_inclusive = JSON.parse(result.checksum);
                $(".preloader").removeClass("ng-show").addClass("ng-hide");
              });
            }).catch(function(error){
              console.log("tax_inclusive_switch issue getting data from local db "+error);
              $(".preloader").removeClass("ng-show").addClass("ng-hide");
            });

    });
      self.check_sku = check_sku;
      self.checked_sku = false;
      function check_sku(sku_code) {
        if(sku_code.includes('"')){
          var check_box = $("input[name='selected_sku'][value='"+sku_code+"']");
        } else {
          var check_box = $('input[name="selected_sku"][value="'+sku_code+'"]');
        }
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
                    angular.forEach(self.skus, function(value, index) {
                      self.changeQuantity(value);
                    });
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
        getOflfineSkuContent();
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
      if(sku_code.includes('"')){
        var check_box = $("input[name='selected_sku'][value='"+sku_code+"']");
      } else {
        var check_box = $('input[name="selected_sku"][value="'+sku_code+'"]');
      }
      if(check_box.prop("checked")) {
        check_box.prop("checked", false);
      } else {
        check_box.prop("checked", true);
      }
    }

     //style based SKU search
     self.change_style_switch = change_style_switch;
     function change_style_switch(style_search){
        if(style_search){
           console.log("style search enabled");
           self.qty_switch = true;
        } else {
          self.qty_switch = false;
        }
     }

     //change qty for style based sku
     self.change_style_qty = change_style_qty;
     function change_style_qty(sku_code, qty) {
        self.tot_style_qty = 0;
        self.tot_style_amount = 0;
        for (var item in self.style_based_sku_data){
            if(self.style_based_sku_data[item]["SKUCode"] === sku_code){
                self.style_based_sku_data[item]["quantity"] = qty;
                self.style_based_sku_data[item]["sku_code"] = sku_code;
                console.log(self.style_based_sku_data[item]);
            }
            if(!self.style_based_sku_data[item]["quantity"]) self.style_based_sku_data[item]["quantity"] = 0;
            self.tot_style_qty += parseFloat(self.style_based_sku_data[item]["quantity"]);
            console.log(parseInt(self.style_based_sku_data[item]["quantity"]) * self.style_based_sku_data[item]["price"]);
            self.tot_style_amount += (parseInt(self.style_based_sku_data[item]["quantity"]) * self.style_based_sku_data[item]["price"]);
        }
    }
    //style sku confirm
    self.style_confirm = style_confirm;
    function style_confirm(){
        for(var item in self.style_based_sku_data){
            if(self.style_based_sku_data[item]["quantity"] > 0){
                update_search_results([self.style_based_sku_data[item]], self.style_based_sku_data[item]["SKUCode"]);
                changeQuantity(self.style_based_sku_data[item]);
            }
        }
        $('#styleModal').modal("hide");
        $("input[type='search'][placeholder='Enter SKUCode/ProductName'").val("").focus();
    }
    /*$rootScope.$on("CallParentMethod", function(){
      $scope.parentmethod();
    });

    $scope.parentmethod = function() {
      cal_total();
    }*/

    $scope.$on('empty', function() {
      cal_total();
    })

      //calculate total items
      self.cal_total = cal_total;
      function cal_total(){
        urlService.current_order.summary.total_amount = 0;
        urlService.current_order.summary.total_quantity = 0;
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
          if (!self.tax_inclusive) {
            self.skus[i].price = parseFloat((self.skus[i].quantity * self.skus[i].unit_price).toFixed(2));
            urlService.current_order.summary.total_amount += self.skus[i].price;
            urlService.current_order.summary.subtotal += self.skus[i].price;
            var total_tax_percent =  self.skus[i].sgst_percent + self.skus[i].cgst_percent + self.skus[i].igst_percent + self.skus[i].utgst_percent
            var unit_price = self.skus[i].price;
            self.skus[i].sgst = (unit_price * self.skus[i].sgst_percent)/100
            self.skus[i].cgst = (unit_price * self.skus[i].cgst_percent)/100
            self.skus[i].igst = (unit_price * self.skus[i].igst_percent)/100
            self.skus[i].utgst = (unit_price * self.skus[i].utgst_percent)/100
            urlService.current_order.summary.sgst += self.skus[i].sgst;
            urlService.current_order.summary.cgst += self.skus[i].cgst;
            urlService.current_order.summary.igst += self.skus[i].igst;
            urlService.current_order.summary.utgst += self.skus[i].utgst;
          } else {
            var total_tax_percent =  self.skus[i].sgst_percent + self.skus[i].cgst_percent + self.skus[i].igst_percent + self.skus[i].utgst_percent
            var unit_price = (self.skus[i].selling_price / ((total_tax_percent + 100)/100)) * self.skus[i].quantity;
            self.skus[i].sgst = (unit_price * self.skus[i].sgst_percent)/100
            self.skus[i].cgst = (unit_price * self.skus[i].cgst_percent)/100
            self.skus[i].igst = (unit_price * self.skus[i].igst_percent)/100
            self.skus[i].utgst = (unit_price * self.skus[i].utgst_percent)/100
            urlService.current_order.summary.sgst += self.skus[i].sgst;
            urlService.current_order.summary.cgst += self.skus[i].cgst;
            urlService.current_order.summary.igst += self.skus[i].igst;
            urlService.current_order.summary.utgst += self.skus[i].utgst;
            self.skus[i].price = parseFloat((unit_price).toFixed(2));
            urlService.current_order.summary.total_amount += self.skus[i].price;
            urlService.current_order.summary.subtotal += self.skus[i].price;
          }
          urlService.current_order.summary.total_quantity += self.skus[i].quantity;
          var discount = (((self.skus[i].selling_price * self.skus[i].quantity) * self.skus[i].discount)/100);
          discount = (urlService.current_order.summary.total_discount/self.skus.length);
          var agg = (self.skus[i].price + (self.skus[i].cgst*self.skus[i].quantity) + (self.skus[i].sgst*self.skus[i].quantity));
          var tax_amt = agg - (self.skus[i].cgst_percent *(agg/100)) - (self.skus[i].sgst_percent *(agg/100)) - discount;
          if(Object.keys(urlService.current_order.summary.gst_based).includes(self.skus[i].cgst_percent.toString())) {
              if (self.tax_inclusive) {
                urlService.current_order.summary.gst_based[self.skus[i].cgst_percent]["cgst"] += (self.skus[i].cgst_percent * (agg/100));
                urlService.current_order.summary.gst_based[self.skus[i].cgst_percent]["sgst"] += (self.skus[i].sgst_percent * (agg/100));
              }
              urlService.current_order.summary.gst_based[self.skus[i].cgst_percent]["taxable_amt"] += tax_amt;
          } else {
              urlService.current_order.summary.gst_based[self.skus[i].cgst_percent] =
                            {"taxable_amt": tax_amt,
                             "cgst_percent" : self.skus[i].cgst_percent,
                             "sgst_percent" : self.skus[i].sgst_percent,
                             "cgst": (self.skus[i].cgst_percent *(agg/100)),
                             "sgst": (self.skus[i].sgst_percent *(agg/100))
                            }
          }
          urlService.current_order.summary.cgst = Math.abs(urlService.current_order.summary.cgst);
          urlService.current_order.summary.sgst = Math.abs(urlService.current_order.summary.sgst);
      if (self.skus[i].return_status === "true" ) {
          urlService.current_order.summary.total_discount += 0;
          urlService.current_order.summary.total_returned += -self.skus[i].price;
          }
      else

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
        if (urlService.current_order.customer_data.Number  && urlService.current_order.customer_data.FirstName) {
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
                urlService.current_order.summary.order_id = 0;
                getCurrentOrderID().then(function(data){
                     urlService.current_order.summary.order_id = data;
                }).catch(function(error){
                    return 0;
                });
                if (self.tax_inclusive) {
                  for (var z=0; z<self.skus.length; z++) {
                    self.skus[z].unit_price = self.skus[z].price/self.skus[z].quantity;
                    self.skus[z].price = self.skus[z].sgst + self.skus[z].cgst + self.skus[z].igst + self.skus[z].price + self.skus[z].utgst - self.skus[z].discount
                  }
                }
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
                urlService.current_order.summary.order_id = 0;
                getCurrentOrderID().then(function(data){
                    urlService.current_order.summary.order_id = data;
                }).catch(function(error){
                    return 0;
                });
                if (self.tax_inclusive) {
                  for (var z=0; z<self.skus.length; z++) {
                    self.skus[z].unit_price = self.skus[z].price/self.skus[z].quantity;
                    self.skus[z].price = self.skus[z].sgst + self.skus[z].cgst + self.skus[z].igst + self.skus[z].price + self.skus[z].utgst - self.skus[z].discount
                  }
                }
                self.customer_order(urlService.current_order);
            } else {
                self.submit_enable = false;
            }
        }
      }
      else{
          urlService.show_toast("Please Fill the Customer Number and Customer Name");
      }
      }

      //print order
      self.print_order = print_order;
      function print_order(data,user) {

        var date = new Date().toDateString();

        if (data.summary.issue_type == 'Delivery Challan') {
          if(self.send_email)
          {
            var data_dict = {}
            data_dict['data'] = urlService.current_order;
            data_dict ['user'] = urlService.userData;
            data_dict ['date'] = date;
            data_dict ['print'] = '';
            data_dict ['print_type'] = '';

         $http.post( urlService.mainUrl+'rest_api/pos_send_mail/',data_dict).
          then(function(data) {

          })
        }
        else{
           printer.print('/app/views/print.html', {'data': urlService.current_order, 'user':urlService.userData, 'print': '',
                        'date': date, 'print_type': ''});
          }
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
                                    "customer_extra": {},
                                    "sku_data" : [],
                                    "payment_mode":"",
                                    "card_name":'',
                                    "reference_number":'',
                                    "summary":{"total_quantity": 0 , "total_amount": 0, "total_discount": 0, "subtotal": 0, "VAT": 0,
                                    "issue_type": self.issue_selected, "order_id": 0, "nw_status": "online", 'invoice_number': '',
                                    "order_date":'', 'staff_member': urlService.default_staff_member},
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
        var temp_date=date_order.getDate() +"-"+(date_order.getMonth()+1)+"-"+date_order.getFullYear().toString();
        urlService.current_order.summary.order_date=temp_date;
        //change the status for preorder0
        if(data.summary.issue_type=="Pre Order"){
            data.status="1";
        }else{
            data.status="0";
        }

              data.summary.nw_status = ONLINE;
              var order_data=Object.assign({},data);
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
              if(data.order_ids[0]!="return"){
                data=data.order_ids[0]+1;
                setCheckSum(setOrderID(data)).
                  then(function(data){
                    console.log("order id updated");
                }).catch(function(error){
                    console.log("order id updated error "+error);
                });
                reduceSKUQty(order_data);
              }
          }
            clear_fields();
          },function(error){

            //change the network status
            order_data.summary.nw_status = OFFLINE;
            $rootScope.sync_status = true;
            $rootScope.$broadcast('change_sync_status');

            setSynOrdersData(urlService.userData.parent_id,order_data,self.qty_switch).
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
                       urlService.show_toast("order creation error "+error);
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
                                      "order_date":'', 'staff_member': urlService.default_staff_member},
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
                  self.skus[j].quantity = parseFloat(self.skus[j].quantity) + quantity;
                  self.skus[j].price = self.skus[j].quantity * self.skus[j].unit_price;
                  self.repeated_data = true;
                  self.skus[j].return_status = self.return_switch.toString();
                  break;
                }
              }
              if (!self.repeated_data) {

                if (!self.qty_switch && !self.return_switch && self.issue_selected === "Delivery Challan" && filter_data[i].stock_quantity == 0) {
                  alert("Given SKU stock is empty.");
                  $('input[name="selected_sku"][value="'+filter_data[0]["SKUCode"]+'"]').prop("checked", false);
                  break;
                } else {

                  //var quantity = (filter_data[i].stock_quantity > 0) ? 1: 0;
                  //Change the quantity to 1
                  var quantity = 1;
                  self.selected_skus.push(filter_data[0]["SKUCode"]);
                  if(filter_data[0]['SKUCode'].includes('"')){
                    $("input[name='selected_sku'][value='"+filter_data[0]['SKUCode']+"']").prop("checked", true);
                  } else {
                    $('input[name="selected_sku"][value="'+filter_data[0]["SKUCode"]+'"]').prop("checked", true);
                  }

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

      function get_product_data(key, style_switch) {

          if(key.length>1){
              var deferred = $q.defer();
              $http.get(urlService.mainUrl+'rest_api/search_product_data/?user='+urlService.userData.parent_id+'&key='+key
                                          + '&style_search=' + style_switch)
                .then( function(data) {
                  if(self.style_switch){
                    self.style_based_sku_data = data.data;
                    data = [];
                    self.style_qtys = {};
                    self.tot_style_qty = 0;
                    self.tot_style_amount = 0;
                    $('#styleModal').modal('show');
                  } else {
                    data=data.data;
                  }
                  if(data.message === "invalid user") {
                    $window.location.reload();
                 } else {
                  console.log("online");
                  self.repos = data;
                  self.repos.map( function (repo) {
                    repo.value = repo.search.toLowerCase();
                    return repo;
                    });

                 if(data.length === 1)
                    update_search_results(data, data[0].SKUCode);

                 }
                 deferred.resolve(querySearch (key));
                 deferred.promise.then(function(data){
                  angular.forEach(self.skus, function(value, index) {
                    self.changeQuantity(value);
                  });
                 });

                },function(error){
                  console.log("offline");
                   getData(key).then(function(data){
                      self.repos = data;
                      //deferred.resolve(data);
                      self.repos.map( function (repo) {
                        repo.value = repo.search.toLowerCase();
                        return repo;
                        });

                      if(data.length === 1)
                        update_search_results(data, data[0].SKUCode);

                    }).then(function(){
                      deferred.resolve(querySearch (key));
                      deferred.promise.then(function(data){
                        angular.forEach(self.skus, function(value, index) {
                          self.changeQuantity(value);
                        });
                      });
                    });

                }).then(function() {
                  /*deferred.resolve(querySearch (key));
                  deferred.promise.then(function(data){
                    angular.forEach(self.skus, function(value, index) {
                      self.changeQuantity(value);
                    });
                  });*/
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
              var indx = self.selected_skus.indexOf(item.sku_code);
              self.selected_skus.splice(indx, 1);
              if(item.sku_code.includes('"')){
                $("input[name='selected_sku'][value='"+item.sku_code+"']").prop("checked", false);
              } else {
                $('input[name="selected_sku"][value="'+item.sku_code+'"]').prop("checked", false);
              }

            } else {

              self.skus[i].quantity = parseFloat(item.quantity);
              self.skus[i].discount = (item.discount) ? parseFloat(item.discount) : 0;
              self.skus[i].unit_price = (item.selling_price - ((item.selling_price/100)*item.discount));
            }
            break;
          }
        }
        cal_total();
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
                } else {
                  item.selling_price = item.price;
                  self.skus[i].quantity = parseFloat(item.quantity);
                  self.skus[i].discount = (item.discount && self.skus[i].return_status==='false') ? parseFloat(item.discount) : 0;
                  self.skus[i].sgst = item.price * self.skus[i]['sgst_percent'] / 100;
                  self.skus[i].cgst = item.price * self.skus[i]['cgst_percent'] / 100;
                  self.skus[i].igst = item.price * self.skus[i]['igst_percent'] / 100;
                  self.skus[i].utgst= item.price * self.skus[i]['utgst_percent'] / 100;
                  urlService.current_order.sku_data = self.skus;
                  self.skus[i].unit_price = (item.selling_price - ((item.selling_price/100)*item.discount));
                  if(self.tax_inclusive) {
                    self.skus[i].unit_price = self.skus[i].unit_price - self.skus[i].cgst - self.skus[i].sgst - self.skus[i].igst;
                  }
                }
                break;
              }
            }
        }
        cal_total();
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
