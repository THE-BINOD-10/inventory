'use strict';

angular
  .module('urbanApp')
  .service('myservice', function() {
      this.name = "unknown";
    });

angular
  .module('urbanApp')
  .controller('AppCtrl', ['$rootScope', '$scope', '$state','$http', '$localStorage', 'Session', 'myservice', "Auth", "AUTH_EVENTS", "Service", "$timeout",
        function AppCtrl($rootScope, $scope, $state, $http, $localStorage, Session, myservice, Auth, AUTH_EVENTS, Service, $timeout) {

      $rootScope.process = false;

      $rootScope.$on('$stateChangeSuccess', function () {
        $rootScope.process = false;
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

        Auth.logout().then(function () {

                 $state.go("user.signin");
                 localStorage.removeItem('order_management');
                   //$rootScope.$broadcast(AUTH_EVENTS.logoutSuccess);
                 });
      }

      var special = ["add_shipmentinfo", "add_qualitycheck", "pos_switch", "production_switch", "setup_status", "order_manage", "add_productproperties", "add_pricemaster", "add_sizemaster", "add_paymentsummary", "add_issues"];
      var labels_list = ["MASTERS_LABEL", "INBOUND_LABEL", "PRODUCTION_LABEL", "STOCK_LABEL", "OUTBOUND_LABEL", "SHIPMENT_LABEL", 
      "OTHERS_LABEL", "PAYMENT_LABEL"];
      $scope.show_tab = function(data) {
        if (!(Session.userName)) {
          return false;
        } else if(labels_list.indexOf(data) > -1) {
          return Session.roles.labels[data];
        }else if(special.indexOf(data) > -1) {
          return Session.roles.permissions[data];
        } else if (Boolean(Session.roles.permissions["is_staff"]) || Boolean(Session.roles.permissions["is_superuser"])) {
          return true;
        } else if (!(Session.roles.permissions[data])) {
          return false;
        } else {
          return true;
        }
      }
    }
]);

