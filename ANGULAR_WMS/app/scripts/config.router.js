'use strict';

var LOGIN_STATE = "user.signin",
    LOGIN_REDIRECT_STATE = "app.dashboard",
    LOGIN_REDIRECT_STATE_CUSTOMER = "user.App.Brands",
    PERMISSION_DENIED = "app.denied";

var app = angular.module('urbanApp')
  app.run(['$rootScope', '$state', '$stateParams', 'Auth', 'AUTH_EVENTS', 'Session', '$timeout',
        function ($rootScope, $state, $stateParams, Auth, AUTH_EVENTS, Session, $timeout) {
      if(Session.user_profile.user_type == "customer") {
        LOGIN_REDIRECT_STATE = LOGIN_REDIRECT_STATE_CUSTOMER;
      }
      $rootScope.$state = $state;
      $rootScope.$stateParams = $stateParams;
      $rootScope.$on('$stateChangeSuccess', function () {
        window.scrollTo(0, 0);
      });
      FastClick.attach(document.body);

      var skipAsync = false;
      var states = ['user.signin', 'user.signup', 'user.sagarfab', 'user.create']

            $rootScope.$on("$stateChangeStart", function (event, next, toPrms, from, fromPrms) {

              var prms = toPrms;
              if(next.name == from.name) {

                return;
              } else if ((states.indexOf(next.name) > -1) && Session.userName) {

                if(confirm("Do you really want to logout from mieone?")) {
                  Auth.logout();
                } else {
                  event.preventDefault();
                  $timeout(function(){$(".preloader").removeClass("ng-show").addClass("ng-hide");}, 2000);
                }
              }

              if (skipAsync) {

                skipAsync = false;
                return;
              }

              if (states.indexOf(next.name) == -1) {

                event.preventDefault();

                ;(function (thisNext) {

                  Auth.status().then(function (resp) {

                    if (Session.roles.permissions["setup_status"] && thisNext.name.indexOf("Register") == -1) {
                      $state.go("app.Register");
                      return;
                    } else if((Session.user_profile.user_type == "customer") && (thisNext.name.indexOf("App") == -1)) {

                       $state.go(LOGIN_REDIRECT_STATE_CUSTOMER,  {"location": "replace"})
                       return;
                    } else if (typeof(next.permission) == "string") {

                      var perm_list = next.permission.split("&");
                      var check_status = false;
                      for(var i=0; i < perm_list.length; i++) {

                        if(!(Session.check_permission(perm_list[i]))) {
                          check_status = true;
                          break;
                        }
                      }
                      if(check_status) {
                        $state.go(PERMISSION_DENIED, {"location": "replace"});
                        return;
                      }
                    }

                    if (thisNext.name !== next.name) {

                      return;
                    }

                    if (resp == 'Fail') {

                      $rootScope.$broadcast(AUTH_EVENTS.unAuthorized);
                      return;
                    }

                    skipAsync = true;
                    $state.go(next.name, prms);
                  });
                }(next));
              }

            });

            $rootScope.$on(AUTH_EVENTS.loginSuccess, function () {

              if (Session.user_profile.user_type == "customer") {
                $state.go(LOGIN_REDIRECT_STATE_CUSTOMER, {"location": "replace"});
              } else {
                $state.go(LOGIN_REDIRECT_STATE, {"location": "replace"});
              }
            });

            function goToLogin () {

              $state.go(LOGIN_STATE, {"location": "replace"});
            }

            $rootScope.$on(AUTH_EVENTS.unAuthorized, goToLogin);
            $rootScope.$on(AUTH_EVENTS.logoutSuccess, goToLogin);

        },
    ])
  .config(['$stateProvider', '$urlRouterProvider',
    function ($stateProvider, $urlRouterProvider) {

      // For unmatched routes
      $urlRouterProvider.otherwise('/');

      // Application routes
      $stateProvider
        .state('app', {
          abstract: true,
          templateUrl: 'views/common/layout.html',
        })


      .state('app.dashboard', {
        url: '/',
        templateUrl: 'views/dashboard/dashboard.html',
        authRequired: true,
        resolve: {
          deps: ['$ocLazyLoad', function ($ocLazyLoad) {
            return $ocLazyLoad.load([
              {
                insertBefore: '#load_styles_before',
                files: [
                                'styles/climacons-font.css',
                                'vendor/rickshaw/rickshaw.min.css'
                            ]
                        },
              {
                serie: true,
                files: [
                                'vendor/d3/d3.min.js',
                                'vendor/rickshaw/rickshaw.min.js',
                                'scripts/extentions/plugins/time/jstz.min.js'
                            ]
                        },
              {
                  name: 'angular-flot',
                  files: [
                                'vendor/angular-flot/angular-flot.js'
                            ]
                        }]).then(function () {
              return $ocLazyLoad.load('scripts/controllers/dashboard/dashboard.js');
            });
                    }]
        },
        data: {
          title: 'Dashboard',
        }
      })


      // Master Routes
      .state('app.masters', {
          template: '<div ui-view></div>',
          abstract: true,
          url: '/Masters',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                { 
                  name: 'angularFileUpload',
                  files: [
                                'vendor/angular-file-upload/angular-file-upload.min.js'
                            ]
              }]);   
                    }]
          },
        })
        .state('app.masters.SKUMaster', {
          url: '/SKUMaster',
          permission: 'add_skumaster',
          templateUrl: 'views/masters/sku_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/skutable.js');
                    }]
          },
          data: {
            title: 'SKU Master',
          }
        })
          .state('app.masters.SKUMaster.update', {
            url: '/SKU',
            templateUrl: 'views/masters/toggles/sku_update.html'
          })
          .state('app.masters.SKUMaster.barcode', {
            url: '/Barcode',
            templateUrl: 'views/masters/toggles/barcode.html'
          })
        .state('app.masters.ImageBulkUpload', {
          url: '/ImageBulkUpload',
          templateUrl: 'views/masters/image_bulk_upload.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/image_bulk_upload.js');
                    }]
          },
          data: {
            title: 'Image Upload',
          }
        })
        .state('app.masters.LocationMaster', {
          url: '/LocationMaster',
          permission: 'add_locationmaster',
          templateUrl: 'views/masters/location_master.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/locationMaster.js');
              }]
          },
          data: {
            title: 'Location Master',
          }
        })
          .state('app.masters.LocationMaster.Zone', {
            url: '/Zone',
            templateUrl: 'views/masters/toggles/add_zone.html'
          })
          .state('app.masters.LocationMaster.Location', {
            url: '/Location',
            templateUrl: 'views/masters/toggles/add_location.html'
          })
        .state('app.masters.supplierSKUMapping', {
          url: '/SupplierSKUMapping',
          permission: 'add_skusupplier',
          templateUrl: 'views/masters/supplier_sku_mapping_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/supplierSKU.js');
                    }]
          },
          data: {
            title: 'Supplier-SKU Mapping',
          }
        })
          .state('app.masters.supplierSKUMapping.mapping', {
             url: '/supplierSKU',
             templateUrl: 'views/masters/toggles/supplier_sku_update.html'
           })
        .state('app.masters.SupplierMaster', {
          url: '/SupplierMaster',
          permission: 'add_suppliermaster',
          templateUrl: 'views/masters/supplier_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/suppliertable.js');
                    }]
          },
          data: {
            title: 'Supplier Master',
          }
        })
          .state('app.masters.SupplierMaster.supplier', {
            url: '/supplier',
            templateUrl: 'views/masters/toggles/supplier_update.html'
          })
        .state('app.masters.CustomerMaster', {
          url: '/CustomerMaster',
          permission: 'add_customermaster',
          templateUrl: 'views/masters/customer_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/customerMaster.js');
                    }]
          },
          data: {
            title: 'Customer Master',
          }
        })
          .state('app.masters.CustomerMaster.customer', {
             url: '/customer',
             templateUrl: 'views/masters/toggles/customer_update.html'
           })
        .state('app.masters.Customer-SKUMapping', {
          url: '/Customer-SKUMapping',
          permission: 'add_customersku&pos_switch',
          templateUrl: 'views/masters/customer_sku_mapping_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/CustomerSKUMapping.js');
                    }]
          },
          data: {
            title: 'Customer-SKU Mapping',
          }
        })
          .state('app.masters.Customer-SKUMapping.CustomerSKU', {
             url: '/CustomerSKU',
             templateUrl: 'views/masters/toggles/customer_sku_update.html'
           })
        .state('app.masters.BOMMaster', {
          url: '/BOMMaster',
          permission: 'add_bommaster',
          templateUrl: 'views/masters/BOM_datatable.html',
          permission: 'production_switch',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/BOMMaster.js');
                    }]
          },
          data: {
            title: 'BOM Master',
          }
        })
          .state('app.masters.BOMMaster.BOM', {
             url: '/BOM',
             templateUrl: 'views/masters/toggles/BOM_update.html'
           })
        .state('app.masters.WarehouseMaster', {
          url: '/WarehouseMaster',
          permission: 'multi_warehouse',
          templateUrl: 'views/masters/warehouse_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/WarehouseMaster.js');
                    }]
          },
          data: {
            title: 'Warehouse Master',
          }
        })
          .state('app.masters.WarehouseMaster.Warehouse', {
             url: '/Warehouse',
             templateUrl: 'views/masters/toggles/warehouse_update.html'
           })
        .state('app.masters.VendorMaster', {
          url: '/VendorMaster',
          permission: 'add_vendormaster&production_switch',
          templateUrl: 'views/masters/vendor_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/VendorMaster.js');
                    }]
          },
          data: {
            title: 'Vendor Master',
          }
        })
           .state('app.masters.VendorMaster.Vendor', {
             url: '/Vendor',
             templateUrl: 'views/masters/toggles/vendor_update.html'
           })
        .state('app.masters.DiscountMaster', {
          url: '/DiscountMaster',
          permission: 'pos_switch',
          templateUrl: 'views/masters/discount_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/DiscountMaster.js');
                    }]
          },
          data: {
            title: 'Discount Master',
          }
        })
          .state('app.masters.DiscountMaster.Discount', {
             url: '/Discount',
             templateUrl: 'views/masters/toggles/discount_update.html'
           })
        .state('app.masters.CustomSKUMaster', {
          url: '/CustomSKUMaster',
          permission: 'productproperties',
          templateUrl: 'views/masters/custom_sku_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/customSKUMaster.js');
                    }]
          },
          data: {
            title: 'Custom SKU Template',
          }
        })
          .state('app.masters.CustomSKUMaster.AddCustomSKU', {
             url: '/AddCustomSKU',
             templateUrl: 'views/masters/toggles/add_custom_sku.html'
           })
        .state('app.masters.SizeMaster', {
          url: '/SizeMaster',
          permission: 'add_sizemaster',
          templateUrl: 'views/masters/size_master.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/size_master.js');
                    }]
          },
          data: {
            title: 'Size Master',
          }
        })
          .state('app.masters.SizeMaster.AddSize', {
             url: '/Size',
             templateUrl: 'views/masters/toggles/size_update.html'
           })
        .state('app.masters.PricingMaster', {
          url: '/PricingMaster',
          permission: 'add_pricemaster',
          templateUrl: 'views/masters/pricing_master.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/pricing_master.js');
                    }]
          },
          data: {
            title: 'Pricing Master',
          }
        })
          .state('app.masters.PricingMaster.Add', {
             url: '/Price',
             templateUrl: 'views/masters/toggles/price_update.html'
           })
        .state('app.masters.SellerMaster', {
          url: '/SellerMaster',
          permission: 'add_sellermaster',
          templateUrl: 'views/masters/seller_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/sellerMaster.js');
                    }]
          },
          data: {
            title: 'Seller Master',
          }
        })
          .state('app.masters.SellerMaster.seller', {
             url: '/seller',
             templateUrl: 'views/masters/toggles/seller_update.html'
           })
        .state('app.masters.SellerMarginMapping', {
          url: '/SellerMarginMapping',
          permission: 'add_sellermaster',
          templateUrl: 'views/masters/seller_margin_mapping.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/sellerMarginMapping.js');
                    }]
          },
          data: {
            title: 'Seller Margin Mapping',
          }
        })
          .state('app.masters.SellerMarginMapping.Mapping', {
             url: '/Mapping',
             templateUrl: 'views/masters/toggles/margin_mapping_update.html'
           })

      // Inbound routes
      .state('app.inbound', {
          template: '<div ui-view></div>',
          abstract: true,
          url: '/inbound',
        })
        .state('app.inbound.RaisePo', {
          url: '/RaisePO',
          permission: 'add_openpo',
          templateUrl: 'views/inbound/raise_po.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/inbound/raise_po/raise_purchase_order.js'
                ]).then( function() { 
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/raise_po/raise_stock_transfer.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Raise PO',
          }
        })
          .state('app.inbound.RaisePo.PurchaseOrder', {
          url: '/PurchaseOrder',
          permission: 'add_openpo',
          templateUrl: 'views/inbound/toggle/raise_purchase.html'
          })
          .state('app.inbound.RaisePo.StockTransfer', {
          url: '/StockTransfer',
          permission: 'add_openpo',
          templateUrl: 'views/inbound/toggle/raise_stock.html'
          })
          .state('app.inbound.RaisePo.PurchaseOrderPrint', {
          url: '/PurchaseOrderPrint',
          permission: 'add_openpo',
          telmplateUrl: 'views/inbound/print/po_print.html'
          })
          .state('app.inbound.RaisePo.barcode', {
            url: '/Barcode',
            templateUrl: 'views/masters/toggles/barcode.html'
          })


        .state('app.inbound.RevceivePo', {
          url: '/ReceivePO',
          permission: 'add_purchaseorder',
          templateUrl: 'views/inbound/receive_po.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/inbound/receive_po.js');
              }]
          },
          data: {
            title: 'Receive PO',
          }
        })
          .state('app.inbound.RevceivePo.GRN', {
          url: '/GRN',
          permission: 'add_purchaseorder',
          templateUrl: 'views/inbound/toggle/generate_grn.html'
          })
          .state('app.inbound.RevceivePo.Vendor', {
          url: '/Vendor',
          permission: 'add_purchaseorder',
          templateUrl: 'views/inbound/toggle/recieve_vendor.html'
          })
          .state('app.inbound.RevceivePo.barcode', {
            url: '/Barcode',
            templateUrl: 'views/masters/toggles/barcode.html'
          })
          .state('app.inbound.RevceivePo.qc_detail', {
            url: '/QC_Detail',
            templateUrl: 'views/inbound/toggle/grn_qc.html'
          })
        .state('app.inbound.QualityCheck', {
          url: '/QualityCheck',
          permission: 'add_qualitycheck',
          templateUrl: 'views/inbound/quality_check.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/inbound/quality_check.js');
              }]
          },
          data: {
            title: 'Quality Check',
          }
        })
          .state('app.inbound.QualityCheck.qc', {
            url: '/QC',
            permission: 'add_qualitycheck',
            templateUrl: 'views/inbound/toggle/qc.html'
          })
          .state('app.inbound.QualityCheck.qc_detail', {
            url: '/QC_Detail',
            permission: 'add_qualitycheck',
            templateUrl: 'views/inbound/toggle/qc_detail.html'
          })
        .state('app.inbound.PutAwayConfirmation', {
          url: '/PutawayConfirmation',
          permission: 'add_polocation',
          templateUrl: 'views/inbound/putaway_confirmation.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/inbound/po_putaway.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/returns_putaway.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/pull_to_locate.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Putaway Confirmation',
          }
        })
          .state('app.inbound.PutAwayConfirmation.confirmation', {
            url: '/Confirmation',
            permission: 'add_polocation',
            templateUrl: 'views/inbound/toggle/putaway_confirm.html'
          })
        .state('app.inbound.SalesReturns', {
          url: '/SalesReturns',
          permission: 'add_orderreturns',
          templateUrl: 'views/inbound/sales_returns.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/inbound/sales_returns.js');
              }]
          },
          data: {
            title: 'Sales Returns',
          }
        })
          .state('app.inbound.SalesReturns.ScanReturns', {
            url: '/ScanReturns',
            permission: 'add_orderreturns',
            templateUrl: 'views/inbound/toggle/scan_returns.html'
          })
          .state('app.inbound.SalesReturns.barcode', {
            url: '/Barcode',
            templateUrl: 'views/masters/toggles/barcode.html'
          })
        .state('app.inbound.SellerInvoice', {
          url: '/SellerInvoices',
          templateUrl: 'views/inbound/seller_invoice.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/inbound/seller_invoice.js');
              }]
          },
          data: {
            title: 'Seller Invoices',
          }
        })
          .state('app.inbound.SellerInvoice.Invoice', {
            url: '/Invoice',
            templateUrl: 'views/inbound/print/seller_invoice.html'
          })

      // Production routes
      .state('app.production', {
          template: '<div ui-view></div>',
          abstract: true,
          url: '/production',
        })
        .state('app.production.RaiseJO', {
          url: '/RaiseJO',
          permission: 'add_jomaterial&production_switch',
          templateUrl: 'views/production/raise_jo.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/production/raise_jo/raise_jo.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/production/raise_jo/raise_rwo.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Raise JO',
          }
        })
          .state('app.production.RaiseJO.JO', {
            url: '/JO',
            permission: 'add_jomaterial&production_switch',
            templateUrl: 'views/production/toggle/update_jo.html'
          })
          .state('app.production.RaiseJO.RWO', {
            url: '/RWO',
            permission: 'add_jomaterial&production_switch',
            templateUrl: 'views/production/toggle/update_rwo.html'
          })
          .state('app.production.RaiseJO.JobOrderPrint', {
            url: '/JobOrderPrint',
            permission: 'add_jomaterial&production_switch',
            templateUrl: 'views/production/print/job_order_print.html'
          })
        .state('app.production.RMPicklist', {
          url: '/RMPicklist',
          permission: 'add_materialpicklist&production_switch',
          templateUrl: 'views/production/rm_picklist.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/production/rm_picklist/rm_picklist.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/production/rm_picklist/picklist_generated.js'
                  ])
                });
              }]
          },
          data: {
            title: 'RM Picklist',
          }
        })
          .state('app.production.RMPicklist.ConfirmedJO', {
            url: '/ConfirmedJO',
            permission: 'add_materialpicklist&production_switch',
            templateUrl: 'views/production/toggle/confirmed_jo.html'
          })
          .state('app.production.RMPicklist.RawMaterialPicklist', {
            url: '/RawMaterialPicklist',
            permission: 'add_materialpicklist&production_switch',
            templateUrl: 'views/production/toggle/raw_material_picklist.html'
          })
        .state('app.production.ReveiveJO', {
          url: '/ReceiveJO',
          permission: 'add_joborder&production_switch',
          templateUrl: 'views/production/receive_jo.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/production/receive_jo.js');
              }]
          },
          data: {
            title: 'Receive JO',
          }
        })
          .state('app.production.ReveiveJO.ReceiveJobOrder', {
            url: '/ReceiveJobOrder',
            permission: 'add_joborder&production_switch',
            templateUrl: 'views/production/toggle/receive_job_order.html'
          })
          .state('app.production.ReveiveJO.Print', {
            url: '/Print',
            permission: 'add_joborder&production_switch',
            templateUrl: 'views/production/print/job_order_sheet.html'
          })
        .state('app.production.JobOrderPutaway', {
          url: '/JobOrderPutaway',
          permission: 'add_rmlocation&production_switch',
          templateUrl: 'views/production/jo_putaway.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/production/jo_putaway.js');
              }]
          },
          data: {
            title: 'Job Order Putaway',
          }
        })
          .state('app.production.JobOrderPutaway.JOPutaway', {
            url: '/JOPutaway',
            permission: 'add_rmlocation&production_switch',
            templateUrl: 'views/production/toggle/job_order_putaway.html'
          })
        .state('app.production.BackOrders', {
          url: '/BackOrders',
          templateUrl: 'views/production/back_orders.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/production/back_orders.js');
              }]
          },
          data: {
            title: 'Back Orders',
          }
        })
          .state('app.production.BackOrders.PO', {
            url: '/BackOrderPO',
            templateUrl: 'views/outbound/toggle/backorder_po.html'
          })
          .state('app.outbound.BackOrders.ST', {
            url: '/ST',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/toggle/create_stock_transfer.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/pop_js/stock_transfer.js');
              }]
            },
          })
          .state('app.production.BackOrders.RWO', {
            url: '/BackOrderRWO',
            templateUrl: 'views/production/toggle/update_rwo.html'
          })
      // Stock Location routes
      .state('app.stockLocator', {
          template: '<div ui-view></div>',
          abstract: true,
          url: '/stockLocator',
        })
        .state('app.stockLocator.StockSummary', {
          url: '/StockSummary',
          templateUrl: 'views/stockLocator/stock_summary.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/stock_summary.js');
              }]
          },
          data: {
            title: 'Stock Summary',
          }
        })
          .state('app.stockLocator.StockSummary.Detail', {
            url: '/Detail',
            templateUrl: 'views/stockLocator/toggles/detail.html'
          })
        .state('app.stockLocator.WarehousesStock', {
          url: '/WarehousesStock',
          templateUrl: 'views/stockLocator/warehouses_stock.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/warehouses_stock.js');
              }]
          },
          data: {
            title: 'Warehouses Stock',
          }
        })
        .state('app.stockLocator.StockDetail', {
          url: '/StockDetail',
          permission: 'add_stockdetail',
          templateUrl: 'views/stockLocator/stock_detail.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/stock_detail.js');
              }]
          },
          data: {
            title: 'Stock Detail',
          }
        })
        .state('app.stockLocator.VendorStock', {
          url: '/VendorStock',
          permission: 'add_vendorstock&production_switch',
          templateUrl: 'views/stockLocator/vendor_stock.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/vendor_stock.js');
              }]
          },
          data: {
            title: 'Vendor Stock',
          }
        })
        .state('app.stockLocator.CycleCount', {
          url: '/CycleCount',
          permission: 'add_cyclecount',
          templateUrl: 'views/stockLocator/cycle_count/cycle_count.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/stockLocator/cycle_count/generate_cc.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/stockLocator/cycle_count/confirm_cc.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/stockLocator/cycle_count/reconfirm_cc.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Cycle Count',
          }
        })
          .state('app.stockLocator.CycleCount.Generate', {
            url: '/Generate',
            permission: 'add_cyclecount',
            templateUrl: 'views/stockLocator/toggles/cycle_tg.html'
          })
          .state('app.stockLocator.CycleCount.ConfirmCycle', {
            url: '/ConfirmCycle',
            permission: 'add_cyclecount',
            templateUrl: 'views/stockLocator/toggles/cycle_tg.html'
          })
        .state('app.stockLocator.MoveInventory', {
          url: '/MoveInventory',
          permission: 'add_inventoryadjustment',
          templateUrl: 'views/stockLocator/move_inventory.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/move_inventory.js');
              }]
          },
          data: {
            title: 'Move Inventory',
          }
        })
          .state('app.stockLocator.MoveInventory.Inventory', {
            url: '/Inventory',
            permission: 'add_inventoryadjustment',
            templateUrl: 'views/stockLocator/toggles/mv_inventory_tg.html'
          })
          .state('app.stockLocator.MoveInventory.IMEI', {
            url: '/IMEI',
            permission: 'add_inventoryadjustment',
            templateUrl: 'views/stockLocator/toggles/imei.html'
          })
        .state('app.stockLocator.InventoryAdjustment', {
          url: '/InventoryAdjustment',
          permission: 'add_inventoryadjustment',
          templateUrl: 'views/stockLocator/inventory_adjustment.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/inventory_adjustment.js');
              }]
          },
          data: {
            title: 'Inventory Adjustment',
          }
        })
          .state('app.stockLocator.InventoryAdjustment.Adjustment', {
            url: '/Adjustment',
            permission: 'add_inventoryadjustment',
            templateUrl: 'views/stockLocator/toggles/inventory_adj_tg.html'
          })
        .state('app.stockLocator.SellerStock', {
          url: '/SellerStock',
          templateUrl: 'views/stockLocator/seller_stock.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/seller_stock.js');
              }]
          },
          data: {
            title: 'Seller Stock',
          }
        })
          .state('app.stockLocator.SellerStock.StockDetails', {
            url: '/StockDetails',
            templateUrl: 'views/stockLocator/toggles/stock_details.html'
          })

      // Outbound routes
      .state('app.outbound', {
          template: '<div ui-view></div>',
          abstract: true,
          url: '/outbound',
        })
        .state('app.outbound.CreateOrders', {
          url: '/CreateOrders',
          permission: 'add_orderdetail',
          templateUrl: 'views/outbound/create_orders.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/create_orders/create_orders.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/create_orders/create_stock_orders.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Create Orders',
          }
        })
          .state('app.outbound.CreateOrders.CreateCustomSku', {
            url: '/CreateCustomSku',
            templateUrl: '/views/outbound/toggle/create_custom_sku.html'
          })
          .state('app.outbound.CreateOrders.customer', {
             url: '/customer',
             templateUrl: 'views/outbound/toggle/customer.html'
           })
        .state('app.outbound.ViewOrders', {
          url: '/ViewOrders',
          permission: 'add_picklist',
          templateUrl: 'views/outbound/view_orders.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                {
                  serie: true,
                  files: [
                             'scripts/controllers/outbound/create_orders/create_orders.js',
                             'scripts/controllers/outbound/create_orders/create_stock_orders.js',
                             'scripts/controllers/outbound/view_orders/custom_orders.js'
                            ]
                        }]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/view_orders/stock_transfer_orders.js'
                  ])
                }).then(function () {

                return $ocLazyLoad.load('scripts/controllers/outbound/view_orders/orders.js');
              });
                    }]
          },
          data: {
            title: 'View Orders',
          }
        })
          .state('app.outbound.ViewOrders.Picklist', {
            url: '/Picklist',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/toggle/batch_tg.html'
          })
          .state('app.outbound.ViewOrders.Transfer', {
            url: '/Transfer',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/toggle/transfer_tg.html'
          })
          .state('app.outbound.ViewOrders.CreateOrder', {
            url: '/CreateOrder',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/toggle/create_order.html'
          })
          .state('app.outbound.ViewOrders.CreateTransfer', {
            url: '/CreateTransfer',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/toggle/create_stock_transfer.html'
          })
          .state('app.outbound.ViewOrders.JO', {
            url: '/RaiseJO',
            permission: 'add_picklist&batch_switch',
            templateUrl: 'views/outbound/toggle/backorder_jo.html'
          })
          .state('app.outbound.ViewOrders.PO', {
            url: '/RaisePO',
            permission: 'add_picklist&batch_switch',
            templateUrl: 'views/outbound/toggle/backorder_po.html'
          })
          .state('app.outbound.ViewOrders.OrderDetails', {
            url: '/OrderDetails',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/toggle/view_order_details.html'
          })
          .state('app.outbound.ViewOrders.CustomOrderDetails', {
            url: '/CustomOrderDetails',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/toggle/custom_order_detail.html'
          })
          .state('app.outbound.ViewOrders.GenerateInvoice', {
            url: '/Invoice',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/print/generate_invoice.html'
          })
          .state('app.outbound.ViewOrders.DetailGenerateInvoice', {
            url: '/DetailInvoice',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/print/detail_generate_inv.html'
          })
          .state('app.outbound.ViewOrders.ST', {
            url: '/ST',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/toggle/create_stock_transfer.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/pop_js/stock_transfer.js');
              }]
            },
          })
        .state('app.outbound.PullConfirmation', {
          url: '/PullConfirmation',
          permission: 'add_picklistlocation',
          templateUrl: 'views/outbound/pull_confirmation.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/pull_confirm/open_orders.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/pull_confirm/picked_orders.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/pull_confirm/batch_picked.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Pull Confirmation',
          }
        })
          .state('app.outbound.PullConfirmation.Open', {
            url: '/Open',
            permission: 'add_picklistlocation',
            templateUrl: 'views/outbound/toggle/open_tg.html'
          })
          .state('app.outbound.PullConfirmation.Picked', {
            url: '/Picked',
            permission: 'add_picklistlocation',
            templateUrl: 'views/outbound/toggle/picked_tg.html'
          })
          .state('app.outbound.PullConfirmation.GenerateInvoice', {
            url: '/Invoice',
            permission: 'add_picklistlocation',
            templateUrl: 'views/outbound/print/generate_invoice.html'
          })
          .state('app.outbound.PullConfirmation.barcode', {
            url: '/Barcode',
            templateUrl: 'views/masters/toggles/barcode.html'
          })
          .state('app.outbound.PullConfirmation.DetailGenerateInvoice', {
            url: '/DetailInvoice',
            permission: 'add_picklist',
            templateUrl: 'views/outbound/print/detail_generate_inv.html'
          })
        .state('app.outbound.ShipmentInfo', {
          url: '/ShipmentInfo',
          permission: 'add_shipmentinfo',
          templateUrl: 'views/outbound/shipment_info.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/shipment_info/create_shipment.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/shipment_info/view_shipment.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Shipment Info',
          }
        })
          .state('app.outbound.ShipmentInfo.Shipment', {
            url: '/Shipment',
            permission: 'add_shipmentinfo',
            templateUrl: 'views/outbound/toggle/ship_tg.html'
          })
          .state('app.outbound.ShipmentInfo.ConfirmShipment', {
            url: '/ConfirmShipment',
            permission: 'add_shipmentinfo',
            templateUrl: 'views/outbound/toggle/confirm_ship_tg.html'
          })
        .state('app.outbound.BackOrders', {
          url: '/BackOrders',
          templateUrl: 'views/outbound/back_orders.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/back_orders.js');
              }]
          },
          data: {
            title: 'Back Orders',
          }
        })
          .state('app.outbound.BackOrders.PO', {
            url: '/BackOrderPO',
            templateUrl: 'views/outbound/toggle/backorder_po.html'
          })
          .state('app.outbound.BackOrders.JO', {
            url: '/BackOrderJO',
            templateUrl: 'views/outbound/toggle/backorder_jo.html'
          })
        .state('app.outbound.CreateStockTransfer', {
          url: '/CreateStockTransfer',
          permission: 'multi_warehouse',
          templateUrl: 'views/outbound/create_stock_transfer.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/create_orders/create_stock_orders.js'
                  ])
              }]
          },
          data: {
            title: 'Create Orders',
          }
        })
        .state('app.outbound.CustomerInvoices', {
          url: '/CustomerInvoices',
          templateUrl: 'views/outbound/customer_invoices.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/customer_invoices.js'
                  ])
              }]
          },
          data: {
            title: 'Customer Invoices',
          }
        })
         .state('app.outbound.CustomerInvoices.InvoiceM', {
            url: '/InvoiceM',
            templateUrl: 'views/outbound/print/customer_invoice.html'
         })
         .state('app.outbound.CustomerInvoices.InvoiceN', {
            url: '/InvoiceN',
            templateUrl: 'views/outbound/print/generate_invoice.html'
          })
          .state('app.outbound.CustomerInvoices.InvoiceD', {
            url: '/InvoiceD',
            templateUrl: 'views/outbound/print/detail_generate_inv.html'
          })
      // Upload route
      .state('app.uploads', {
          url: '/uploads',
          templateUrl: 'views/uploads/uploads.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/uploads/uploads.js');
              }]
          },
          data: {
            title: 'Uploads'
          }
        })
      
      // Track Orders
      .state('app.TrackOrders', {
          url: '/TrackOrders',
          templateUrl: 'views/track_orders/track_orders.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/track_orders/orders.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/track_orders/purchase_orders.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Track Orders'
          }
        })

      // Track Orders
      .state('app.PaymentTracker', {
          url: '/PaymentTracker',
          templateUrl: 'views/payment_tracker/payment_tracker.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/payment_tracker/payment_tracker.js'
                ]);
              }]
          },
          data: {
            title: 'Pending Payment Tracker'
          }
        })

      // Orders Sync Issues
      .state('app.OrdersSyncIssues', {
          url: '/OrdersSyncIssues',
          templateUrl: 'views/orders_sync_issues/orders_sync_issues.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load([
                    'scripts/controllers/orders_sync_issues/orders_sync_issues.js'
                  ]);
                }]
          },
          data: {
              title: 'Orders Sync Issues'
          }
      })
      .state('app.OrdersSyncIssues.ModifyIssues', {
            url: '/ModifyOrdersSync',
            templateUrl: 'views/orders_sync_issues/toggle/modify_orders_sync.html',
      })
      // Reports routes
      .state('app.reports', {
          template: '<div ui-view></div>',
          abstract: true,
          url: '/reports',
        })
        .state('app.reports.SKUList', {
          url: '/SKUList',
          templateUrl: 'views/reports/sku_list.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/sku_list.js');
              }]
          },
          data: {
            title: 'SKU List',
          }
        })
        .state('app.reports.LocationWiseFilter', {
          url: '/LocationWiseFilter',
          templateUrl: 'views/reports/location_wise_filter.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/location_wise_filter.js');
              }]
          },
          data: {
            title: 'Location Wise Filter',
          }   
        })
        .state('app.reports.GoodsReceiptNote', {
          url: '/GoodsReceiptNote',
          templateUrl: 'views/reports/goods_receipt_note.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/goods_receipt_note.js');
              }]
          },
          data: {
            title: 'Goods Receipt Note',
          }   
        })
          .state('app.reports.GoodsReceiptNote.PurchaseOrder', {
            url: '/GoodsReceiptNote',
            templateUrl: 'views/reports/toggles/purchase_order.html',
          })
        .state('app.reports.ReceiptSummary', {
          url: '/ReceiptSummary',
          templateUrl: 'views/reports/receipt_summary.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/receipt_summary.js');
              }]
          },
          data: {
            title: 'Receipt Summary',
          }   
        })
        .state('app.reports.DispatchSummaryReport', {
          url: '/DispatchSummary',
          templateUrl: 'views/reports/dispatch_summary.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/dispatch_summary.js');
              }]
          },
          data: {
            title: 'Dispatch Summary Report',
          }   
        })
        .state('app.reports.SKUWiseStock', {
          url: '/SKUWiseStock',
          templateUrl: 'views/reports/sku_wise_stock.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/sku_wise_stock.js');
              }]
          },
          data: {
            title: 'SKU Wise Stock',
          }   
        })
        .state('app.reports.SKUWisePurchaseOrders', {
          url: '/SKUWisePurchaseOrders',
          templateUrl: 'views/reports/sku_wise_purchase_orders.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/sku_wise_purchase_orders.js');
              }]
          },
          data: {
            title: 'SKU Wise Purchase Orders',
          }   
        })
        .state('app.reports.SupplierWisePOs', {
          url: '/SupplierWisePOs',
          templateUrl: 'views/reports/supplier_wise_pos.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/supplier_wise_pos.js');
              }]
          },
          data: {
            title: 'Supplier Wise POs',
          }   
        })
        .state('app.reports.SalesReturnReport', {
          url: '/SalesReturnReport',
          permission: 'add_orderreturns',
          templateUrl: 'views/reports/sales_return.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/sales_return.js');
              }]
          },
          data: {
            title: 'Sales Return Report',
          }
        })
        .state('app.reports.InventoryAdjustment', {
          url: '/InventoryAdjustment',
          templateUrl: 'views/reports/inventory_adjustment.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/inventory_adjustment.js');
              }]
          },
          data: {
            title: 'Inventory Adjustment',
          }
        })
        .state('app.reports.InventoryAging', {
          url: '/InventoryAging',
          templateUrl: 'views/reports/inventory_aging.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/inventory_aging.js');
              }]
          },
          data: {
            title: 'Inventory Aging Report',
          }
        })
        .state('app.reports.StockSummaryReport', {
          url: '/StockSummary',
          templateUrl: 'views/reports/production_stages.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/production_stages.js');
              }]
          },
          data: {
            title: 'Stock Summary Report',
          }
        })
        .state('app.reports.DailyProductionReport', {
          url: '/DailyProduction',
          templateUrl: 'views/reports/daily_production.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/daily_production.js');
              }]
          },
          data: {
            title: 'Daily Production Report',
          }
        })
        .state('app.reports.OrderSummaryReport', {
          url: '/OrderSummary',
          templateUrl: 'views/reports/order_summary.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/order_summary.js');
              }]
          },
          data: {
            title: 'Order Summary Report',
          }
        })
        .state('app.reports.JOStatusReport', {
          url: '/JOStatus',
          templateUrl: 'views/reports/jo_status.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/jo_status.js');
              }]
          },
          data: {
            title: 'JO Status Report',
          }
        })
        .state('app.reports.OpenJOReport', {
          url: '/OpenJO',
          templateUrl: 'views/reports/open_jo.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/open_jo.js');
              }]
          },
          data: {
            title: 'Open JO Report',
          }
        })
        .state('app.reports.SellerInvoiceDetails', {
          url: '/SellerInvoiceDetails',
          templateUrl: 'views/reports/seller_invoice_details.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/seller_invoice_details.js');
              }]
          },
          data: {
            title: 'Seller Invoice Details',
          }
        })

      // configuration route
      .state('app.configurations', {
          url: '/configurations',
          templateUrl: 'views/configurations.html',
          authRequired: true,
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                {
                  insertBefore: '#load_styles_before',
                  files: [
                                'scripts/extentions/plugins/multiselect/multi-select.css'
                            ]
                        },
                {
                  serie: true,
                  files: [
                                'scripts/extentions/plugins/multiselect/jquery.multi-select.js'
                            ]
                        }]).then(function () {
                return $ocLazyLoad.load('scripts/controllers/configs/configurations.js');
              });   
                    }]
          },
          data: {
            title: 'Configurations'
          }
      })

      //Channels
      .state('app.channels', {
          url: '/Channels',
          templateUrl : 'views/channels/channels.html',
          resolve:{
                deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load(

                        [{
                         serie: true,
                         files: [
                                'vendor/jquery.ui/ui/core.js',
                                'vendor/jquery.ui/ui/widget.js',
                                'vendor/jquery.ui/ui/mouse.js',
                                'vendor/jquery.ui/ui/slider.js',
                                'scripts/extentions/plugins/slider/rzslider.css',
                                'scripts/extentions/plugins/slider/rzslider.js',
                                //'scripts/controllers/alert.js'
                                //'scripts/extentions/noty-defaults.js',
                                'vendor/noty/js/noty/packaged/jquery.noty.packaged.min.js',
                                'scripts/extentions/noty-defaults.js',
                                //'scripts/controllers/notifications.js',
                                //'vendor/checkbo/src/0.1.4/css/checkBo.min.css',
                                //'vendor/checkbo/src/0.1.4/js/checkBo.min.js',
                                //'scripts/controllers/bootstrap.ui.js'
                                ]
                        }]

                ).then(function () {
                return $ocLazyLoad.load('scripts/controllers/masters/one_channel.js');
              });
                    }]
                },
             data: {
                        title: 'Channels',
                }
          })
	.state('app.channels.add_flipkart', {
          url: '/flipkart/add',
          templateUrl: 'views/channels/add_flipkart.html'
        })
        .state('app.channels.add_amazon', {
          url: '/amazon/add',
          templateUrl: 'views/channels/add_amazon.html'
        })
        .state('app.channels.update_flipkart', {
          url: '/flipkart/update',
          templateUrl: 'views/channels/add_flipkart.html'
        })
        .state('app.channels.update_amazon', {
          url: '/amazon/update',
          templateUrl: 'views/channels/add_amazon.html'
        })

      // Tally Configuration
      .state('app.tally', {
        url: '/Tally',
        templateUrl: 'views/tally/tally_config.html',
        permission: 'tally_config',
        resolve: {
          deps: ['$ocLazyLoad', function ($ocLazyLoad) {
            return $ocLazyLoad.load('scripts/controllers/tally/tally_config.js');
          }]
        },
        data: {
          title: 'Tally Configuration',
        }
      })

      // ManageUsers route
      .state('app.ManageUsers', {
          url: '/ManageUsers',
          permission: 'is_staff',
          templateUrl: 'views/manage_users/manage_users.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                { 
                  serie: true,
                  files: [   
                             'scripts/controllers/manage_users/manage_groups.js'
                            ]
                        }]).then(function () {
                return $ocLazyLoad.load('scripts/controllers/manage_users/manage_users.js');
              });   
                    }]
          },
          data: {
            title: 'Manage Users'
          }
        })   
          .state('app.ManageUsers.UpdateUser', {
            url: '/UpdateUser',
            templateUrl: 'views/manage_users/update_user.html'
          })
          .state('app.ManageUsers.AddUser', {
            url: '/AddUser',
            templateUrl: 'views/manage_users/add_user.html'
          })
          .state('app.ManageUsers.AddGroup', {
            url: '/AddGroup',
            templateUrl: 'views/manage_users/add_group.html'
          })
          .state('app.ManageUsers.ChangePassword', {
            url: '/ChangePassword',
            templateUrl: 'views/manage_users/change_password.html'
          })
          .state('app.ManageUsers.GroupDetails', {
            url: '/GroupDetails',
            templateUrl: 'views/manage_users/group_details.html'
          })

      //register
      .state('app.Register', {
          url: '/Register',
          templateUrl: 'views/register/register.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/register.js');
                    }]
          },
          data: {
            title: 'Registration'
          }
        })
        .state('app.Register.One', {
          url: '/1',
          templateUrl: 'views/register/step_one.html'
        })
        .state('app.Register.Two', {
          url: '/2',
          templateUrl: 'views/register/step_two.html'
        })
        .state('app.Register.Three', {
          url: '/3',
          templateUrl: 'views/register/step_three.html'
        })
        .state('app.Register.Completed', {
          url: '/Completed',
          templateUrl: 'views/register/completed.html'
        })
        

      //Customer page
      .state('user.Customer', {
          url: '/Customer',
          templateUrl: 'views/outbound/create_orders.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/create_orders/create_orders.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/create_orders/create_stock_orders.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Customer',
            appClasses: 'bg-white usersession',
            contentClasses: 'full-height'
          }
        })

      // User route 
      .state('user', {
          templateUrl: 'views/common/session.html',
        })
        .state('user.signin', {
          url: '/login',
          templateUrl: 'own/views/signin.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/session.js');
                    }]
          },
          data: {
            appClasses: 'bg-white usersession',
            contentClasses: 'full-height'
          }
        })
        .state('user.forgot', {
          url: '/forgot',
          templateUrl: 'views/extras-forgot.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/session.js');
                    }]
          },
          data: {
            appClasses: 'bg-white usersession',
            contentClasses: 'full-height'
          }
        })
        .state('user.signup', {
          url: '/signup',
          templateUrl: 'views/signup.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/signup.js');
                    }]
          },
          data: {
            appClasses: 'bg-white usersession',
            contentClasses: 'full-height'
          }
        })
        .state('user.create', {
          url: '/createAccount',
          templateUrl: 'views/create_account.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/create_account.js');
                    }]
          },
          data: {
            appClasses: 'bg-white usersession',
            contentClasses: 'full-height'
          }
        })
        .state('user.sagarfab', {
          url: '/sagarfab_login',
          templateUrl: 'views/customers/sagarfab_login.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/session.js');
                    }]
          },
          data: {
            appClasses: 'bg-white usersession',
            contentClasses: 'full-height'
          }
        })
        .state('user.App', {
          url: '/App',
          templateUrl: 'views/outbound/app/create_orders.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/outbound/app/create_orders.js');
                    }]
          },
	      data: {
            appClasses: 'bg-white usersession',
            contentClasses: 'full-height'
          }
        })
          .state('user.App.Brands', {
            url: '/Brands',
            templateUrl: 'views/outbound/app/create_orders/details.html'
          })
          .state('user.App.Products', {
            url: '/Products',
            templateUrl: 'views/outbound/app/create_orders/catlog.html'
          })
          .state('user.App.Style', {
            url: '/Style?styleId',
            templateUrl: 'views/outbound/app/create_orders/style.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/style.js');
              }]
            }
          })
          .state('user.App.Cart', {
            url: '/Cart',
            templateUrl: 'views/outbound/app/create_orders/order.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/cart.js');
              }]
            }
          })
          .state('user.App.MyOrders', {
            url: '/MyOrders',
            templateUrl: 'views/outbound/app/create_orders/your_orders.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/my_order.js');
              }]
            }
          })
          .state('user.App.OrderDetails', {
            url: '/OrderDetails?orderId',
            templateUrl: 'views/outbound/app/create_orders/order_detail.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/order_details.js');
              }]
            }
          })
        .state('app.denied', {
          url: '/PermissionDenied',
          templateUrl: 'views/permission_denied.html',
          data: {
            title: 'PERMISSION DENIED'
          }
        })

        }
    ])

app.config(['$httpProvider', function($httpProvider) {
    $httpProvider.defaults.withCredentials = true;
  }])

  app.provider('myCSRF',[function(){
  var headerName = 'X-CSRFToken';
  var cookieName = 'csrftoken';
  var allowedMethods = ['GET', 'POST'];

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
