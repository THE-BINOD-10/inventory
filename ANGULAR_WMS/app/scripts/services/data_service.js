'use strict';

var app = angular.module('urbanApp')
app.service('Data',['$rootScope', '$compile','$q', '$http', '$state', '$timeout', 'Session', 'COLORS', Service]);

function Service($rootScope, $compile, $q, $http, $state, $timeout, Session, COLORS) {

  var self = this;
  self.industry_type = Session.user_profile.industry_type;

  /*** Receive PO  ***/
  self.receive_po = {
                      style_view: false
                    }

  self.payment_based_invoice = {
                                  style_view: true
                                }

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
                                                       'Reserved Quantity', 'Total Quantity', 'Open Order Quantity', 'Unit of Measurement', 'Stock Value'],
                                      'StockSummaryAlt':['SKU Class', 'Style Name', 'Brand', 'SKU Category']},
                         size_type: 'DEFAULT'
                       }
  //WareHouse stock

  self.stock_view = {
                      views: ['Available', 'Available+Intransit', 'Total'],
                      view: 'Available',
                      levels: [1,2],
                      level: 1
                    }

  self.warehouse_alternative_stock_view = {
                        views: ['Available', 'Reserved', 'Total'],
                        view: 'Available',
                        levels: [1,2],
                        level: 1
                      }

  self.warehouse_toggle_value = false;

  self.warehouse_view = self.stock_view;

  /*** Outbound **/

  //Create orders
  self.create_orders= { fields:{
                          'other':{ unit_price: true, amount: true, tax: true, total_amount: true, remarks: true },
                          'Subhas Publications': {unit_price: false, amount: false, tax: false, total_amount: false, remarks: false}
                        },
                        custom_order_data: []
                      }

  //create shipment
  self.create_shipment = {

                            alternate_view: true,
                            view: 'ShipmentPickedAlternative',
                            tb_headers: {'ShipmentPickedOrders': ['Order ID', 'SKU Code', 'Title', 'Customer ID', 'Customer Name','Address', 'Marketplace',
                                                                  'Picked Quantity'],
                                         'ShipmentPickedAlternative': ['Order ID', 'Customer ID', 'Customer Name', 'Marketplace','Address',
                                                                  'Picked Quantity', 'Total Quantity', 'Order Date']}
                         }

  self.tranfer_shipment = {
                       //alternate_view: true,
                       view: 'StockTransferShipment',
                       tb_headers: {'StockTransferShipment': ['Stock Transfer ID', 'Destination Warehouse', 'Total Quantity', 'Picked Quantity', 'Stock Transfer Date&Time']}
                                    // 'ShipmentPickedAlternative': ['Order ID', 'Customer ID', 'Customer Name', 'Marketplace',
                                    //                          'Picked Quantity', 'Total Quantity', 'Order Date']}
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
                        tb_headers: { 'CustomerOrderView': {'Customer Name': 'Customer Name', 'Order ID': 'Order ID', 'Address': 'Address', 'Market Place': 'Market Place', 'Total Quantity': 'Total Quantity', 'Shipment Date': 'Exp Delivery Date', 'Creation Date': 'Creation Date', 'Order Taken By': 'Order Taken By', 'Status': 'Status'},
                                      'CustomerCategoryView': {'Customer Name': 'Customer Name', 'Order ID': 'Order ID', 'Address': 'Address', 'Category': 'Category', 'Total Quantity': 'Total Quantity', 'Order Taken By': 'Order Taken By', 'Status': 'Status'},
                                      'SKUView': {'SKU Code': 'SKU Code', 'Title': 'Title', 'Total Quantity': 'Total Quantity'},
                                      'OrderView': {'Order ID': 'Order ID', 'Address': 'Address', 'SKU Code': 'SKU Code', 'Title': 'Title', 'Product Quantity': 'Product Quantity', 'Shipment Date': 'Exp Delivery Date', 'Order Taken By': 'Order Taken By', 'Status': 'Status'},
                                      'SellerOrderView': {'SOR ID': 'SOR ID', 'UOR ID': 'UOR ID', 'Seller Name': 'Seller Name', 'Customer Name': 'Customer Name', 'Market Place': 'Market Place', 'Total Quantity': 'Total Quantity', 'Creation Date': 'Creation Date', 'Order Taken By': 'Order Taken By', 'Status': 'Status'}
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
    if (self.industry_type == 'FMCG') {
      self.dispatch_summary_report = {

                              alternate_view: false,
                              view: 'normalView',
                              tb_headers: {'normalView': ['Order ID', 'WMS Code', 'WMS MRP', 'Child SKU', 'Child SKU MRP', 'Child SKU Weight', 'Description', 'Location', 'Quantity', 'Picked Quantity', 'Date', 'Time'],
                                           'serialView': ['Order ID', 'WMS Code', 'Description', 'Customer Name', 'Serial Number', 'Date', 'Time'],
                                           'customerView': ['Customer ID', 'Customer Name', 'WMS Code', 'Description', 'Quantity', 'Picked Quantity']}
                           }
    } else {
      self.dispatch_summary_report = {

                              alternate_view: false,
                              view: 'normalView',
                              tb_headers: {'normalView': ['Order ID', 'WMS Code', 'WMS MRP', 'Child SKU', 'Description', 'Location', 'Quantity', 'Picked Quantity', 'Date', 'Time'],
                                           'serialView': ['Order ID', 'WMS Code', 'Description', 'Customer Name', 'Serial Number', 'Date', 'Time'],
                                           'customerView': ['Customer ID', 'Customer Name', 'WMS Code', 'Description', 'Quantity', 'Picked Quantity']}
                           }
    }

    self.dispatch_summary_view_types = [{ 'name' : 'Order View', 'value' : 'normalView'}, { 'name' : 'Serial Number View', 'value' : 'serialView'}, { 'name' : 'Customer View', 'value' : 'customerView'}]

    if(Session.roles.permissions['batch_switch']) {

      self.other_view.view = 'SKUView'
    } else {

      self.other_view.view = 'OrderView'
    }

    /** customer login **/
    self.marginSKUData = {data: []};
    self.enquiry_orders = [];
    self.my_orders = [];
    self.manual_orders = [];
    self.styleId = '';
    self.styles_data = {};
    self.tot_corporates = [];
    self.shipment_number = '';
    self.categories = [];
    self.sub_categories = [];
    self.invoice_data = {};
    self.datatable = 'ReturnToVendor';
    self.seller_types = [];
    self.rtv_filters = {};
    self.receive_jo_barcodes = false;

    /** login page maintainance **/
    self.login_data = {

      state_name: '',
      login_type: '',
      customers: { sagarfab: 'user.sagarfab'},
      default: 'user.signin'
    }
}
