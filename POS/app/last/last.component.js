;(function (angular) {
  "use strict";

  angular.module("last", [])
         .component("last", {

           "templateUrl": "/app/last/last.template.html",
           "controller"  : ["$scope", "urlService", "manageData",
    function ($scope, urlService, manageData) {
      var self = this;
      self.last_five = urlService.done_orders;
    }]
  })
}(window.angular));
