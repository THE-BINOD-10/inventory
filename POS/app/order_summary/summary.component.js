;(function (angular) {
  "use strict";

  angular.module("summary", [])
         .component("summary", {

           "templateUrl": "/app/order_summary/summary.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData", "$state", "$location", "$window",
    function ($http, $scope, urlService, manageData, $state, $location, $window) {

      var self = this;
      self.VAT = urlService.VAT;
      self.order = urlService.current_order.summary;


		if (urlService.user_update) {

        
            console.log("online");
            $http.get( urlService.mainUrl+'rest_api/get_pos_user_data/?id='+urlService.userData.parent_id).
					then(function(data, status, headers, config) {
                data=data.data;
                if (data.status == "Success"){
                  console.log(data);
                  urlService.userData = data;
                  urlService.VAT = data.VAT;
                  self.VAT = data.VAT;

                  //save user status in local db
                  setCheckSum(setCheckSumFormate(JSON.stringify(data),USER_DATA)).
                          then(function(data){
                              console.log("user data saved on locally "+data); 
                                      
                              if(navigator.onLine){
                                //sync pos data 
                                navigator.serviceWorker.ready.then(function() {
                                  
                                  urlService.show_loading();
                                  syncPOSTransactionData().then(function(){
                                    urlService.hide_loading();
                                  }).catch(function(){
                                    urlService.hide_loading();
                                  });
                                });
                              }else{
                                console.log( "offline");
                                urlService.hide_loading();
                              }               
                          }).catch(function(error){
                             console.log("user data saved fail in locally "+error.message); 
                          })
                } else {
                  $window.location.href = urlService.stockoneUrl;//+ "?next='"+ urlService.mainUrl + "'";
                  //$state.go("login");
                }
              },function(error){

                console.log("offline");
                //get user status from local db
                getChecsumByName(USER_DATA).then(function(result){

                  var data=JSON.parse(result.checksum);

                   if (data.status == "Success"&& urlService.userData.parent_id==data.parent_id){
                      console.log(data);
                      urlService.userData = data;
                      urlService.VAT = data.VAT;
                      self.VAT = data.VAT;

                  }else{
                      $window.location.href = urlService.stockoneUrl; 
                  }
                }).catch(function(){
                  
                  $window.location.href = urlService.stockoneUrl; 
                
                });

              });
      
    }

      /*
      if (urlService.user_update) {
      $http.get( urlService.mainUrl+'get_pos_user_data/?id='+urlService.userData.parent_id).success(function(data, status, headers, config) {

          if (data.status == "Success"){
            console.log(data);
            urlService.userData = data;
            urlService.VAT = data.VAT;
            self.VAT = data.VAT;
          } else {

            $state.go("login");
          }
        })
      }*/
      $scope.$on('handleBroadcast', function() {

        self.order = urlService.current_order.summary;
      });

      $scope.$on('change_current_order', function(){

        self.order = urlService.current_order.summary;
      });
    }]
  });
}(window.angular));
