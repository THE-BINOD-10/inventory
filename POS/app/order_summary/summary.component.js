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
      var GET_STAFF_DATA=false;
		if (urlService.user_update) {
           console.log("online");
            $http.get( urlService.mainUrl+'rest_api/get_pos_user_data/?id='+urlService.userData.parent_id).
					then(function(data) {
                data=data.data;
                if (data.status == "Success"){
                  console.log(data);
                  urlService.userData = data;
                  urlService.VAT = data.VAT;
                  self.VAT = data.VAT;

                  getUserID().
                    then(function(result){
                      urlService.show_loading();
                      if(result===urlService.userData.parent_id){
                        saveUserData(data)
                      }else{
                        userDiffClearData(data);
                      }
                    }).catch(function(error){
                      urlService.show_loading();
                      userDiffClearData(data);
                    });
                  
                  
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

    //user different clear the data
    function userDiffClearData(user_data){
      clearUserofflineSyncData().
        then(function(){
          if(GET_STAFF_DATA===true){
            saveStaffMembers(self.staff_members);
          }
          saveUserData(user_data);
        }).catch(function(error){
          if(GET_STAFF_DATA===true){
            saveStaffMembers(self.staff_members);
          }
          saveUserData(user_data);
        }); 
    }

    //save user status in local db
    function saveUserData(user_data){

        setCheckSum(setCheckSumFormate(JSON.stringify(user_data),USER_DATA)).
                          then(function(data){
                              console.log("user data saved on locally "+data); 
                                      
                              if(navigator.onLine){
                                //sync pos data 
                                navigator.serviceWorker.ready.then(function() {
                                  
                                  
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
                             urlService.hide_loading();
                             console.log("user data saved fail in locally "+error.message); 
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


      var temp_url=urlService.mainUrl+"rest_api/get_staff_members_list/";
      $http({
        method: 'GET',
        url:temp_url,
        withCredential: true,
        }).success(function(data, status, headers, config) {
          self.staff_members = data.members;
          GET_STAFF_DATA=true;
          $(".preloader").removeClass("ng-show").addClass("ng-hide");
          self.staff_member = self.staff_members[0];
          urlService.current_order.summary.staff_member = self.staff_member;
          urlService.default_staff_member = self.staff_member;  
	 //save user staff members in local db 
          saveStaffMembers(self.staff_members);
                  
        }).error(function() {
          GET_STAFF_DATA=false;
          getChecsumByName(STAFF_MEMBERS).
            then(function(result){
              $scope.$apply(function(){
                console.log("staff members get from local db "+result);
                self.staff_members = JSON.parse(result.checksum);
                $(".preloader").removeClass("ng-show").addClass("ng-hide");
                self.staff_member = self.staff_members[0];
                urlService.current_order.summary.staff_member = self.staff_member;
                urlService.default_staff_member = self.staff_member;
              });
          }).catch(function(error){
              console.log("staff members get from local db error "+error);
              $(".preloader").removeClass("ng-show").addClass("ng-hide");
            });
        });

      //save user staff members in local db  
      function saveStaffMembers(data){
        setCheckSum(setCheckSumFormate(JSON.stringify(data),STAFF_MEMBERS)).
            then(function(data){
              console.log("staff members saved in local db "+data);
            }).catch(function(error){
              console.log("staff members saving issue in local db "+error);
            });

      }  

      self.staff_member_value = staff_member_value;
      function staff_member_value (staff_member_value) {
        self.staff_member = staff_member_value;
        urlService.current_order.summary.staff_member = self.staff_member;
        urlService.default_staff_member = self.staff_member;
      }

    }]
  });
}(window.angular));
