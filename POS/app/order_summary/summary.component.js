;(function (angular) {
  "use strict";

  angular.module("summary", [])
         .component("summary", {

           "templateUrl": "/app/order_summary/summary.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData", "$state", "$location",
    function ($http, $scope, urlService, manageData, $state, $location) {

      var self = this;
      self.VAT = urlService.VAT;
      self.order = urlService.current_order.summary;

      if (urlService.user_update) {
      $http.get( urlService.mainUrl+'get_pos_user_data/?id='+urlService.userData.parent_id).success(function(data, status, headers, config) {

          if (data.status == "Success"){
            console.log(data);
            urlService.userData = data;
            urlService.VAT = data.VAT;
            self.VAT = data.VAT;
          } else {

            $state.go("login");
          }
        })
      }
      $scope.$on('handleBroadcast', function() {

        self.order = urlService.current_order.summary;
      });

      $scope.$on('change_current_order', function(){

        self.order = urlService.current_order.summary;
      });
    }]
  });
}(window.angular));
