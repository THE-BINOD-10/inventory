;(function(){

'use strict';

function AppNewStyle ($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {
	console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.place_order_loading = false;

  vm.main_menus = [{'name':'House Keeping', 'sub_menus':['Menu-1','Menu-2','Menu-3','Menu-4']},
  				   {'name':'Office Stationary', 'sub_menus':['Menu-1','Menu-2','Menu-3','Menu-4']},
  				   {'name':'Content Management', 'sub_menus':['Menu-1','Menu-2','Menu-3','Menu-4']},
  				   {'name':'Office Technologies', 'sub_menus':['Menu-1','Menu-2','Menu-3','Menu-4']},
  				   {'name':'Promotional Items', 'sub_menus':['Menu-1','Menu-2','Menu-3','Menu-4']},
  				   {'name':'Display Systems', 'sub_menus':['Menu-1','Menu-2','Menu-3','Menu-4']}];

} // End of funciton


// Initializing the controller to module
angular
  .module('urbanApp')
  .controller('AppNewStyle', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', AppNewStyle]);


})();