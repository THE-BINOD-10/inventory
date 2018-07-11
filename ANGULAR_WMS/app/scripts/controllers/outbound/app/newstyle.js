;(function(){

'use strict';

function AppNewStyle ($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {
	console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.place_order_loading = false;


} // End of funciton


// Initializing the controller to module
angular
  .module('urbanApp')
  .controller('AppNewStyle', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', AppNewStyle]);


})();