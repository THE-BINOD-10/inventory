;(function (angular) {
  "use strict";

  angular.module("auth").service("Session", function ($rootScope, $q, $http) {

    var that = this;
    that.host = 'http://127.0.0.1:8099/';
    // that.host = 'https://api.stockone.in/';
    that.url = that.host+'rest_api/';
    window['manifest_api_url'] = that.url+'get_manifest_json/';

    that.pos_host = 'http://pos.mieone.com/';

    function resetSession () {

      angular.extend(that, {

        "userId"  : null,
        "userName": null,
        "parent": {},
        "roles"   : [],
        "user_profile" : {},
        "notification_count": 0,
      });
    }

(function() {
      setTimeout(function(){
        var OneSignal = window.OneSignal || [];
        OneSignal.push(function() {
            OneSignal.init({
              appId: "98737db9-a2c9-4ff7-be74-42149f21679f",
            });
        });

        OneSignal.getUserId(function(userId) {
        console.log("OneSignal User ID:", userId);
        OneSignal.webpushid = userId;
        var data = {'wpn_id': userId};
        $http.post(that.url + "save_webpush_id/", data).then(function (resp) {
            if (resp.message != "success") {
                console.log("Save web push failed");
            }
        });
      });
      }, 0);
    })();

    resetSession();

    this.get = function () {

      return {

        "userId"  : this.userId,
        "userName": this.userName,
        "parent"  : this.parent,
        "roles"   : this.roles,
        "user_profile" : this.user_profile,
        "notification_count" : this.notification_count
      };
    };

    this.set = function (data) {

      this.userId   = data.userId;
      this.userName = data.userName;
      this.parent = data.parent;
      this.roles    = data.roles;
      this.user_profile = data.user_profile;
      this.notification_count = data.notification_count

      this.changeUserData();
    };

    this.unset = resetSession;

    this.changeUserData = function() {

      angular.forEach(that.roles.permissions, function(value, key) {
        if (value == "true") {
          that.roles.permissions[key] = Boolean(true);
        } else if (value == "false") {
          that.roles.permissions[key] = Boolean(false);
        }
      });
      $rootScope.$broadcast('change_user_data');
    };

    var deferredStatus = null;
    var special = ["add_shipmentinfo", "add_qualitycheck", "pos_switch", "production_switch", "setup_status", "tally_config", "change_inventoryadjustment"];
    this.check_permission = function(data) {

      //deferredStatus = $q.defer();
      if (this.roles.permissions) {
        if( special.indexOf(data) > -1) {
          return this.roles.permissions[data];
          //deferredStatus.resolve(String(this.roles.permissions[data]));
        } else if(data == "is_superuser") {
          return this.roles.permissions["is_superuser"];
          //deferredStatus.resolve(String(this.roles.permissions["is_superuser"]));
        } else if(Boolean(this.roles.permissions["is_staff"]) || Boolean(this.roles.permissions["is_superuser"])) {
          return true;
          //deferredStatus.resolve("true");
        } else if (!(this.roles.permissions[data])) {
          return false;
          //deferredStatus.resolve("false");
        } else {
          return true;
          //deferredStatus.resolve("true");
        }
      } else {
        return false;
        //deferredStatus.resolve("false");
      }
      //return deferredStatus.promise;
    }
  });

}(window.angular));
