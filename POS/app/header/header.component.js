;(function (angular) {
  "use strict";

  angular.module("pageheader", ["ngMaterial"])
         .component("pageheader", {

           "templateUrl": "/app/header/header.template.html",
           "controller"  : ["$scope","$mdToast", "urlService", "Fullscreen","$rootScope","$window",
    function ($scope,$mdToast, urlService, Fullscreen, $rootScope,$window) {
      var self = this;

      $scope.name = "Test";
      $scope.is_disable = "false";
      $scope.customerUrl = urlService.mainUrl;
      $scope.stockoneUrl = urlService.stockoneUrl;
      $scope.user_data = urlService.userData;
      urlService.returnsView = false;
      $scope.returnsView = urlService.returnsView;
//      $scope.sync_status = $rootScope.sync_status;
//      $scope.sync_msg = "Not Synced !";
//      $scope.$on('change_sync_status', function(){
//        $scope.sync_status = $rootScope.sync_status;
//      })
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
      $scope.returnsViewChange = function() {
        if (urlService.returnsView) {
          urlService.returnsView = false;
          $scope.returnsView = false;
        } else {
          $scope.returnsView = true;
          urlService.returnsView = true;
        }
      };
	  //Synchronize DB
//	  $scope.sync = function () {
//		//$scope.is_disable = "true";
//
//		if(navigator.onLine){
//            //sync pos data
//            navigator.serviceWorker.ready.then(function() {
//            	if(POS_UPDATE_FOUND){
//            		reloadPOSPage();
//            	}else if(POS_ENABLE_SYNC===false){
//	                urlService.show_loading();
//	                syncPOSTransactionData().then(function(){
//	                	//check user info and user id
//	                	checkUserInfo().then(function(data){
//	                		$rootScope.sync_status = false;
//	                    	$rootScope.$broadcast('change_sync_status');
//	                	}).catch(function(error){
//	                		$scope.sync_msg=error;
//	                		$rootScope.sync_status = true;
//	                    	$rootScope.$broadcast('change_sync_status');
//	                	});
//	                    urlService.hide_loading();
//	                    POS_ENABLE_SYNC=false;
//	                    //check update for update
//	                    reloadPOSPage();
//	                }).catch(function(){
//	                    urlService.hide_loading();
//	                    POS_ENABLE_SYNC=false;
//	                    //check update for update
//	                    reloadPOSPage();
//	                });
//                }
//            });
//        }else{
//            console.log( "offline");
//            urlService.hide_loading();
//            urlService.show_toast(NETWORK_ERROR);
//        }
//
//      };

      //sync assign to url service
      urlService.pos_sync=$scope.sync;

	urlService.show_loading=function showRefresh(){
	  $(".glyphicon-refresh").addClass("refresh-spinner");
	};

	urlService.hide_loading=function hideRefresh(){
	    $(".glyphicon-refresh").removeClass("refresh-spinner");
	    checkstorage();
	};

	function checkstorage(){
		checkStoragePercent().then(function(data){
		if(data){
		  urlService.show_toast("memory usage exceed 70% .please free the space");        
		}else{
		  console.log("memory is not reached 70%");
		}
	  }).catch(function(error){
		  console.log(error);
	  });
	}	

	//trigger event for getting data at intiallly.
    //$scope.sync();

	window.addEventListener('load', function(e) {
	  if (navigator.onLine) {
	    console.log("online");
	    urlService.show_toast(CONNECTED_NETWORK);
	  } else {
	    console.log("offline");
	    urlService.show_toast(NETWORK_ERROR);
	  }
	}, false);

	window.addEventListener('online', function(e) {
	  console.log("And we're back");
	  urlService.show_toast(CONNECTED_NETWORK);
	  //$scope.sync();
	}, false);

	window.addEventListener('offline', function(e) {
	  console.log("Connection is flaky.");
	  urlService.show_toast(NETWORK_ERROR);
	  POS_ENABLE_SYNC=false;
	}, false);

	//show toast  message on POS
	
	urlService.show_toast=function toast_msg(msg){
	   $mdToast.show( $mdToast.simple()
	  	.textContent(msg)
	  	.position('top right')
	  	.hideDelay(5000));
	}

	function checkNotificationPermission(){

	 enableNotificaiton().then(function(data){

	  		if(data==false){
	  		  urlService.show_toast(NOTIIFICATION_ERROR);
	  		}

	  		  checkPersistent().then(function(data){
	  			  console.log(""+data);
	  		  }).catch(function(error){
	  			  console.log(""+error);
	  		  });
	  		});
	}  

	checkNotificationPermission();


  }]
  })
}(window.angular));
