;(function (angular) {
  "use strict";

  angular.module("customer", [])
         .component("customer", {

           "templateUrl": "/app/customer/customer.template.html",
           "controller"  : ["$http", "$scope","$rootScope", "$timeout", "$q", "$log", "urlService",
                            "manageData", "$location", "$window",
  function ($http, $scope,$rootScope, $timeout, $q, $log, urlService, manageData, $location, $window) {

    var self = this;

    self.simulateQuery = false;
    self.isDisabled    = false;

    self.repos;
    self.querySearch   = querySearch;
    self.selectedItemChange = selectedItemChange;
    self.searchTextChange   = searchTextChange;

    self.customer = {};
    self.searchText;

    // Get data from backend to show below the search box
    self.get_user_data = get_user_data;
   /* 
   function get_user_data(key) {

        self.search_term = key;
        var deferred = $q.defer();
        $http.get(urlService.mainUrl+'search_customer_data/?user='+urlService.userData.parent_id+'&key='+key)
          .success( function(data) {
            if (data.length==0 && self.search_term!=0) {
                self.customerButton = true;
            }
            else { self.customerButton = false; }
            self.repos = data;
            return self.repos.map( function (repo) {
              repo.value = repo.Number.toLowerCase();
              return repo;
            })
          }).then(function() {
            deferred.resolve(querySearch (key));
          })
        return deferred.promise;
    }
    */

     function get_user_data(key) {
        if (key.length > 1) {
            self.search_term = key;
            var deferred = $q.defer();

            $http.get(urlService.mainUrl+'rest_api/search_pos_customer_data?user='+urlService.userData.parent_id+'&key='+key)
              .then(function(data) {
                 console.log($window);
                if(data.message === "invalid user") {
                    $window.location.reload();
                } else {
                  data=data.data;
                  onLineUserData(data);
                }  
              },function(error){
                  console.log("activate offline");
                  getCustomerData(key).then(function(data){
                      offLineUserData(data);
                  });    
              }).then(function() {
                  deferred.resolve(querySearch (key));
              });
            return deferred.promise;
          }
        return [];
    }

    //function online get user data process
    function onLineUserData(data){
      if (data.length==0 && self.search_term!=0) {
        self.customerButton = true;
      }else {
        self.customerButton = false;
      }
      self.repos = data;
      return self.repos.map( function (repo) {
        repo.value = repo.Number.toLowerCase();
        return repo;
      });
    }

    //function offline get user Data
    function offLineUserData(data){
      onLineUserData(data);
    }

    // clear input field when user submit data
    $scope.$on('handleBroadcast', function() {
      self.customer = {};
      self.searchText = "";
      self.customerButton = false;
    });

    //change data
    $scope.$on('change_current_order', function(){
      self.customer = urlService.current_order.customer_data;
      self.searchText = urlService.current_order.customer_data.Number;
      self.customerButton = false;
    })

    $scope.$watch(self.FirstName, function (value) {
            $scope.FirstName = value;
    });

    // Internal methods
    function querySearch (query) {
      //var results = query ? self.repos.filter( createFilterFor(query) ) : self.repos,
      var results = self.repos,
          deferred;
      if (self.simulateQuery) {
        deferred = $q.defer();
        $timeout(function () { deferred.resolve( results ); }, Math.random() * 1000, false);
        return deferred.promise;
      } else {
        return results;
      }
    }

    function searchTextChange(text) {
      $log.info('Text changed to ' + text);
      if (self.searchText != urlService.current_order.customer_data.Number) {
        self.customer = {}
      }
    }

    function selectedItemChange(item) {
      if (!(typeof(item) == "undefined")) {
        self.customer = urlService.current_order.customer_data = item;
        $log.info('Item changed to ' + JSON.stringify(item));
      }
    }

    // Create filter function for a query string
    function createFilterFor(query) {
      var lowercaseQuery = angular.lowercase(query);

      return function filterFn(item) {
        return (item.value.indexOf(lowercaseQuery) === 0);
      };

    }

    // add customer to database
    self.new_customers = [];
    self.addCustomer = addCustomer;
    self.customer_status = false;
    function addCustomer() {
      var data =  [];
      var user_details={"user": urlService.userData.parent_id,
                         "firstName": self.customer.FirstName || '',
                         "secondName": self.customer.LastName || '',
                         "mail": self.customer.Email || '',
                         "number": parseInt(self.searchText) || ''};

      data = data.concat(user_details);
      data = $.param({
          customers : JSON.stringify(data)
                   });
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
            $http.post(urlService.mainUrl+'rest_api/add_customer/', data)
              .then( function(data) {
                 data=data.data; 
                 if(data.message === "invalid user") {
                        $window.location.reload();
                    } else {
                 console.log(data);
                 self.customerButton = false;
               }
              },function(error){
                console.log("offline");   
                $rootScope.sync_status = true;
                $rootScope.$broadcast('change_sync_status');
                setSynCustomerData(user_details).
                            then(function(data){
                              console.log(data);
                              self.customerButton = false;
                              syncPOSData(false).then(function(data){
                                  // $rootScope.sync_status = false;
                                  //$rootScope.$broadcast('change_sync_status');
                              });

                            }).catch(function(error){

                            });

              });

            self.customer_status = true;
            $timeout(function() {
              self.customer_status = false;
            }, 2000);

    }

    // to show customer add button
    self.customerButton = false;

    self.updateCustomer = updateCustomer;
    function updateCustomer(name, var_type) {
       if(var_type=="first_name") {
           urlService.current_order.customer_data.FirstName = self.customer.FirstName;
        }
       else if (var_type=="last_name") {
           urlService.current_order.customer_data.LastName = self.customer.LastName;
        }
       else if (var_type=="email") {
           urlService.current_order.customer_data.Email = self.customer.Email;
        }
       urlService.current_order.customer_data.Number = self.searchText;
       urlService.current_order.customer_data.value = self.searchText;
       console.log(urlService.current_order.customer_data);
    }

    self.checkNumber = checkNumber;
    function checkNumber(name) {

      $timeout(function() {
        if (typeof(self.customer.FirstName) == "undefined") {

          self.customerButton = true;
        }
        else {

          self.customerButton = (self.customer.FirstName.length == 0) ? true : false;
        }
      }, 500);
    }
  }]
 });
}(window.angular));
