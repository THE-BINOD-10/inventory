'use strict';

function sessionCtrl($rootScope ,$scope, $state, $http, Auth, AUTH_EVENTS, Session) {

  $scope.process = false;
  $scope.invalid = false;
  $scope.password_expired = false;

  $scope.username = "";
  $scope.password = "";
  $scope.submit = function () {

     $scope.process = true;
     var data = $.param({
                login_id: this.username,
                password: this.password
            });
      Auth.login(data).then(function (data) {
                if (data.message == "Fail") {
                  $scope.process = false;
                  $scope.username = "";
                  $scope.password = "";
                  $scope.invalid = true;
                  $scope.password_expired = false;
                } else if((["Password Expired", "Account Locked"]).indexOf(data.message)  != -1) {
                  $scope.process = false;
                  $scope.username = "";
                  $scope.password = "";
                  $scope.password_expired = true;
                  $scope.invalid = false;
                  $scope.error_message = data.message;
                } else {
                  console.log(Session);
                  if(Session.roles.permissions["setup_status"])  {

                    $state.go('app.Register');
                  } else {
                    $rootScope.$broadcast(AUTH_EVENTS.loginSuccess);
                  }
                }
                });
  }

  $scope.signup = function() {

    var data = $.param({
         username: this.username,
         email: this.email,
         password: this.password
         });

    Auth.signup(data).then(function () {
        $state.go('user.signin');
          });

  }

}

angular
  .module('urbanApp')
  .controller('sessionCtrl', ['$rootScope' ,'$scope', '$state', '$http', 'Auth', 'AUTH_EVENTS', 'Session', sessionCtrl]);
