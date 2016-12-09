'use strict';

var app = angular.module('urbanApp')

app.config(['$httpProvider', function($httpProvider) {
    $httpProvider.defaults.withCredentials = true;
    $httpProvider.defaults.useXDomain = true;
  }])



  app.provider('myCSRF',[function(){
  var headerName = 'X-CSRFToken';
  var cookieName = 'csrftoken';
  var allowedMethods = ['GET'];

  this.setHeaderName = function(n) {
    headerName = n;
  }
  this.setCookieName = function(n) {
    cookieName = n;
  }
  this.setAllowedMethods = function(n) {
    allowedMethods = n;
  }
  this.$get = ['$cookies', function($cookies){
    return {
      'request': function(config) {
        if(allowedMethods.indexOf(config.method) === -1) {
          // do something on success
          config.headers[headerName] = $cookies[cookieName];
        }
        return config;
      }
    }
  }];
}]).config(function($httpProvider) {
  $httpProvider.interceptors.push('myCSRF');
});
