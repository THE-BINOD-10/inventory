;(function (angular) {
  "use strict";

  angular.module("money", [])
         .component("money", {

           "templateUrl": "/app/cal_money/money.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData",
  function ($http, $scope, urlService, manageData) {

    var self = this;
    self.given = urlService.current_order.summary.total_amount;
    self.returnMoney = 0;
    self.cal_retun_money = cal_retun_money;
    function cal_retun_money(money) {

      if (urlService.current_order.summary.total_amount > 0){
        self.returnMoney = money - urlService.current_order.summary.total_amount;
      };
    };

    $scope.$on('handleBroadcast', function() {

      self.returnMoney = 0;
      self.given = 0;
    })
  }]
 });
}(window.angular));
