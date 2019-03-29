;(function (angular) {
  "use strict";
  angular.module("paymenttype", [])
         .component("paymenttype", {
           "templateUrl": "/app/payment_type/paymenttype.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData",
  function ($http, $scope, urlService, manageData) {
    var self = this;
    self.paymentTypeInput = [];
    self.show_card = false;
    self.payment_mode = '';
    self.reference_number = '';
    self.card_digits = '';
    urlService.current_order.summary.paymenttype_values = self.paymentTypeInput;
    self.card_name_list = [
      {
          "key": "Master",
          "value": "Master"
      },
      {
          "key": "Visa",
          "value": "Visa"
      },
      {
          "key": "AmericanExpress",
          "value": "AmericanExpress"
      },
      {
          "key": "RuPay",
          "value": "RuPay"
      }
    ]
    self.paymenttypes = [
      {
          "key": "Cash",
          "value": "Cash"
      },
      {
          "key": "Card",
          "value": "Card"
      },
      {
          "key": "Paytm",
          "value": "Paytm"
      },
      {
          "key": "PhonePe",
          "value": "PhonePe"
      },
      {
          "key": "GooglePay",
          "value": "GooglePay"
      }
    ];
    self.paymenttype_value = "cash";
    self.add_payment_type = function() {
      self.payment_mode = "";
      self.card_name = '';
      self.reference_number='';
      self.card_digits = '';
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
    self.remove_null = remove_null;
    function remove_null(name_value, index){
        angular.forEach(self.paymentTypeInput, function (index_value, index) {
            if(!index_value['type_value']){
                index_value['type_value'] = 0;
            }
        })
    }
    self.show_card_value  = function(){
      self.show_card = 'true';
      urlService.current_order.card_name = self.card_name
    }
    self.reference_number_save = function(){
      urlService.current_order.reference_number = self.reference_number;
    }
    self.save_card_value = function (){
      urlService.current_order.reference_number = self.card_digits;
    }
    self.payment_valid = payment_valid;
    function payment_valid (name_value, index) {
      urlService.current_order.summary.paymenttype_values = self.paymentTypeInput;
      urlService.current_order.payment_mode = self.paymentTypeInput[0].type_name;

      var temp = 0;
      angular.forEach(self.paymentTypeInput, function (index_value, index) {
        temp += index_value['type_value'];
      })
      if(temp > (urlService.current_order.summary.total_amount - urlService.current_order.summary.total_discount)) {
        if (self.paymentTypeInput.length == 1) {
          self.paymentTypeInput[0]['type_value'] = urlService.current_order.summary.total_amount
						   - urlService.current_order.summary.total_discount;
        }
        if (self.paymentTypeInput.length == 2) {
          var check = (urlService.current_order.summary.total_amount - urlService.current_order.summary.total_discount)
		      - self.paymentTypeInput[0]['type_value'];
          if (check < 0) {
            self.paymentTypeInput[0]['type_value'] = urlService.current_order.summary.total_amount
						     - urlService.current_order.summary.total_discount;
          }
          self.paymentTypeInput[1]['type_value'] = Math.max(0, check);
          if(urlService.current_order.summary.total_amount == 0) {
            self.paymentTypeInput[0]['type_value'] = 0;
          }
        }
      }
      urlService.current_order.summary.paymenttype_values = self.paymentTypeInput;
    }

    $scope.$on('empty_payment_values', function(){
      self.paymentTypeInput = [];
    })

  }]
 });
}(window.angular));
