;(function (angular) {
  "use strict";

  angular.module("pending", [])
         .component("pending", {

           "templateUrl": "/app/pending/pending.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData", "$state", "$location",
    function ($http, $scope, urlService, manageData, $state, $location) {

      var self = this;
      self.pending_data = urlService.hold_data;

      self.unhold_order = unhold_order;
      function unhold_order(order) {

        if (order.status != 1) {
          var save_order = urlService.current_order;
          urlService.current_order = order;
          for (var i=0; i < urlService.hold_data.length; i++) {

            if ( order.customer_data.Number == urlService.hold_data[i].customer_data.Number && order.$$hashKey == urlService.hold_data[i].$$hashKey) {
  
              urlService.hold_data.splice(i, 1);
              if (save_order.summary.total_amount > 0) {
                urlService.hold_data.push(save_order);
              }
              break;
            }
          }
        }
        urlService.prepForBroadcast("change Current Order");
      };
    }]
  });
}(window.angular));
