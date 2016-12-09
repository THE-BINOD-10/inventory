'use strict';

function signupCtrl($rootScope ,$scope, $state, $http, Auth, AUTH_EVENTS, Service) {

  $scope.readonly = false;
  var location = window.location.hash;
  if(location.search("hashcode"))  {

    get_user_data(location);
  } else {
    $state.go("user.signin")
  }

  $scope.form_data = {full_name:"", email: "", company: "", phone: ""}
  function get_user_data(data) {
    var code = data.split("=")[1];

    if(code && (data.split("=").length == 2)) {

      Service.apiCall("get_trial_user_data/?hash_code="+code).then(function(data){
        if(data.message) {
          if (data.data.message == "success") {
            $scope.readonly = true;
            angular.copy(data.data.data, $scope.form_data);
          } else {
            $state.go("user.signin");
          }
        } else {
          $state.go("user.signin");
        }
      });
    } else {
      $state.go("user.signin");
    } 
  }
  /*
  $scope.username = "";
  $scope.password = "";
  $scope.submit = function () {

     $scope.process = true;
     var data = $.param({
                login_id: this.username,
                password: this.password
            });
      Auth.login(data).then(function (data) {
                  console.log(data);
                if (data.message == "Fail") {
                  $scope.process = false;
                  $scope.username = "";
                  $scope.password = "";
                } else { 
                  $state.go('app.dashboard');
                  $rootScope.$broadcast(AUTH_EVENTS.loginSuccess);
                }
                });
  }
  */

  $scope.signup = function(data) {

    var password = $("input[type='password']").val();
    if(data.$valid && password.length > 7) {
      $scope.form_data["password"] = password;
      Service.apiCall("create_user/", 'POST', $scope.form_data).then(function(data){
        if(data.message) {
          if(data.data == "success") {
            $state.go("app.Register")
          } else {
            $state.go("app.Register")
          }
        }
      })
    }
  }

}

angular
  .module('urbanApp')
  .controller('signupCtrl', ['$rootScope' ,'$scope', '$state', '$http', 'Auth', 'AUTH_EVENTS', 'Service', signupCtrl]);
