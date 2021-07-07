'use strict';

var stockone = angular.module('urbanApp');

angular
  .module('urbanApp')
  .service('myservice', function() {
      this.name = "unknown";
    });

angular
  .module('urbanApp')
  .controller('AppCtrl', ['$rootScope', '$scope', '$state','$http', '$localStorage', 'Session', 'myservice', "Auth", "AUTH_EVENTS", "Service", "$timeout", 'Analytics', 'Idle', 'Keepalive', '$modal', '$window',
        function AppCtrl($rootScope, $scope, $state, $http, $localStorage, Session, myservice, Auth, AUTH_EVENTS, Service, $timeout, Analytics, Idle, Keepalive, $modal, $window) {
      $scope.started = false;
      function closeModals() {
          if ($scope.warning) {
              $scope.warning.close();
              $scope.warning = null;
          }

          if ($scope.timedout) {
              $scope.timedout.close();
              $scope.timedout = null;
          }
      }

      $scope.$on('IdleStart', function() {
          closeModals();

          $scope.warning = $modal.open({
              templateUrl: 'warning-dialog.html',
              windowClass: 'modal-warning'
          });
      });
      
      $scope.$on('IdleEnd', function() {
          closeModals();
          //Session.unset();
          //$state.go("user.signin"); 
	  //$window.location.reload();
      });

      $scope.$on('IdleTimeout', function() {
          closeModals();
          $scope.logout()
          //Session.unset();
          //$state.go("user.signin");
          //$window.location.reload(); 
	 // $scope.timedout = $modal.open({
          //     templateUrl: 'timedout-dialog.html',
          //     windowClass: 'modal-danger'
          // });
      });

      $scope.start = function() {
          console.log('start');
          closeModals();
          Idle.watch();
          $scope.started = true;
      };

      $scope.stop = function() {
          console.log('stop');
          closeModals();
          Idle.unwatch();
          $scope.started = false;

      }; 
      $rootScope.process = false;
      $scope.session = Session;
      $scope.stockone_loader = false;

      $rootScope.$on('$stateChangeSuccess', function () {
        $rootScope.process = false;
        $scope.stockone_loader = true;
      })

      $scope.mobileView = 767;

      $scope.app = {
        name: 'Urban',
        author: 'Nyasha',
        version: '1.0.0',
        year: (new Date()).getFullYear(),
        layout: {
          isSmallSidebar: false,
          isChatOpen: false,
          isFixedHeader: true,
          isFixedFooter: false,
          isBoxed: false,
          isStaticSidebar: false,
          isRightSidebar: false,
          isOffscreenOpen: false,
          isConversationOpen: false,
          isQuickLaunch: false,
          sidebarTheme: '',
          headerTheme: ''
        },
        isMessageOpen: false,
        isConfigOpen: false
      };

      $scope.user = {};

      $scope.myservice = myservice;
      $scope.user = Session.get();

      $scope.$on('change_user_data', function(){
        $scope.user = Session.get();
        $scope.permissions = Session.roles.permissions;
        console.log($scope.user);
        localStorage.setItem('username', $scope.user.userName);
      });

      $scope.service = Service;
      $scope.Auth = Auth;

      $scope.permissions = Session.roles.permissions;

      $rootScope.$on('$stateChangeSuccess', function(event, toState, toParams, fromState, fromParams){
        $timeout(function() {
          var height = 0
          if ($scope.user.user_profile['trail_user'] == "true") {
            height = 30;
          }
          if(!(angular.element(".page-layout").hasClass("no-scroll"))) {
            $(".page-layout").css('height',$(window).height()-height);
            $(".page-layout").css('overflow-y', 'auto');
          }
        }, 1000)
      })

      $( window ).resize(function() {
        var height = 0
          if ($scope.user.user_profile['trail_user'] == "true") {
            height = 30;
          }
        if(!(angular.element(".page-layout").hasClass("no-scroll"))) {

          $(".page-layout").css('height',$(window).height()-height);
          $(".page-layout").css('overflow-y', 'auto');
        }
      })

      $scope.scroll_bottom = function(e) {

        $rootScope.$broadcast('scroll-bottom');
      }
      /*
      $rootScope.$on('$stateChangeSuccess', function(event, toState, toParams, fromState, fromParams){
        $timeout(function() {
          var height = 0
          if ($scope.user.user_profile['trail_user'] == "true") {
            height = 30;
          }
          $(".layout-body").css('height',$(window).height()-height-$(".layout-header").height()-10-$(".brand:visible.visible-xs").height());
          $(".layout-body").css('overflow-y', 'auto');
        }, 1000)
      })

      $( window ).resize(function() {
        var height = 0
          if ($scope.user.user_profile['trail_user'] == "true") {
            height = 30;
          }
        $(".layout-body").css('height',$(window).height()-height-height-$(".layout-header").height()-10-$(".brand:visible.visible-xs").height()-20);
        $(".layout-body").css('overflow-y', 'auto');
      })
      */

      $scope.clear = function () {

        Service.alert_msg("Do want to clear total data").then(function(msg) {
          if (msg == "true") {

            Service.apiCall("clear_demo_data/").then(function(data){
              if(data.message) {
                updated_demod_data();
              }
            });
          }
        });
      }

      $scope.load = function () {

        Service.alert_msg("Do want to clear total data and dumps the Demo data").then(function(msg) {
          if (msg == "true") {
            Service.apiCall("load_demo_data/").then(function(data){
              if(data.message) {
                updated_demod_data();
              }
            });
          }
        });
      }

      function updated_demod_data() {

        if ($state.current.name != "app.dashboard") {
          $state.go("app.dasboard");
        } else {
          $state.reload();
        }
      }

      if (angular.isDefined($localStorage.layout)) {
        $scope.app.layout = $localStorage.layout;
      } else {
        $localStorage.layout = $scope.app.layout;
      }

      $scope.$watch('app.layout', function () {
        $localStorage.layout = $scope.app.layout;
      }, true);

      $scope.getRandomArbitrary = function () {
        return Math.round(Math.random() * 100);
      };
      
      $scope.logout = function() {
        var user_type = $scope.permissions.user_type;
        var parent_username = Session.parent.parent_username
        var user_types = ['central_admin', 'distributor', 'warehouse'];
        Auth.logout().then(function () {
          if (parent_username == 'sm_admin') {
            $state.go("user.smlogin");
          } else {
            $state.go("user.signin");
          }
          localStorage.removeItem('order_management');
          //$rootScope.$broadcast(AUTH_EVENTS.logoutSuccess);
        });
      }

      var special = ["add_shipmentinfo", "add_qualitycheck", "pos_switch", "production_switch", "setup_status", "order_manage", "add_productproperties", "add_pricemaster", "add_sizemaster", "add_paymentsummary", "add_issues", "show_pull_now", "tally_config", "change_inventoryadjustment"];
      var labels_list = ["MASTERS_LABEL", "INBOUND_LABEL", "PRODUCTION_LABEL", "STOCK_LABEL", "OUTBOUND_LABEL", "SHIPMENT_LABEL",
      "OTHERS_LABEL", "PAYMENT_LABEL", "DASHBOARD", "UPLOADS", "REPORTS", "CONFIGURATIONS" , "NOTIFICATION_LABEL","MASTERS_VIEW_LABEL"];
      $scope.show_tab = function(data) {
        if (!(Session.userName)) {
          return false;
        } else if(labels_list.indexOf(data) > -1) {
          return Session.roles.labels[data];
        }else if(special.indexOf(data) > -1) {
          return Session.roles.permissions[data];
        } else if (!data) {
          return true;
        } else if (!(Session.roles.permissions[data])) {
          return false;
        } else if (data == 'add_orderdetail' && Session.parent['72networks']){
          return false;
        } else if (data == 'add_openpo' && Session.roles.permissions.enable_pending_approval_pos){
          return false;
        } else {
          return true;
        }
      }

      $rootScope.$on('invalidUser', function () {
        $state.go("user.signin");
        Session.unset();
      });
    }
]);

angular
  .module('urbanApp')
  .config(['AnalyticsProvider', function (AnalyticsProvider) {
   AnalyticsProvider.setAccount('UA-89737240-2');
   AnalyticsProvider.trackPages(true);
   AnalyticsProvider.setPageEvent('$accountCreationSuccess');
}]).run(['Analytics', function(Analytics) { }]);
