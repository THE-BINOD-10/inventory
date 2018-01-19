;(function (angular) {
  "use strict";

  angular.module("paymenttype", [])
         .component("paymenttype", {
           "templateUrl": "/app/payment_type/paymenttype.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData",
  function ($http, $scope, urlService, manageData) {
    var self = this;
    self.paymentTypeInput = [];
    
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
      self.paymentTypeInput.push({ type_name: self.paymenttype_value, type_value: 0 });
      //self.isEmptyMarket = false;
    }

    self.remove_payment_type = function(index) {
      self.paymentTypeInput.splice(index);
    }

  }]
 });
}(window.angular));
