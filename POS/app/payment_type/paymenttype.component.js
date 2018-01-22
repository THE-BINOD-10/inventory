;(function (angular) {
  "use strict";
  angular.module("paymenttype", [])
         .component("paymenttype", {
           "templateUrl": "/app/payment_type/paymenttype.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData",
  function ($http, $scope, urlService, manageData) {
    var self = this;
    self.paymentTypeInput = [];
    urlService.current_order.summary.paymenttype_values = self.paymentTypeInput;
    self.paymenttypes = [
      {
          "key": "cash",
          "value": "Cash"
      },
      {
          "key": "card",
          "value": "Card"
      }
    ];
    self.paymenttype_value = "cash";
    self.add_payment_type = function() {
      var add = 1;
      angular.forEach(self.paymentTypeInput, function (index_value, index) {
        if (self.paymenttype_value == index_value['type_name']) {
          add = 0;
          return false;
        }
      })
      if (add) {
        self.paymentTypeInput.push({ 'type_name' : self.paymenttype_value , 'type_value' : 0 });
      }
    }
    self.remove_payment_type = function(index) {
      self.paymentTypeInput.splice(index,1);
    }
  }]
 });
}(window.angular));
