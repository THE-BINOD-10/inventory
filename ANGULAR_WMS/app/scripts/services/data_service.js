'use strict';

var app = angular.module('urbanApp')
app.service('Data',['$rootScope', '$compile','$q', '$http', '$state', '$timeout', 'Session', 'COLORS', Service]);

function Service($rootScope, $compile, $q, $http, $state, $timeout, Session, COLORS) {

  var self = this;
  /*** Production Data ***/

  // Receive Job Order
  self.receive_jo = {
                      sku_view: false,
                      tb_headers: {'ReceiveJOSKU': ['Job Code', 'SKU Code' , 'SKU Category', 'Creation Date', 'Receive Status'],
                                    'ReceiveJO': ['Job Code', 'Creation Date', 'Receive Status']}
                    }

  /*** Stock Locator ***/
  
  // Stock Summary

  self.stock_summary = {

                         tb_headers: ['WMS Code', 'Product Description', 'SKU Brand', 'SKU Category', 'Quantity', 'Unit of Measurement']
                       }

  /*** Outbound **/
  
  //View Orders

    //Order View
    self.order_view = {

                        tb_headers: ['Customer Name', 'Order ID', 'Category', 'Total Quantity']
                      }
}

