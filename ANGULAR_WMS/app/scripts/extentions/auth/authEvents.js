;(function (angular) {
  "use strict";

  angular.module("auth").constant("AUTH_EVENTS", {

    "loginSuccess" : "auth-login-success",
    "logoutSuccess": "auth-logout-success",
    "unAuthorized" : "auth-unauthorized"
  });

}(window.angular));
