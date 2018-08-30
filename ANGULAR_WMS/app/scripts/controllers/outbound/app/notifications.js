;(function(){

'use strict';

function AppCart($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  var vm = this;
    vm.service = Service;



angular
  .module('urbanApp')
      .controller('AppCart', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout',
                  'Auth', '$stateParams', '$modal', 'Data', AppCart]);
})();
