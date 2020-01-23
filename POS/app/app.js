
var app=angular.module('App', ['ngMaterial','ui.router','FBAngular','ngAnimate','ui.bootstrap','customer','sku', 'money', 'paymenttype', 'login', 'summary', 'pending', 'order', 'pageheader', 'more', 'pageheader']);

app.service('urlService', function($rootScope){

    this.mainUrl = ENDPOINT;//'http://dev.stockone.in/';
    this.stockoneUrl = STOCKONE;
    this.userData = {"VAT":0};
    this.VAT = 0;
    this.hold_data = [];
    this.current_order = {"customer_data" : {"customer_extra": {}},
                          "sku_data" : [],
                          "summary":{"total_quantity": 0 , "total_amount": 0, "total_discount": 0, "subtotal": 0, "VAT": 0, 
                                    "unit_price": 0, "cgst":0, "sgst": 0, "igst":0, "utgst":0},
                          "money_data": {},
                          "status": 0
                          };
  
    this.user_update = true;
    that = this;

    //sync status
    checkPOSSync().then(function(data){
        $rootScope.sync_status = data;
    });

    this.changeCurrentOrder = function() {

      $rootScope.$broadcast('change_current_order');
    };

    this.prepForBroadcast = function(msg) {

      this.changeCurrentOrder();
    };

   });

app.factory('manageData', function($rootScope) {

  var storage = {};

  storage.prepForBroadcast = function(msg) {
        this.customer_number = '';
        this.broadcastItem();
  };
  storage.broadcastItem = function() {
        $rootScope.$broadcast('handleBroadcast');
  };
  return storage;
})

/*app.run(function($rootScope, $window) {
  $rootScope.$on('$stateChangeStart',
    function(event, toState, toParams, fromState, fromParams) {
      if (toState.external) {
        event.preventDefault();
        $window.open(toState.url, '_self');
      }
    });
})*/

app.config(function($stateProvider, $urlRouterProvider,$httpProvider){
      
      $httpProvider.defaults.withCredentials = true;

      // For any unmatched url, send to /route1
      $urlRouterProvider.otherwise("/login");

      
      $stateProvider
        .state('login', {
            //url: STOCKONE,
            template: '<login></login>',
            //external: true
        })
        .state('home', {
            url: '/home',
            templateUrl: '/app/views/home.html'
        })
        .state('more', {
            url: '/more',
            template: '<more></more>'
        })
  }).
  run(["$rootScope", "$state", "$location", "$http","urlService",
    function ($rootScope, $state, $location, $http, urlService) {

      if (typeof(urlService.userData.user_name) != "undefined") {

        $state.go("home");
      } else {

        if (typeof($location.$$search.user_id) != "undefined") {

          urlService.userData = {'user_name':$location.$$search.user_name,
				 'user_id': $location.$$search.user_id, 'VAT':0}
        } else {

          //$state.go("login")
        }
      }
      $rootScope.$on("$stateChangeStart", function (event) {
        console.log("from wms");
      })
    }
  ])

app.factory('printer', ['$rootScope', '$compile', '$http', '$timeout','$q', function ($rootScope, $compile, $http, $timeout, $q) {
        var printHtml = function (html) {
            var deferred = $q.defer();
            var hiddenFrame = $('<iframe style="visibility: hidden"></iframe>').appendTo('body')[0];
            $(hiddenFrame).on('load', function () {
                if (!hiddenFrame.contentDocument.execCommand('print', false, null)) {
                    hiddenFrame.contentWindow.focus();
                    hiddenFrame.contentWindow.print();
                }
                hiddenFrame.contentWindow.onafterprint = function () {
                    $(hiddenFrame).remove();
                };
            });
            var htmlContent = ""+
                        "<html>"+
                            '<body onload="printAndRemove();">' +
                                html +
                            '</body>'+
                        "</html>";
            var doc = hiddenFrame.contentWindow.document.open("text/html", "replace");
            doc.write(htmlContent);
            deferred.resolve();
            doc.close();
            return deferred.promise;
        };

        var openNewWindow = function (html) {
            var newWindow = window.open("printTest.html");
            newWindow.addEventListener('load', function(){
                $(newWindow.document.body).html(html);
            }, false);
        };

        var print = function (templateUrl, data) {
            $http.get(templateUrl).success(function(template){
                var printScope = $rootScope.$new()
                angular.extend(printScope, data);
                var element = $compile($('<div>' + template + '</div>'))(printScope);
                var waitForRenderAndPrint = function() {
                    if(printScope.$$phase || $http.pendingRequests.length) {
                        $timeout(waitForRenderAndPrint);
                    } else {
                        // Replace printHtml with openNewWindow for debugging
                        printHtml(element.html());
                        printScope.$destroy();
                    }
                };
                waitForRenderAndPrint();
            });
        };

        var printFromScope = function (templateUrl, scope) {
            $rootScope.isBeingPrinted = true;
            $http.get(templateUrl).success(function(template){
                var printScope = scope;
                var element = $compile(angular.element('<div>' + template + '</div>'))(printScope);
                var waitForRenderAndPrint = function() {
                    if (printScope.$$phase || $http.pendingRequests.length) {
                        $timeout(waitForRenderAndPrint);
                    } else {
                        printHtml(element.html()).then(function() {
                           $rootScope.isBeingPrinted = false;
                       });

                    }
                };
                waitForRenderAndPrint();
            });
        };
        return {
            print: print,
            printFromScope:printFromScope
        }


}]);


