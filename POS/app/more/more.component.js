;(function (angular) {
  "use strict";

  angular.module("more", [])
         .component("more", {

           "templateUrl": "/app/more/more.template.html",
           "controller"  : ["$http", "$scope", "urlService",
    function ($http, $scope, urlService) {
      var self = this;
      self.isDisabled = false;

      self.get_order_details = get_order_details;
      var user = urlService.userData.parent_id;

      get_order_details('','','','initial_preorder');
      function get_order_details(order_id, mobile, customer_name, request_from) {

        self.request_from = request_from;
        $(".preloader").removeClass("ng-hide").addClass("ng-show");


        if(navigator.onLine){
          
          console.log("online");
          // ajax call to send data to backend
        var data = $.param({
                    data: JSON.stringify({'user':user, 'order_id':order_id, 'mobile': mobile, 'customer_name': customer_name,
                                          'request_from': request_from})
                   });
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        $http.post( urlService.mainUrl+'rest_api/pre_order_data/', data).success(function(data, status, headers, config) {

            var key = Object.keys(data.data)[0];
            //key ? (request_from !== "return" ? self.order_details = data.data[key]: self.order_details = data.data) : self.order_details = {'status':'empty'};
            key ? (self.order_details = data.data, self.filtered_order_details = data.data) : self.order_details = {'status':'empty'};
            self.isDisabled = false;

            //$(".preloader").removeClass("ng-show").addClass("ng-hide");
            //$(".no_order").removeClass("ng-hide");
            //$(".already_delivered").removeClass("ng-hide");
            //self.order_details.status.toString()==='0'?$("#delivered_btn").addClass("ng-hide"):$("#delivered_btn").addClass("btn-danger").removeClass("btn-success").removeClass("ng-hide");

       }).then(function() {
       });

        }else{
          console.log("offline");
          getPreOrderDetails_Check_Off_Delivered(order_id).then(function(result){
  
              if(Object.keys(result).length>0){
                self.order_details=result;
              }else{
              self.order_details = {'status':'empty'};
              }
              self.isDisabled = false;

            $scope.$apply(function() { 

              $(".preloader").removeClass("ng-show").addClass("ng-hide");
              $(".no_order").removeClass("ng-hide");
              $(".already_delivered").removeClass("ng-hide");
              //self.order_details.status = self.order_details.status.toString();
              self.order_details.status==='0'?$("#delivered_btn").addClass("ng-hide"):$("#delivered_btn").addClass("btn-danger").removeClass("btn-success").removeClass("ng-hide");
              });

          });
        }
      }

      //click one preorder id to show details
      self.select_order = select_order;

      function select_order(order_id) {

        self.selected_order = self.filtered_order_details[order_id];
        $('#orderModal').modal('show');
      }
      //pre order filters
      self.pre_order_filter = pre_order_filter;

      function pre_order_filter(order_id, customer_name, sku_id) {

		var before_order_filter = self.order_details;
      	//if order id
		if(order_id) {

			order_id = order_id.toUpperCase();
			var id_filtered = {};
			Object.keys(before_order_filter).forEach(function(item) {

				if(item.toString().toUpperCase().indexOf(order_id)>=0) {
					console.log(item);
					id_filtered[item] = before_order_filter[item];
				}

			})
			self.filtered_order_details = id_filtered;
			debugger;
			//self.filtered_order_details = [self.order_details[order_id]];
		}
		else {
			self.filtered_order_details = before_order_filter;
		}//end order id filter

		//if sku_id
		var before_sku_filter = self.filtered_order_details;
		if(sku_id) {
			sku_id = sku_id.toUpperCase();
			var sku_filtered = {};
			Object.keys(before_sku_filter).forEach(function(item){

				Object.keys(before_sku_filter[item]).forEach(function(sku){
					if (sku === "sku_data") {
						Object.keys(before_sku_filter[item][sku]).forEach(function(each_sku){
							if(before_sku_filter[item][sku][each_sku]['sku_code'].toUpperCase().indexOf(sku_id)>=0){
								sku_filtered[item] = before_sku_filter[item];
							}
					})
				}
			})
		})
		self.filtered_order_details = sku_filtered;
		}
		else {
			self.filtered_order_details = before_sku_filter;
		}//end sku id filter

		//if customer_name
		var before_customer_filter = self.filtered_order_details;
		if(customer_name) {

			customer_name = customer_name.toUpperCase();
			var customer_filter = {};
			Object.keys(before_customer_filter).forEach(function(item){

				Object.keys(before_customer_filter[item]).forEach(function(custo){
					if (custo === "customer_data") {
						if(before_customer_filter[item][custo]['Name'].toUpperCase().indexOf(customer_name)>=0){
							customer_filter[item] = before_customer_filter[item];
            			}
        			}
    			})
			})
			self.filtered_order_details = customer_filter;
		}
		else {
			self.filtered_order_details = before_customer_filter;
		}//end customer filter

      }//end filter

      //update preorder status and reduce quantity
      self.update_order_status = update_order_status;

      function update_order_status(order_id) {

        if(self.isDisabled === false){

          if(navigator.onLine){

              $(".preloader").removeClass("ng-hide").addClass("ng-show");
              // ajax call to send data to backend
              var data = $.param({
                          data: JSON.stringify({'user':user, 'order_id':order_id})
                         });
              $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
              $http.post( urlService.mainUrl+'rest_api/update_order_status/', data).success(function(data, status, headers, config) {
   
                  $(".preloader").removeClass("ng-show").addClass("ng-hide");
                  if(data==="Error"){
                      alert("Please update Stock Quantity and try again");
                  } else {
                      self.isDisabled = true;
                      $("#delivered_btn").removeClass("btn-danger").addClass("btn-success");
                  }

             }).then(function() {
             });
          }else{

              console.log("offline");
              setPreOrderStatus(order_id,0).
                            then(function(data){

                                 $scope.$apply(function() {  
                                  $(".preloader").removeClass("ng-show").addClass("ng-hide");
                                  self.isDisabled = true;
                                  $("#delivered_btn").removeClass("btn-danger").addClass("btn-success");
                                });
                            
                            }).catch(function(error){

                                $scope.$apply(function() { 
                                  $(".preloader").removeClass("ng-show").addClass("ng-hide");
                                  alert(error);
                                });

                            });
          }
        }//if
        else {
          self.order_details.status = '0';
        }
      }
    }]
  })
}(window.angular));
