var app=angular.module('App', ['ngAria','ngMaterial','simple-autocomplete','FBAngular', 'Features']);

app.service('urlService', function(){
    this.mainUrl = 'http://176.9.181.43:7777/';
    this.total_customer_data = [];
    this.total_sku_data = [];
    that = this;

    this.checkCustomer = function( mail, number ) {

      var found = false;
      for (i = 0; i < that.total_customer_data.length; i++) {

        if (that.total_customer_data[i].Email == mail || that.total_customer_data[i].Number == number) {
          found =true;
          break;
        }
      }
      return found;
    }
   });

app.factory('manageData', function($rootScope) {

  var storage = {};
  storage.customer_number = '';
  storage.prepForBroadcast = function(msg) {
        this.customer_number = '';
        this.broadcastItem();
  };
  storage.broadcastItem = function() {
        $rootScope.$broadcast('handleBroadcast');
  };
  return storage;
})

app.controller('posController', function($http, $scope, urlService, Fullscreen){

  $scope.name = "Test";
  $scope.customerUrl = urlService.mainUrl;


  // Fullscreen
  $scope.goFullscreen = function () {

      if (Fullscreen.isEnabled())
         Fullscreen.cancel();
      else
         Fullscreen.all();
   };

   $scope.isFullScreen = false;

   $scope.goFullScreenViaWatcher = function() {
      $scope.isFullScreen = !$scope.isFullScreen;
   };
})


  app.controller('Customer', function ($http, $scope, $timeout, $q, $log, urlService, manageData) {
    var self = this;

    self.simulateQuery = false;
    self.isDisabled    = false;

    self.repos;
    self.querySearch   = querySearch;
    self.selectedItemChange = selectedItemChange;
    self.searchTextChange   = searchTextChange;

    self.firstName = "";
    self.lastName = "";
    self.email = "";
    self.cellNumber = "";
    self.searchText;

    self.get_user_data = get_user_data;
    function get_user_data(key) {

        var deferred = $q.defer();
        $http.get(urlService.mainUrl+'search_pos_customer_data?key='+key)
          .success( function(data) {
            self.repos = data;
            repos = data;
            return repos.map( function (repo) {
              repo.value = repo.Number.toLowerCase();
              return repo;
            })
          }).then(function() {
            filter_data = querySearch (key);
            deferred.resolve(filter_data);
          })
        return deferred.promise;
    }

    $scope.$on('handleBroadcast', function() {
      self.firstName = "";
      self.lastName = "";
      self.Email = "";
      self.cellNumber = "";
      self.searchText = "";
      self.customerButton = false; 
    });

    // Internal methods
    function querySearch (query) {
      var results = query ? self.repos.filter( createFilterFor(query) ) : self.repos,
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
      self.firstName = '';
      self.lastName = '';
      self.Email = '';
      self.cellNumber = text;
    }

    function selectedItemChange(item) {
      if (!(typeof(item) == "undefined")) {
        self.firstName = item.FirstName;
        self.lastName = item.LastName;
        self.Email = item.Email;
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
    self.new_customers = [];
    self.addCustomer = addCustomer;
    self.customer_status = false;
    function addCustomer() {
      var customer = {'phoneNumber': self.cellNumber, 'FirstName': self.firstName, 'LastName': self.lastName, 'Email': self.Email}

      if ( self.firstName && self.lastName && self.Email) {
        if (!(urlService.checkCustomer(self.Email,self.cellNumber))){
          self.new_customers.push(customer);

          var data = $.param({
                      firstName: self.firstName,
                      secondName: self.lastName,
                      mail: self.Email,
                      number: self.cellNumber
                     });
          $http.get(urlService.mainUrl+'add_customer/?'+data)
            .success( function(data) {

              console.log(data);
            })
          self.customer_status = true;
          $timeout(function() {
            self.customer_status = false;
          }, 2000);
        } else {

          alert("this number already exist")
        }
      } else {

        alert("Please fill all the fields");
      }
      console.log(self.new_cusomters);
      console.log("added");
      return true;
    }

    self.customerButton = false;
    self.checkNumber = checkNumber;
    function checkNumber(name) {

      $timeout(function() {
        if ((self.firstName.length > 0) && (self.searchText > 0)) {

          console.log("already exist")
        } else {
          self.customerButton = true;
        }
      }, 500);
    }
  });


app.controller('SKU', function ($http, $scope, $timeout, $q, $log, urlService, manageData) {
    var self = this;

    self.simulateQuery = false;
    self.isDisabled    = false;

    self.repos;
    self.querySearch   = querySearch;
    self.selectedItemChange = selectedItemChange;
    self.searchTextChange   = searchTextChange;
    self.searchText

    self.items = [];
    self.total_amount = 0;
    self.total_quantity = 0;

    self.cal_total = cal_total;
    function cal_total(){
      self.total_amount = 0;
      self.total_quantity = 0;
      for (i = 0; i < purchase_goods.length; i++){

        self.total_amount += purchase_goods[i].price
        self.total_quantity += purchase_goods[i].quantity;
      }
      console.log("total");
    }

    self.submit_data = submit_data;
    function submit_data() {

      self.items = [];
      purchase_goods = [];
      self.skus = purchase_goods;
      self.total_amount = 0;
      self.total_quantity = 0;
      self.searchText = '';
      self.quantity = 0;
      manageData.prepForBroadcast("clear");
    }

    self.get_product_data = get_product_data;


    function update_search_results(filter_data, key) {
        for (i=0; i<filter_data.length; i++) {
          if(filter_data[i].SKUCode===key) {
            self.searchText = "";
            self.repeated_data = false;
            for (j=0; j<purchase_goods.length; j++) {
              if (purchase_goods[j].sku_code === key) {
                purchase_goods[j].quantity += 1;
                purchase_goods[j].price = purchase_goods[j].quantity * purchase_goods[j].unit_price
                self.repeated_data = true;
                break;
              }
            }
            if (!self.repeated_data) {
              purchase_goods.push({'name': filter_data[i].ProductDescription, 'unit_price': filter_data[i].price, 'quantity': 1, 'sku_code': filter_data[i].SKUCode, 'price': filter_data[i].price});
              break;
            }
          }
        }
    }

    function get_product_data(key) {

        if (key.length > 3) {
            var deferred = $q.defer();
            $http.get(urlService.mainUrl+'search_product_data?key='+key)
              .success( function(data) {
                self.repos = data;
                repos = data;
                return repos.map( function (repo) {
                  repo.value = repo.search.toLowerCase();
                  return repo;
                })
              }).then(function() {
                filter_data = querySearch (key);
                deferred.resolve(filter_data);
                update_search_results(filter_data, key)
                cal_total();
              })
            return deferred.promise;
        }
        return [];
    }

    self.removeProduct = removeProduct;
    function removeProduct(name) {

      for (i = 0; i < self.skus.length; i++) {

        if (name ==  self.skus[i].name) {

          self.skus.splice(i, 1);
          cal_total();
          break;
        }
      }
    }

    // Internal methods
    function querySearch (query) {
      var results = query ? self.repos.filter( createFilterFor(query) ) : self.repos,
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
    }

    var purchase_goods = [];
    self.skus = purchase_goods;
    function selectedItemChange(item) {
      if (!(typeof(item) == "undefined")) {
        update_search_results([item], item.SKUCode);
        cal_total();
        self.searchText = "";
      }
    }

    // Create filter function for a query string
    function createFilterFor(query) {
      var lowercaseQuery = angular.lowercase(query);

      return function filterFn(item) {
        return (item.value.indexOf(lowercaseQuery) >= 0);
      };

    }
});

