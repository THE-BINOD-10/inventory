'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockTransferShipmentCtrl',['$scope', '$http', '$state', '$compile', '$rootScope', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', '$modal', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $rootScope, Session, DTOptionsBuilder, DTColumnBuilder, Service, $modal, Data) {
    

}