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
    self.extra_fields_flag = false;
    self.extra_fields = {};
    self.repos;
    self.querySearch   = querySearch;
    self.selectedItemChange = selectedItemChange;
    self.searchTextChange = searchTextChange;
    self.customer = {};
    self.searchText;
    self.searchOrder;
    self.urlservice = urlService;
    urlService.current_order.customer_extra = {};
    //get extra fields
    $http.get(urlService.mainUrl+'rest_api/get_extra_fields/?user='+urlService.userData.parent_id)
    .then( function(data) {
        extraFieldsresposne(data.data);
        //save extra fields locally  
        setCheckSum(setCheckSumFormate(JSON.stringify(data.data),EXTRA_FIELDS)).
                          then(function(data){
                              console.log("user data saved on locally "+data); 
                            }).catch(function(error){

                          });
    },function(error){

         getChecsumByName(EXTRA_FIELDS).
                      then(function(result){
                        if(Object.keys(result).indexOf("checksum")!=-1){
                          extraFieldsresposne(JSON.parse(result.checksum));    
                        }else{
                          urlservice.show_toast("No extra fields");
                          console.log("extra fields error " +error.message);
                        }
                      }).catch(function(error){
                        urlservice.show_toast("No extra fields");
                        console.log("extra fields error " +error.message);
                      });

    });

    
  //store extra data in urlservice on change modal
  function extraFieldsresposne(data){
        self.extra_fields = data;
          self.customer.extra_fields = {};
          for (var typ in self.extra_fields) {
              for(var field in self.extra_fields[typ]) {
                  //var temp = self.extra_fields[typ][field].toLowerCase().trim().replace(" ","_");
                  self.customer.extra_fields[self.extra_fields[typ][field]] = "";
              }
          }
      }
    //on change issue type to 'Pre Order' display the extra fields
    $scope.$on('change_issue_type', function(){
        $scope.issue_type = $rootScope.issue_type;
        if($scope.issue_type === "Pre Order") {
            self.extra_fields_flag = true;
        }
        else {
            self.extra_fields_flag = false;
        }
    });
    //on change text in customer extra fields, save it in urlService
    self.save_extra_fields = save_extra_fields;
    function save_extra_fields() {
        for(var  field in self.customer.extra_fields) {
            urlService.current_order.customer_extra[field] = self.customer.extra_fields[field] || '';
        }
    }


    // Get data from backend to show below the search box
    self.get_user_data = get_user_data;
    self.get_order_data = get_order_data;
   
    function get_order_data(key) {
      self.search_term = key;
      var deferred = $q.defer();
      $http.get(urlService.mainUrl+'rest_api/search_pos_order_ids/?user='+urlService.userData.parent_id+'&key='+key)
        .success( function(data) {
          self.repos = data;
          return self.repos.map( function (repo) {
            return repo;
          })
        }).then(function() {
          deferred.resolve(querySearch (key));
        })
      return deferred.promise;
    }

    self.searchOrderChange = searchOrderChange;
    self.original_order_id = '';
    function searchOrderChange(data) {
      if (typeof(data) != "undefined") {
        self.searchOrder = data['original_order_id'];
        self.original_order_id = data['original_order_id'];
        get_customer_data(data);
        // load_order_Data(data);
      }
    }

    self.searchOrderText = searchOrderText;
    function searchOrderText(text) {
      if (self.searchText != self.original_order_id) {
        self.customer = {}
      }
    }

    self.get_customer_data = get_customer_data;
    function get_customer_data(customer) {
      $http.get(urlService.mainUrl+'rest_api/get_pos_customer_data?user='+urlService.userData.parent_id+'&key='+customer.customer_id).then(function(data) {
        data=data.data;
        self.customer = urlService.current_order.customer_data = data;
      })
    }

    // self.load_order_Data = load_order_Data;
    // function load_order_Data(customer) {
    //   $http.get(urlService.mainUrl+'rest_api/get_view_order_details?id=''&order_id='+customer.original_order_id).then(function(data) {
    //     data=data.data;
    //     self.customer = urlService.current_order.customer_data = data;
    //   })
    // }

    function get_user_data(key) {
      if (key.length > 1) {
        self.search_term = key;
        var deferred = $q.defer();
        $http.get(urlService.mainUrl+'rest_api/search_pos_customer_data?user='+urlService.userData.parent_id+'&key='+key)
          .then(function(data) {
            data=data.data;
            console.log($window);
            if(data.message === "invalid user") {
              $window.location.reload();
            } else {
              onLineUserData(data);
            } 
            deferred.resolve(querySearch (key)); 
          },function(error){
              console.log("activate offline");
              getCustomerData(urlService.userData.parent_id,key).then(function(data){
                offLineUserData(data);
              }).then(function(){
                deferred.resolve(querySearch (key));
              });   
          }).then(function() {
              /*deferred.resolve(querySearch (key));*/
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
      console.log(urlService)
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
      for(var  field in self.customer.extra_fields) {
        user_details[field] = self.customer.extra_fields[field] || '';
      }

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
                 updateCustomer(self.searchText, "");
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
