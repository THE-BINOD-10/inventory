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
          update_manifest(resp.data);
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
          if (window.current_version) {
            $http.get(Session.url + "service_worker_check/?current_version="+window.current_version).then(function (data) {

              if (data.data.reload) {
                location.reload();
              }
            })
          }
          resp = resp.data;
          update_manifest(resp.data);

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
          update_manifest(resp.data);
          if ((resp.message != "Fail") && resp.data.userId) {
             /*setloginStatus(resp);*/
             Session.set(resp.data);

          }

          deferredStatus.resolve(resp.message);
        })
        return deferredStatus.promise;
      };

      function update_manifest(resp_data) {
        var temp_user_list = ["sagar_fab"];
        var manifest_json = {
            "name": "STOCKONE",
            "short_name": "STOCKONE",
            "icons": [
            {
              "src": "https://go.stockone.in/images/stockone_logo.png",
              "sizes": "192x192",
              "type": "image\/png"
            },
            {
              "src": "https://go.stockone.in/images/stockone_logo.png",
              "sizes": "512x512",
              "type": "image\/png"
            }
          ],
          "start_url": "/#/",
          "display": "standalone",
          "background_color": "#ffffff",
          "orientation":"potrait",
          "gcm_sender_id": "21194035295"
        };
        if(resp_data.parent && 'userName' in resp_data.parent && temp_user_list.indexOf(resp_data.parent.userName.toLowerCase()) != -1) {
          manifest_json["name"] = "My Tee";
          manifest_json["short_name"] = "My Tee";
          manifest_json["icons"] =  [
            {
              "src": "https://go.stockone.in/images/MYTEE.png",
              "sizes": "192x192",
              "type": "image/png"
            },
            {
              "src": "https://go.stockone.in/images/MYTEE.png",
              "sizes": "512x512",
              "type": "image/png"
            }
          ]
        }
        const stringManifest = JSON.stringify(manifest_json);
        const blob = new Blob([stringManifest], {type: 'application/json'});
        const manifestURL = URL.createObjectURL(blob);
        document.querySelector('#my-manifest-placeholder').setAttribute('href', manifestURL);
      };

  }]);

}(window.angular));
