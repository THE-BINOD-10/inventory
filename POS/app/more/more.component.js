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

      function get_order_details(order_id) {

        $(".preloader").removeClass("ng-hide").addClass("ng-show");
        // ajax call to send data to backend
        var data = $.param({
                    data: JSON.stringify({'user':user, 'order_id':order_id})
                   });
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        $http.post( urlService.mainUrl+'rest_api/pre_order_data/', data).success(function(data, status, headers, config) {
        
            $(".preloader").removeClass("ng-show").addClass("ng-hide");
            $(".no_order").removeClass("ng-hide");
            $(".already_delivered").removeClass("ng-hide");
            self.isDisabled = false;
            data.data.status==='0'?$("#delivered_btn").addClass("ng-hide"):$("#delivered_btn").addClass("btn-danger").removeClass("btn-success");
            self.order_details = data;

       }).then(function() {
       });
      }

      self.update_order_status = update_order_status;

      function update_order_status(order_id) {

        debugger;
        if(self.isDisabled === false){
            $(".preloader").removeClass("ng-hide").addClass("ng-show");
            // ajax call to send data to backend
            var data = $.param({
                        data: JSON.stringify({'user':user, 'order_id':order_id})
                       });
            $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
            $http.post( urlService.mainUrl+'rest_api/update_order_status/', data).success(function(data, status, headers, config) {
            
                $(".preloader").removeClass("ng-show").addClass("ng-hide");
                self.isDisabled = true;
                $("#delivered_btn").removeClass("btn-danger").addClass("btn-success");

           }).then(function() {
           });
        }//if
        else {
          self.order_details.data.status = '0';
        }
      }



    }]
  })
}(window.angular));
