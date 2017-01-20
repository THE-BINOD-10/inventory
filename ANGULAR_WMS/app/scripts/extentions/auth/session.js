;(function (angular) {
  "use strict";

  angular.module("auth").service("Session", function ($rootScope, $q) {

    var that = this;
    //that.host = 'https://api.stockone.in/';
    //that.host = 'http://dev.stockone.in/';
    that.host = 'http://176.9.181.43:7655/';
    that.url = that.host+'rest_api/';

    function resetSession () {

      angular.extend(that, {

        "userId"  : null,
        "userName": null,
        "roles"   : [],
        "user_profile" : {}
      });
    }

    resetSession();

    this.get = function () {

      return {

        "userId"  : this.userId,
        "userName": this.userName,
        "roles"   : this.roles,
        "user_profile" : this.user_profile
      };
    };

    this.set = function (data) {

      this.userId   = data.userId;
      this.userName = data.userName;
      this.roles    = data.roles;
      this.user_profile = data.user_profile;

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
    var special = ["add_shipmentinfo", "add_qualitycheck", "pos_switch", "production_switch", "setup_status"];
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
