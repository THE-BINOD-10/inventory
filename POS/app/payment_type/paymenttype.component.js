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
    
    self.payment_valid = payment_valid;
    function payment_valid (name_value, index) {
      var temp = 0;
      angular.forEach(self.paymentTypeInput, function (index_value, index) {
        temp += index_value['type_value'];
      })
      if(temp > urlService.current_order.summary.total_amount) {
        if (self.paymentTypeInput.length == 1) {
          self.paymentTypeInput[0]['type_value'] = urlService.current_order.summary.total_amount;
        }
        if (self.paymentTypeInput.length == 2) {
          var check = urlService.current_order.summary.total_amount - self.paymentTypeInput[0]['type_value'];
          if (check < 0) {
            self.paymentTypeInput[0]['type_value'] = urlService.current_order.summary.total_amount;
          }
          self.paymentTypeInput[1]['type_value'] = Math.max(0, check);
          if(urlService.current_order.summary.total_amount == 0) {
            self.paymentTypeInput[0]['type_value'] = 0;
          }
        }
      }
    }

    $scope.$on('empty_payment_values', function(){
      self.paymentTypeInput = [];
    })

  }]
 });
}(window.angular));
