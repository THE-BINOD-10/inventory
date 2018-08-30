;(function (angular) {
  "use strict";

  angular.module("auth", []).service("Auth", ["$q", "$http", "Session", "$state",

    function ($q, $http, Session, $state) {

      var deferredStatus = null;

      this.login = function (credentials) {

        deferredStatus = null;

        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        return $http.post(Session.url + "wms_login/", credentials)
                    .then(function (resp) {

          resp = resp.data;
          if (resp.message != "Fail") {
             //setloginStatus(resp);
             Session.set(resp.data);
            
          }
          return resp;
        });
      };

      this.signup = function(data) {

        deferredStatus = null;

        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";

        return $http.post(Session.url + "create_user/", data)
                    .then(function (resp) {

            resp = resp.data;
         });
      };


      this.isAuthorized = function () {

        var session = Session.get();

        return !!(session && session.userId);
      };

      this.logout = function () {

        return $http.get(Session.url + "logout/", {withCredentials: true}).then(function () {

          Session.unset();
          deferredStatus = null;
          //deleteDB();
        });
      };

      this.status = function () {

        if (deferredStatus) {

          return deferredStatus.promise;
        }

        deferredStatus = $q.defer();

        if(Session.userName) {

          deferredStatus.resolve("Success");
          return deferredStatus.promise;
        }

        $http.get(Session.url + "status/", {withCredentials: true}).then(function (resp) {

          resp = resp.data;

          if ((resp.message != "Fail") && resp.data.userId) {
             //setloginStatus(resp);
             Session.set(resp.data);

            if (resp.data.roles.permissions["setup_status"] == "true") {

              $state.go("app.Register");
            }
          } else {
            
            $state.go("user.signin");
          }

          deferredStatus.resolve(resp.message);
       
        }).catch(function(err){

            /*getloginStatus().then(function(resp){
              if((resp.message != "Fail") && resp.data.userId) {
                 //TODO add the statusinto indexDb  
                 Session.set(resp.data);
                  if(resp.data.roles.permissions["setup_status"] == "true") {
                   $state.go("app.Register");
                  }
                
               }else{
                 $state.go("user.signin");
               }

               if(resp.message == "Success") {
                 if(resp.data.user_profile["user_type"] == "customer") {
                   deferredStatus.resolve(resp.message);
                 }
               }
           });*/
       });

        return deferredStatus.promise;
      };

      this.update = function () {

        deferredStatus = $q.defer();

        $http.get(Session.url + "status/", {withCredentials: true}).then(function (resp) {

          resp = resp.data;

          if ((resp.message != "Fail") && resp.data.userId) {
             /*setloginStatus(resp);*/
             Session.set(resp.data);

          }

          deferredStatus.resolve(resp.message);
        })
        return deferredStatus.promise;
      };
  }]);

}(window.angular));
