;(function (angular) {
  "use strict";

  angular.module("login", [])
         .component("login", {

           "templateUrl": "/app/login/login.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData", "$state", "$location",
    function ($http, $scope, urlService, manageData, $state, $location) {

      var self = this;
      self.username;
      self.password;

      self.login = login;
      function login(username, password) {

        var data = $.param({
                user_id : username,
                user_name : password
            });
        $http.get( urlService.mainUrl+'validate_sales_person/?user_id='+username+'&user_name='+password).success(function(data, status, headers, config) {

          if (data.status == "Success"){
            $state.go("home");
            console.log(data);
            urlService.user_update = false;
            urlService.userData = data;
            urlService.VAT = data.VAT;
            console.log("success");
          }
          else {

            self.username = "";
            self.password = "";
            $state.go("login");
          }
        })
        .error( function(data) {

          console.log("fail");
        });
      }
    }
  ]});
}(window.angular));
