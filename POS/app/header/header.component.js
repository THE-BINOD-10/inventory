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
				   showRefresh();
				 
				   if(navigator.onLine){
				 	//sync pos data 
				 	syncPOSTransactionData().then(function(){
				 	  hideRefresh();
				 	}).catch(function(){
				 	  hideRefresh();
				 	});
				   }else{
				 	console.log( "offline");
				 	hideRefresh();
				   }

				};

				function showRefresh(){
				  $(".preloader").removeClass("ng-hide").addClass("ng-show");
				}

				function hideRefresh(){
				  $(".preloader").removeClass("ng-show").addClass("ng-hide");
				  checkStoragePercent().then(function(data){
					if(data){
					  toast_msg("memory usage exceed 70% .please free the space");        
					}else{
					  console.log("memory is not reached 70%");
					}
				  }).catch(function(error){
					  console.log(error);
				  });
				}

				//trigger event for getting data at intiallly.
				$scope.sync();

			  window.addEventListener('load', function(e) {
				if (navigator.onLine) {
				  console.log("online");
				  toast_msg(CONNECTED_NETWORK);
				} else {
				  console.log("offline");
				  toast_msg(NETWORK_ERROR);
				}
			  }, false);

			  window.addEventListener('online', function(e) {
				console.log("And we're back");
				toast_msg(CONNECTED_NETWORK);
			  }, false);

			  window.addEventListener('offline', function(e) {
				console.log("Connection is flaky.");
				toast_msg(NETWORK_ERROR);
			  }, false);

			  function toast_msg(msg){
				 $mdToast.show( $mdToast.simple()
					.textContent(msg)
					.position('top right')
					.hideDelay(3000));
			  }

			  function checkNotificationPermission(){

			   enableNotificaiton().then(function(data){

						if(data==false){
						  toast_msg(NOTIIFICATION_ERROR);
						}

						  checkPersistent().then(function(data){
							  console.log(""+data);
						  }).catch(function(error){
							  console.log(""+error);
						  });
						});
			  }  

			  checkNotificationPermission();

			})

    }]
  })
}(window.angular));
