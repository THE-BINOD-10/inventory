'use strict';

function createAccountCtrl($rootScope ,$scope, $state, $http, Auth, AUTH_EVENTS, Service, Session, Analytics) {

  $scope.signup = function(data) {

    if( data.$valid ) {

      var send = $("form:visible").serializeArray()
      Service.apiCall("book_trial/", 'POST', send).then(function(data){
        if(data.message) {

          console.log(data)
          if(data.data == 'Added Successfully') {

            Analytics.trackEvent('go-stockone 30 day trial', 'submit', 'go-stockone Free Trial', $scope.form_data.email);

            //$scope.valid_msg = 'Thank You! Please check your email to activate your subscription.';
            $scope.valid = true;
            $scope.invalid = false;
            window.location.href = 'http://stockone.in/index.php/thanks-30-day-trial';
          } else {

            $scope.invalid_msg = data.data;
            $scope.invalid = true;
          }
        } else {

          $scope.invalid_msg = 'Oops! Some issues are there. Try again later';
          $scope.invalid = true;
        }
      })
    }
  }

}

angular
  .module('urbanApp')
  .controller('createAccountCtrl', ['$rootScope' ,'$scope', '$state', '$http', 'Auth', 'AUTH_EVENTS', 'Service', 'Session', 'Analytics', createAccountCtrl]);
