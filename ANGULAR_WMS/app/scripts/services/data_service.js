'use strict';

var app = angular.module('urbanApp')
app.service('Data',['$rootScope', '$compile','$q', '$http', '$state', '$timeout', 'Session', 'COLORS', Service]);

function Service($rootScope, $compile, $q, $http, $state, $timeout, Session, COLORS) {

  var self = this;
  /*** Production Data ***/

  // Receive Job Order
  self.receive_jo = {
                      sku_view: false,
                      tb_headers: {'ReceiveJOSKU': ['Job Code', 'SKU Code' , 'SKU Brand', 'SKU Category', 'Creation Date', 'Receive Status', 'Quantity'],
                                    'ReceiveJO': ['Job Code', 'Creation Date', 'Receive Status', 'Quantity']
                                  }
                    }

  /*** Stock Locator ***/

  // Stock Summary

  self.stock_summary = {
                         stock_2d: false,
                         view: 'StockSummary',
                         tb_headers: {'StockSummary': ['WMS Code', 'Product Description', 'SKU Brand', 'SKU Category', 'Available Quantity',
                                                       'Reserved Quantity', 'Total Quantity', 'Unit of Measurement'],
                                      'StockSummaryAlt':['SKU Class', 'Style Name', 'Brand', 'SKU Category']},
                         size_type: 'DEFAULT'
                       }
  //WareHouse stock
  self.stock_view = {

                      views: ['Available', 'Available+Intransit', 'Total'],
                      view: 'Available'

                    }


  /*** Outbound **/

  //Create orders
  self.create_orders= { fields:{
                          'other':{ unit_price: true, amount: true, tax: true, total_amount: true, remarks: true },
                          'Subhas Publications': {unit_price: false, amount: false, tax: false, total_amount: false, remarks: false}
                        }
                      }

  //create shipment
  self.create_shipment = {

                            alternate_view: true,
                            view: 'ShipmentPickedAlternative',
                            tb_headers: {'ShipmentPickedOrders': ['Order ID', 'SKU Code', 'Title', 'Customer ID', 'Customer Name', 'Marketplace',
                                                                  'Picked Quantity'],
                                         'ShipmentPickedAlternative': ['Order ID', 'Customer ID', 'Customer Name', 'Marketplace',
                                                                  'Picked Quantity', 'Total Quantity', 'Order Date']}
                         }

  /*** Production ***/

    //RM Picklist
    self.confirm_orders = {

                            sku_view: false,
                            view: 'RawMaterialPicklist',
                            tb_headers: {'RawMaterialPicklistSKU': ['Job Code', 'SKU Code' , 'SKU Brand', 'SKU Category', 'Quantity', 'Order Type', 'Creation Date'],
                                         'RawMaterialPicklist': ['Job Code', 'Creation Date', 'Order Type', 'Quantity']}

                          }

    //Back Orders
    self.back_orders_list = {

                              toggle_switch: false,
                              view: 'ProductionBackOrders',
                              tb_headers: {'ProductionBackOrders': ['WMS Code', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity',
                                                                    'Procurement Quantity'],
                                           'ProductionBackOrdersAlt': ['Job Code', 'WMS Code', 'Ordered Quantity', 'Stock Quantity',
                                                                       'Transit Quantity', 'Procurement Quantity']}
                            }
  //View Orders

    //Other View
    self.other_view = {

                        views: ['OrderView', 'SKUView', 'CustomerOrderView', 'CustomerCategoryView', 'SellerOrderView'],
                        view: 'OrderView',
                        generate_picklist_urls : { 'CustomerOrderView': 'order_category_generate_picklist/',
                                                   'CustomerCategoryView': 'order_category_generate_picklist/',
                                                   'OrderView': 'generate_picklist/',
                                                   'SKUView': 'batch_generate_picklist/',
                                                   'SellerOrderView': 'seller_generate_picklist/'
                                                 },
                        tb_headers: { 'CustomerOrderView': ['Customer Name', 'Order ID', 'Market Place', 'Total Quantity', 'Shipment Date', 'Creation Date', 'Order Taken By', 'Status'],
                                      'CustomerCategoryView': ['Customer Name', 'Order ID', 'Category', 'Total Quantity', 'Order Taken By', 'Status'],
                                      'SKUView': ['SKU Code','Title', 'Total Quantity'],
                                      'OrderView': ['Order ID', 'SKU Code', 'Title', 'Product Quantity', 'Shipment Date', 'Order Taken By', 'Status'],
                                      'SellerOrderView': ['SOR ID', 'UOR ID', 'Seller Name', 'Customer Name', 'Market Place', 'Total Quantity', 'Creation Date', 'Order Taken By', 'Status']
                                    },
                        dt_data: {'OrderView': {}, 'OrderCategoryView': ''}
                      }

    //Custom Orders
    self.custom_orders = {
                           view:'CustomerOrders',
                           tb_headers:['Customer Name', 'Order ID', 'Total Quantity', 'Shipment Date', 'Creation Date', 'Production Unit', 'Printing Unit', 'Embroidery Unit', 'Order Taken By', 'Status']
                         }

    /*** Production ***/
    //Job Order Putaway

    self.order_putaway = {
        sku_view: false,
        tb_headers: {
                    'PutawayConfirmationSKU' : ['Job Code','SKU Code','SKU Brand','SKU Category', 'Creation Date'],
                    'PutawayConfirmation': ['Job Code', 'Creation Date'] }
    }

    //Dispatch Summary Report
    self.dispatch_summary_report = {

                            alternate_view: false,
                            view: 'normalView',
                            tb_headers: {'normalView': ['Order ID', 'WMS Code', 'Description', 'Location', 'Quantity', 'Picked Quantity', 'Date', 'Time'],
                                         'serialView': ['Order ID', 'WMS Code', 'Description', 'Customer Name', 'Serial Number', 'Date', 'Time']}
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

