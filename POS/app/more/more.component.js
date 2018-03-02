;(function (angular) {

	"use strict";

	angular.module("more", [])
	.component("more", {

		"templateUrl": "/app/more/more.template.html",
    "controller"  : ["$http", "$scope", "urlService", "$rootScope", "$location", "$window", "printer",
		function ($http, $scope, urlService, $rootScope, $location, $window, printer) {
			var self = this;
			self.isDisabled = false;

			self.get_order_details = get_order_details;
			var user = urlService.userData.parent_id;

			get_order_details('','','','initial_preorder');
			function get_order_details(order_id, mobile, customer_name, request_from) {

				self.request_from = request_from;
				$(".preloader").removeClass("ng-hide").addClass("ng-show");

				console.log("online");
					// ajax call to send data to backend
					var data = $.param({
						data: JSON.stringify({'user':user, 'order_id':order_id, 'mobile': mobile, 'customer_name': customer_name,
							'request_from': request_from})
					});
					$http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";

					$http.post( urlService.mainUrl+'rest_api/pre_order_data/', data).
					then(function(data) {
						data=data.data;
						if(data.message === "invalid user") {
                $window.location.href = urlService.stockoneUrl;
            } else {
						onLinePreorderData(data);
						}
					},function(error){
						console.log("offline");
						getPreOrderDetails_Check_Off_Delivered(urlService.userData.parent_id,order_id).then(function(data){
							offLinePreorderData(data);
						});
					});

					//onLine getpreordersData
					function onLinePreorderData(data){
							var key = Object.keys(data.data);
							if(key.length > 0) {
							  self.order_details = data.data;
							  self.filtered_order_details = data.data;
	            } else {
	              self.order_details = {'status':'empty'};
	            }
							self.isDisabled = false;
					
					}

				//offline getPreorderData
				function offLinePreorderData(data){
					$scope.$apply(function(){
					onLinePreorderData(data);
					//auto sync when network available
					syncPOSData(false).then(function(data){
						 // $rootScope.sync_status = false;
							//$rootScope.$broadcast('change_sync_status');
						}); 
					});       
				}

			//click one preorder id to show details
			self.select_order = select_order;

			function select_order(order_id) {

				self.selected_order = self.filtered_order_details[order_id];
				self.selected_order.status=self.selected_order.status.toString();

				self.isDisabled = false;
				self.selected_order.status==="1" ? $(".already_delivered").removeClass("ng-show").addClass("ng-hide")
				: $(".already_delivered").removeClass("ng-hide").addClass("ng-show"),
				self.success_msg="Delivered Successfully";
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
				}else {
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
				}else {
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
								if(before_customer_filter[item][custo]['Name']!=undefined &&before_customer_filter[item][custo]['Name'].toUpperCase().indexOf(customer_name)>=0){
									customer_filter[item] = before_customer_filter[item];
								}
							}
						})
					})
					self.filtered_order_details = customer_filter;
				}else {
					self.filtered_order_details = before_customer_filter;
				}//end customer filter


			}//end filter

			//update preorder status and reduce quantity
			self.update_order_status = update_order_status;

			function update_order_status(order_id, delete_order =false) {

				if(self.isDisabled === false){

					var del = "false";
					if(delete_order) {
						del = confirm("Sure to delete the order permanantly ?").toString();
						if(del==='false') return;
					}

					$(".preloader").removeClass("ng-hide").addClass("ng-show");
							// ajax call to send data to backend
							var data = $.param({
								data: JSON.stringify({'user':user, 'order_id':order_id, 'delete_order':del})
							});
							$http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
							$http.post( urlService.mainUrl+'rest_api/update_order_status/', data)
							.then(function(data) {
								data=data.data;
								if(data.message === "invalid user") {
                    $window.location.href = urlService.stockoneUrl;
                } else {
                        onLineOrderStatusData(order_id,data,del);
                       }
                    },function(error){

                        console.log("offline");
                        $rootScope.sync_status = true;
                        $rootScope.$broadcast('change_sync_status');
                        setPreOrderStatus(""+order_id,"0",del).
                        then(function(data){

                            offLineOrderStatusData(order_id,data,del);
                        }).catch(function(error){
                            $scope.$apply(function() {
                                $(".preloader").removeClass("ng-show").addClass("ng-hide");
                                alert(error);
                            });

                        });


                    });

				}//if
				else {
					self.order_details.status = '0';
				}
			}	

				//onLine preorder status update
				function onLineOrderStatusData(order_id,data,del){
						$(".preloader").removeClass("ng-show").addClass("ng-hide");     
						if(data.message==="Error"){
							alert("Please update Stock Quantity and try again");
						}
						else {
						  if(data.message === "Delivered Successfully !") {
                            printer.print('/app/views/print.html', {'data': data.data.data,
                                                                    'user':urlService.userData,
                                                                    'print_type': '',
                                                                    'date':data.data.data.order_date});
                          }
							self.isDisabled = true;
							self.success_msg = data.message;
							//if(del==='true') $("."+order_id).parent('div').addClass("ng-hide");
                            $("."+order_id).parent('div').addClass("ng-hide");
							$(".already_delivered").removeClass("ng-hide").addClass("ng-show");
							self.selected_order.status = '0';
						}
				}

				//offline preorder status update
				function offLineOrderStatusData(order_id,data,del){
					$scope.$apply(function() {

						onLineOrderStatusData(order_id,data,del)

						//auto sync when network available
						syncPOSData(false).then(function(data){

						 // $rootScope.sync_status = false;
							//$rootScope.$broadcast('change_sync_status');
						});
					});
				}

			}
		}]
	})

}(window.angular));
