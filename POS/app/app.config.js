;(function (angular) {
  "use strict";
  var app=angular.module('App', ['ui.router']);
  app.config(function($stateProvider, $urlRouterProvider){
      // For any unmatched url, send to /route1
      $urlRouterProvider.otherwise("/login");

      $stateProvider
        .state('login', {
            url: '/login',
            template: '<login></login>',
        })
        .state('home', {
            url: '/home',
            templateUrl: 'app/views/home.html'
        })
  }).
  run(["$rootScope", "$state", "$location", "urlService",
    function ($rootScope, $state, $location, urlService) {

      if (typeof(urlService.userData.user_name) != "undefined") {

        $state.go("home");
      } else {

        if (typeof($location.$$search.user_id) != "undefined") {

          urlService.userData = {'user_id':$location.$$search.user_id, 'user_name':$location.$$search.user_name}
        } else {

          $state.go("login")
        }
      }
      $rootScope.$on("$stateChangeStart", function (event) {
        console.log("from wms");
      })
    }
  ])
}(window.angular));
