;(function (angular) {
  "use strict";

  angular.module("order", [])
         .component("order", {

           "templateUrl": "/app/order/order.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData", "printer",
  function ($http, $scope, urlService, manageData, printer) {

    var self = this;
    self.given = urlService.current_order.summary.total_amount;
    self.order_number = "";
    self.print_order = print_order;
    function print_order(order) {
      if(order.length <= 0) {
        return;
      }
      $http.get( urlService.mainUrl+'/rest_api/print_order_data/?user='+urlService.userData.parent_id+'&order_id='+order).success(function(data, status, headers, config) {
            console.log(data);
            if(data.status == "success") {
              printer.print('/app/views/print.html', {'data': data.data, 'user':urlService.userData, 'print': 'Reprint', 'date':data.data.order_date}); 
            }
        }) 
    };

  }]
 });
}(window.angular));
