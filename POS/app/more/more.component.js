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

      function get_order_details(order_id, mobile, customer_name, request_from) {

        self.request_from = request_from;
        $(".preloader").removeClass("ng-hide").addClass("ng-show");
        // ajax call to send data to backend
        var data = $.param({
                    data: JSON.stringify({'user':user, 'order_id':order_id, 'mobile': mobile, 'customer_name': customer_name,
                                          'request_from': request_from})
                   });
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        $http.post( urlService.mainUrl+'rest_api/pre_order_data/', data).success(function(data, status, headers, config) {

            var key = Object.keys(data.data)[0];
            key ? (request_from !== "return" ? self.order_details = data.data[key]: self.order_details = data.data) : self.order_details = {'status':'empty'};
            self.isDisabled = false;

            $(".preloader").removeClass("ng-show").addClass("ng-hide");
            $(".no_order").removeClass("ng-hide");
            $(".already_delivered").removeClass("ng-hide");
            self.order_details.status==='0'?$("#delivered_btn").addClass("ng-hide"):$("#delivered_btn").addClass("btn-danger").removeClass("btn-success");

       }).then(function() {
       });
      }

      self.update_order_status = update_order_status;

      function update_order_status(order_id) {

        if(self.isDisabled === false){
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
        }//if
        else {
          self.order_details.status = '0';
        }
      }



    }]
  })
}(window.angular));
