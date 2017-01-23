'use strict';

var app = angular.module('urbanApp')
app.service('Data',['$rootScope', '$compile','$q', '$http', '$state', '$timeout', 'Session', 'COLORS', Service]);

function Service($rootScope, $compile, $q, $http, $state, $timeout, Session, COLORS) {

  var self = this;
  /*** Production Data ***/

  // Receive Job Order
  self.receive_jo = {
                      sku_view: false,
                      tb_headers: {'ReceiveJOSKU': ['Job Code', 'SKU Code' , 'SKU Brand', 'SKU Category', 'Creation Date', 'Receive Status'],
                                    'ReceiveJO': ['Job Code', 'Creation Date', 'Receive Status']}
                    }

  /*** Stock Locator ***/

  // Stock Summary

  self.stock_summary = {

                         tb_headers: ['WMS Code', 'Product Description', 'SKU Brand', 'SKU Category', 'Quantity', 'Reserved Quantity', 'Total Quantity', 'Unit of Measurement']
                       }

  /*** Outbound **/

  //View Orders

    //Other View
    self.other_view = {

                        views: ['OrderView', 'SKUView', 'CustomerOrderView', 'CustomerCategoryView'],
                        view: 'OrderView',
                        generate_picklist_urls : { 'CustomerOrderView': 'order_category_generate_picklist/',
                                                   'CustomerCategoryView': 'order_category_generate_picklist/',
                                                   'OrderView': 'generate_picklist/',
                                                   'SKUView': 'batch_generate_picklist/'
                                                 },
                        tb_headers: { 'CustomerOrderView': ['Customer Name', 'Order ID', 'Market Place', 'Total Quantity', 'Creation Date'],
                                      'CustomerCategoryView': ['Customer Name', 'Order ID', 'Category', 'Total Quantity'],
                                      'SKUView': ['SKU Code','Title', 'Total Quantity'],
                                      'OrderView': ['Order ID', 'SKU Code', 'Title', 'Product Quantity', 'Shipment Date']
                                    },
                        dt_data: {'OrderView': {}, 'OrderCategoryView': ''}
                      }
    if(Session.roles.permissions['batch_switch']) {

      self.other_view.view = 'SKUView'
    } else {

      self.other_view.view = 'OrderView'
    }

    /** login page maintainance **/
    self.login_data = {

      state_name: '',
      login_type: '',
      customers: { sagarfab: 'user.sagarfab'},
      default: 'user.signin'
    }
}

