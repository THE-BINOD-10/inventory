;(function (angular) {
  "use strict";

  angular.module("pageheader", [])
         .component("pageheader", {

           "templateUrl": "/app/header/header.template.html",
           "controller"  : ["$scope", "urlService", "Fullscreen",
    function ($scope, urlService, Fullscreen) {
      var self = this;

                $scope.name = "Test";
                $scope.is_disable = "false";
                $scope.customerUrl = urlService.mainUrl;
                $scope.user_data = urlService.userData;

                // Fullscreen
                $scope.goFullscreen = function () {

                    if (Fullscreen.isEnabled())
                     Fullscreen.cancel();
                    else
                     Fullscreen.all();
                 };

				$scope.isFullScreen = false;

                 $scope.goFullScreenViaWatcher = function() {
                    $scope.isFullScreen = !$scope.isFullScreen;
                 };

                 //Synchronize DB
                 $scope.sync = function () {
                    //$scope.is_disable = "true";
                    $(".preloader").removeClass("ng-hide").addClass("ng-show");
                    debugger; 
                    if(navigator.onLine){
                    //sync pos data 
                    syncPOSTransactionData().then(function(){
                      $(".preloader").removeClass("ng-show").addClass("ng-hide");
                    }).catch(function(){
                      $(".preloader").removeClass("ng-show").addClass("ng-hide");
                    }); 
                    }else{
                    console.log( "offline");
                    $(".preloader").removeClass("ng-show").addClass("ng-hide");
                    }

                };

    }]
  })
}(window.angular));
