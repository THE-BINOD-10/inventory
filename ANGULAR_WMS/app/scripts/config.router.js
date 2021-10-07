'use strict';

var LOGIN_STATE = "user.signin",
    LOGIN_REDIRECT_STATE = "app.dashboard",
    LOGIN_REDIRECT_STATE_CUSTOMER = "user.App.Brands",
    LOGIN_REDIRECT_STATE_ANT_CUSTOMER = "user.App.newStyle",
    PERMISSION_DENIED = "app.denied";

var app = angular.module('urbanApp')
  app.run(['$rootScope', '$state', '$stateParams', 'Auth', 'AUTH_EVENTS', 'Session', '$timeout', '$http',
        function ($rootScope, $state, $stateParams, Auth, AUTH_EVENTS, Session, $timeout, $http) {
      if(Session.user_profile.request_user_type == "customer") {
        if (Session.roles.permissions.is_portal_lite) {
          LOGIN_REDIRECT_STATE = LOGIN_REDIRECT_STATE_ANT_CUSTOMER;
        } else {
          LOGIN_REDIRECT_STATE = LOGIN_REDIRECT_STATE_CUSTOMER;
        }
      }
     $rootScope.$redirect = '';
     $rootScope.$current_pr ='';
     $rootScope.$current_po = '';
     $rootScope.$current_raise_pr = '';
     $rootScope.$current_path = '';
     $rootScope.$state = $state;
     $rootScope.$stateParams = $stateParams;
     $rootScope.$on('$stateChangeSuccess', function () {
       window.scrollTo(0, 0);
     });
     $rootScope.$location_href = location.href;
     FastClick.attach(document.body);
     if(window.location.href.includes('notifications/email')){
       var request_hash_code = window.location.href.split('notifications/email/')[1];
       var tmp_route = request_hash_code.split('?hash_code')[0];
       if(request_hash_code.includes('hash_code')) {
         Session.unset();
         $rootScope.$redirect = tmp_route;
         var data = request_hash_code.split(tmp_route)[1];
         var loader_header = ''
         if (tmp_route == 'pending_pr_request') {
            loader_header = 'PR'
         } else if (tmp_route == 'pendingPREnquiry') {
            loader_header = 'Pending Enquiry'
         } else {
            loader_header = 'PO'
         }
         swal2({
           title: 'Redirecting to Validate '+loader_header,
           text: 'User Authentication in Progress..',
           imageUrl: 'images/default_loader.gif',
           imageWidth: 150,
           imageHeight: 150,
           imageAlt: 'Custom image',
           showConfirmButton:false,
         })
         $http.get(Session.url + tmp_route +'/'+data).then(function (resp) {
          resp = resp.data
          if (localStorage.getItem('username') == null || resp.data.userName != localStorage.getItem('username')) {
            if (tmp_route == 'pending_pr_request') {
              localStorage.setItem('current_pr', JSON.stringify(resp.aaData['aaData'][0]));
            } else if (tmp_route == 'pendingPREnquiry') {
              localStorage.setItem('current_pr_enq', JSON.stringify(resp.aaData['aaData'][0]));
            } else {
              localStorage.setItem('current_po', JSON.stringify(resp.aaData['aaData'][0]));
            }
            $rootScope.$current_path = resp['pr_data']['path'];
            localStorage.setItem('username', resp.data.userName);
            localStorage.setItem('route', $rootScope.$current_path);
            localStorage.setItem('route_type', tmp_route);
            swal2.close();
            Auth.logout();
          } else if (resp) {
            $rootScope.$current_path = resp['pr_data']['path'];
            if (tmp_route == 'pending_pr_request') {
              $rootScope.$current_pr = resp.aaData['aaData'][0]
            } else if (tmp_route == 'pendingPREnquiry') {
              $rootScope.$current_pr_enq = ''
            } else {
              $rootScope.$current_po = resp.aaData['aaData'][0]
            }
            localStorage.clear();
            localStorage.setItem('username', resp.data.userName);
            if (resp.message != "Fail") {
              Session.set(resp.data)
              swal2.close()
              $state.go($rootScope.$current_path);
            }
          }
       });
      }
     } else {
        var skipAsync = false;
        var states = ['user.signin', 'user.signup', 'user.sagarfab', 'user.create', 'user.smlogin', 'user.marshlogin',
         'user.Corp Attire', 'user.forgot']
          $rootScope.$on("$stateChangeStart", function (event, next, toPrms, from, fromPrms) {
              var prms = toPrms;
              if(next.name == from.name) {
                return;
              } else if ((states.indexOf(next.name) > -1) && Session.userName) {
                if ($rootScope.$redirect) {
                  $state.go("app.masters.SKUMaster");
                } else {
                 if(confirm("Do you really want to logout from mieone?")) {
                   Auth.logout();
                 } else {
                   event.preventDefault();
                   $timeout(function(){$(".preloader").removeClass("ng-show").addClass("ng-hide");}, 2000);
                 }
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
                    if (localStorage.getItem('route') != null && localStorage.getItem('username') == Session.userName) {
                      if (localStorage.getItem('route_type') == 'pending_pr_request') {
                        $rootScope.$current_pr = JSON.parse(localStorage.getItem('current_pr'));
                        localStorage.removeItem('current_pr');
                      } else if (localStorage.getItem('route_type') == 'pendingPREnquiry') {
                        $rootScope.$current_pr_enq = ''
                        localStorage.removeItem('current_pr_enq');
                      } else {
                        $rootScope.$current_po = JSON.parse(localStorage.getItem('current_po'));
                        localStorage.removeItem('current_po');
                      }
                      localStorage.removeItem('route_type');
                      var current_redirect = localStorage.getItem('route');
                      localStorage.removeItem('route');
                      $state.go(current_redirect);
                      return;
                    }
                    if (Session.roles.permissions["setup_status"] && thisNext.name.indexOf("Register") == -1) {
                      $state.go("app.Register");
                      return;
                    } else if((Session.user_profile.request_user_type == "customer") && (thisNext.name.indexOf("App") == -1)) {

                        if (Session.roles.permissions.is_portal_lite) {

                          $state.go(LOGIN_REDIRECT_STATE_ANT_CUSTOMER,  {"location": "replace"})
                        } else {

                          $state.go(LOGIN_REDIRECT_STATE_CUSTOMER,  {"location": "replace"})
                        }
                        return;
                    } else if (typeof(next.permission) == "string") {

                      var split_variable = '|';
                      var check_status = true;
                      if(next.permission.indexOf("&")>0){
                        split_variable = '&';
                        check_status = false;
                      }
                      var perm_list = next.permission.split(split_variable);
                      for(var i=0; i < perm_list.length; i++) {

                        if(!(Session.check_permission(perm_list[i])) && split_variable == '&') {
                          check_status = true;
                          break;
                        }
                        else if((Session.check_permission(perm_list[i])) && split_variable == '|') {
                          check_status = false;
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

              if (Session.user_profile.request_user_type == "customer") {
                $state.go(LOGIN_REDIRECT_STATE_CUSTOMER, {"location": "replace"});

              } else if (Session.user_profile.request_user_type == "supplier"){
                $state.go("app.PurchaseOrder", {"location": "replace"});
              } else {
                $state.go(LOGIN_REDIRECT_STATE, {"location": "replace"});
              }
            });

            function goToLogin () {

              $state.go(LOGIN_STATE, {"location": "replace"});
            }

            $rootScope.$on(AUTH_EVENTS.unAuthorized, goToLogin);
            $rootScope.$on(AUTH_EVENTS.logoutSuccess, goToLogin);
          }
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

      //notifications router
      .state('app.notifications', {
        url: '/notifications',
        templateUrl: 'views/notifications/notifications.html',
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
              return $ocLazyLoad.load('scripts/controllers/notifications/notifications.js');
            });
                    }]
        },
        data: {
          title: 'Notifications',
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
          permission:'view_skumaster',
          templateUrl: 'views/masters/sku_master/sku_master_mapping.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load(['scripts/controllers/masters/skutable.js'
                ]).then(function(){
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/toggle/attributes.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/masters/skuMappingDOA.js'
                  ])
                });
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
        .state('app.masters.SKUMaster.Mapping', {
            url: '/SKUMapping',
            templateUrl: 'views/masters/sku_master/sku_mapping_doa_update.html'
          })
        .state('app.masters.AssetMaster', {
          url: '/AssetMaster',
          permission: 'view_assetmaster',
          templateUrl: 'views/masters/asset_master/asset_master_mapping.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/asset_master_table.js'
                ]).then(function(){
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/asset_master_doa.js'
                  ])
                })
             }]
          },
          data: {
            title: 'Asset Master',
          }
        })
          .state('app.masters.AssetMaster.update', {
            url: '/Asset',
            templateUrl: 'views/masters/toggles/asset_update.html'
          })
          .state('app.masters.AssetMaster.Mapping', {
            url: '/SKUMapping',
            templateUrl: 'views/masters/asset_master/asset_master_doa_update.html'
            })

          .state('app.masters.TestMaster', {
          url: '/TestMaster',
          permission: 'add_assetmaster',
          templateUrl: 'views/masters/test_master.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load(['scripts/controllers/masters/test_master.js'
                ])
             }]
          },
          data: {
            title: 'Test Master',
          }
        })
          .state('app.masters.TestMaster.update', {
            url: '/Test',
            templateUrl: 'views/masters/toggles/test_master_update.html'
          })
        .state('app.masters.ServiceMaster', {
          url: '/ServiceMaster',
          permission: 'view_servicemaster',
          templateUrl: 'views/masters/service_master/service_master_mapping.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/service_master_table.js'
                ]).then(function(){
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/service_master_doa.js'
                  ])
                })
             }]
          },
          data: {
            title: 'Service Master',
          }
        })
          .state('app.masters.ServiceMaster.update', {
            url: '/Service',
            templateUrl: 'views/masters/toggles/service_update.html'
          })
          .state('app.masters.ServiceMaster.Mapping', {
            url: '/Service',
            templateUrl: 'views/masters/service_master/service_master_doa_update.html'
          })
          
        .state('app.masters.OtherItemsMaster', {
          url: '/OtherItemsMaster',
          permission: 'view_otheritemsmaster',
          templateUrl: 'views/masters/otheritems_master/otheritems_master_mapping.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/otheritems_master_table.js'
                ]).then(function(){
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/otheritems_master_doa.js'
                  ])
                })
             }]
          },
          data: {
            title: 'OtherItems Master',
          }
        })
          .state('app.masters.OtherItemsMaster.update', {
            url: '/OtherItems',
            templateUrl: 'views/masters/toggles/otheritems_update.html'
          })
          .state('app.masters.OtherItemsMaster.Mapping', {
            url: '/OtherItems',
            templateUrl: 'views/masters/otheritems_master/otheritems_doa_update.html'
          })
        .state('app.masters.LocationMaster', {
          url: '/LocationMaster',
          permission: 'add_locationmaster',
          templateUrl: 'views/masters/location_master_datatable.html',
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
          .state('app.masters.LocationMaster.SubZoneMapping', {
            url: '/Location',
            templateUrl: 'views/masters/toggles/add_sub_zone_mapping.html'
          })
        .state('app.masters.sourceSKUMapping', {
          url: '/SourceSKUMapping',
          permission: 'view_skusupplier',
          templateUrl: 'views/masters/source_sku_mapping.html',

          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/masters/source_sku_mapping/supplierSKU.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/masters/source_sku_mapping/warehouseSKU.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/masters/source_sku_mapping/supplierSKUAttribute.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/masters/source_sku_mapping/supplierSKUDOA.js'
                  ])
                });
              }]
          },

          data: {
            title: 'Source-SKU Mapping',
          }
        })
          .state('app.masters.sourceSKUMapping.mapping', {
             url: '/supplierSKU',
             templateUrl: 'views/masters/toggles/supplier_sku_update.html'
           })
          .state('app.masters.sourceSKUMapping.wh_mapping', {
             url: '/warehouseSKU',
             templateUrl: 'views/masters/toggles/warehouse_sku_update.html'
           })
          .state('app.masters.sourceSKUMapping.sku_attributes', {
             url: '/supplierSKUAttributes',
             templateUrl: 'views/masters/toggles/supplier_sku_attributes.html'
           })
        .state('app.masters.SupplierMaster', {
          url: '/SupplierMaster',
          permission: 'view_suppliermaster',
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
        .state('app.masters.CorporateMaster', {
          url: '/CorporateMaster',
          permission: 'add_corporatemaster',
          templateUrl: 'views/masters/corporate_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/CorporateMaster.js');
                    }]
          },
          data: {
            title: 'Corporate Master',
          }
        })
        .state('app.masters.CorporateMaster.corporate', {
             url: '/corporate',
             templateUrl: 'views/masters/toggles/corporate_update.html'
           })
        .state('app.masters.CorporateMapping', {
          url: '/CorporateMapping',
          permission: 'add_corpresellermapping',
          templateUrl: 'views/masters/corporate_mapping.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/CorporateMapping.js');
                    }]
          },
          data: {
            title: 'Reseller Corporate Mapping',
          }
        })
        .state('app.masters.CustomerMaster', {
          url: '/CustomerMaster',
          permission: 'view_customermaster',
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

           .state('app.masters.VehicleMaster', {
          url: '/VehicleMaster',
          permission: 'show_vehiclemaster',
          templateUrl: 'views/masters/vehicle_datatable.html',
          resolve: {
//            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
//                return $ocLazyLoad.load('scripts/controllers/masters/vehicleMaster.js');
//                    }]
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load(['scripts/controllers/masters/vehicleMaster.js'
                ]).then(function(){
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/toggle/attributes.js'
                  ])
                })
              }]
          },
          data: {
            title: 'Vehicle Master',
          }
        })
          .state('app.masters.VehicleMaster.vehicle', {
             url: '/vehicle',
             templateUrl: 'views/masters/toggles/vehicle_update.html'
           })

           .state('app.masters.SkuPackMaster', {
             url: '/SkuPackMaster',
             // permission: 'sku_pack_config',
             templateUrl: 'views/masters/sku_pack_datatable.html',
             resolve: {
               deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                   return $ocLazyLoad.load('scripts/controllers/masters/skuPackMaster.js');
                       }]
             },
             data: {
               title: 'Sku Pack Master',
             }
           })
             .state('app.masters.SkuPackMaster.skupack', {
                url: '/skupack',
                templateUrl: 'views/masters/toggles/sku_pack_update.html'
              })

              .state('app.masters.InventoryNorm', {
                url: '/InventoryNorm',
                // permission: 'sku_pack_config',
                templateUrl: 'views/masters/replenushment_datatable.html',
                resolve: {
                  deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                      return $ocLazyLoad.load('scripts/controllers/masters/Replenushment.js');
                          }]
                },
                data: {
                  title: 'Inventory Norm Master',
                }
              })
                .state('app.masters.InventoryNorm.update', {
                   url: '/replenushmentupdate',
                   templateUrl: 'views/masters/toggles/replenushment_update.html'
                 })


        .state('app.masters.Customer-SKUMapping', {
          url: '/Customer-SKUMapping',
          permission: 'add_customersku',
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

        .state('app.masters.CompanyMaster', {
          url: '/CompanyMaster',
          permission: 'add_customersku',
          templateUrl: 'views/masters/company_master.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/CompanyMaster.js');
                    }]
          },
          data: {
            title: 'Company Master',
          }
        })
          .state('app.masters.CompanyMaster.Company', {
             url: '/Company',
             templateUrl: 'views/masters/toggles/company_master_update.html'
           })
        .state('app.masters.BOMMaster', {
          url: '/BOMMaster',
          permission: 'add_bommaster',
          templateUrl: 'views/masters/BOM_datatable.html',
          //permission: 'production_switch',
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
          permission: 'add_productproperties',
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
          permission: 'view_pricemaster',
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
        .state('app.masters.NetworkMaster', {
          url: '/NetworkMaster',
          permission: 'add_networkmaster',
          templateUrl: 'views/masters/network_master.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/network_master.js');
                    }]
          },
          data: {
            title: 'Network Master',
          }
        })
        .state('app.masters.NetworkMaster.Add', {
             url: '/Network',
             templateUrl: 'views/masters/toggles/network_update.html'
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
        .state('app.masters.TaxMaster', {
          url: '/TaxMaster',
          permission: 'add_taxmaster',
          templateUrl: 'views/masters/tax_master.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/tax_master.js');
                    }]
          },
          data: {
            title: 'Tax Master',
          }
        })
        .state('app.masters.TandCMaster', {
          url: '/TandCMaster',
          permission: 'add_tandcmaster',
          templateUrl: 'views/masters/TandCMaster.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/TandCMaster.js');
                    }]
          },
          data: {
            title: 'T&C Master',
          }
        })
        .state('app.masters.StaffMaster', {
          url: '/StaffMaster',
          // permission: 'add_staffmaster',
          templateUrl: 'views/masters/SatffMaster.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/StaffMaster.js');
                    }]
          },
          data: {
            title: 'Staff Master',
          }
        })
        .state('app.masters.StaffMaster.Staff', {
             url: '/Staff',
             templateUrl: 'views/masters/toggles/staff_update.html'
        })
        .state('app.masters.PurchaseApproval', {
          url: '/PurchaseApproval',
          // permission: 'add_staffmaster',
          templateUrl: 'views/masters/PurchaseApproval.html',
                    resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/masters/purchase_approvals/pr_approvals.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/masters/purchase_approvals/po_approvals.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Purchase Approval Matrix',
          }
        })
        .state('app.masters.PurchaseApproval.updateApproval', {
             url: '/updateApproaval',
             templateUrl: 'views/masters/toggles/approval_update.html'
        })
        .state('app.masters.NotificationMaster', {
          url: '/NotificationMaster',
          // permission: 'add_staffmaster',
          templateUrl: 'views/masters/NotificationMaster.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/NotificationMaster.js');
                    }]
          },
          data: {
            title: 'Notification Master',
          }
        })
        .state('app.masters.ClusterSkuMaster', {
          url: '/ClusterSkuMaster',
          permission: 'add_clusterskumapping',
          templateUrl: 'views/masters/cluster_sku_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/masters/clusterskutable.js');
                    }]
          },
          data: {
            title: 'Cluster Sku Master',
          }
        })
        .state('app.masters.MachineMaster', {
          url: '/MachineMaster',
          permission: 'add_machinemaster',
          templateUrl: 'views/masters/machine_master.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load(['scripts/controllers/masters/machinemaster.js'
                ]).then(function(){
                return $ocLazyLoad.load([
                    'scripts/controllers/masters/toggle/attributes.js'
                  ])
                })
             }]
          },
          data: {
            title: 'Machine Master',
          }
        })
        .state('app.masters.MachineMaster.machine', {
            url: '/machine',
            templateUrl: 'views/masters/toggles/machine_update.html'
          })
      //PR PO Migrations
      .state('app.masters.PR_PO_Migrations', {
        url: '/PR_PO_Migrations',
        templateUrl: 'views/masters/pr_po_migrations.html',
        resolve: {
          deps: ['$ocLazyLoad', function ($ocLazyLoad) {
            return $ocLazyLoad.load('scripts/controllers/masters/pr_po_migrations.js');
                  }]
        },
        data: {
          title: 'PR PO Migrations'
        }
      })
      // Inbound routes
      .state('app.inbound.MaterialRequest', {
        url: '/MaterialRequest',
        templateUrl: 'views/inbound/main_material_request.html',
        resolve: {
          deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                'scripts/controllers/inbound/material_request.js'
              ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/pending_material_request.js'
                ])
              })
          }]
        },
        data: {
          title: 'Material Request',
        }
      })
      .state('app.inbound.MaterialRequest.DetailMR', {
         url: '/DetailMR',
         templateUrl: 'views/inbound/toggle/detailed_mr_view.html'
       })
      .state('app.inbound.TransferOrder', {
        url: '/TransferOrder',
        permission: 'multi_warehouse',
        // permission: 'add_openst',
        templateUrl: 'views/inbound/main_transfer_order.html',
        resolve: {
          deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                'scripts/controllers/inbound/raise_po/raise_stock_transfer.js'
              ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/raise_inter_st.js'
                ])
              })
          }]
        },
        data: {
          title: 'Transfer Order',
        }
      })
      .state('app.inbound.TransferOrder.StockTransfer', {
        url: '/StockTransfer',
        templateUrl: 'views/inbound/toggle/raise_stock.html'
      })
      .state('app.inbound', {
          template: '<div ui-view></div>',
          abstract: true,
          url: '/inbound',
        })
        .state('app.inbound.RaisePr', {
          url: '/RaisePR',
          permission: 'add_pendingpr|change_pendingpr|view_pendingpr',
          templateUrl: 'views/inbound/raise_pr.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/inbound/raise_pr/raise_purchase_request.js'
                ]).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/raise_pr/pending_for_approval_pr.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/raise_pr/approved_purchase_requests.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/pending_pr_enquiries.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/raise_pr/cancelled_rejected.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/raise_pr/pr_converted_to_po.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Purchase Request',
          }
        })
        .state('app.inbound.RaisePr.OpenPr', {
          url: '/PurchaseRequest',
          templateUrl: 'views/inbound/toggle/raise_pr.html'
          })
        .state('app.inbound.RaisePr.PurchaseOrder', {
          url: '/PurchaseOrder',
          templateUrl: 'views/inbound/toggle/raise_purchase.html'
          })
        .state('app.inbound.RaisePr.PurchaseRequest', {
          url: '/RaisePurchaseRequest',
          templateUrl: 'views/inbound/toggle/raise_pr.html'
          })
          .state('app.inbound.RaisePr.ApprovePurchaseRequest', {
          url: '/ApprovePR',
          templateUrl: 'views/inbound/toggle/approve_pr.html'
          })
          .state('app.inbound.RaisePr.SavedPurchaseRequest', {
          url: '/SavedPR',
          templateUrl: 'views/inbound/toggle/saved_pr.html'
          })
          .state('app.inbound.RaisePr.ConvertPRtoPO', {
          url: '/ConverPRtoPO',
          // templateUrl: 'views/inbound/toggle/convert_pr_to_po.html'
          templateUrl: 'views/inbound/toggle/approve_pr.html'
          })
          .state('app.inbound.RaisePr.PRemptyPreview', {
          url: '/ConverPRtoPO',
          templateUrl: 'views/inbound/toggle/pr_consolidated_preview.html'
          })
          .state('app.inbound.RaisePr.submitResponseToEnquiry', {
          url: '/submitEnquiryResponse',
          templateUrl: 'views/inbound/toggle/enquiry_response.html'
          })

        .state('app.inbound.RaisePo', {
          url: '/RaisePO',
          permission: 'add_openpo|change_openpo|add_intransitorders|add_pendingpo|change_pendingpo|view_pendingpo',
          templateUrl: 'views/inbound/raise_po.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/inbound/raise_po/raise_purchase_order.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/raise_po/raise_stock_transfer.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/raise_po/raise_intransit_orders.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/raise_po/repeat_purchase_order.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/raise_pending_purchase_order.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/pending_po_enquiries.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/inbound/cancelled_rejected_pos.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Purchase Order',
          }
        })
          .state('app.inbound.RaisePo.PurchaseOrder', {
          url: '/PurchaseOrder',
          templateUrl: 'views/inbound/toggle/raise_purchase.html'
          })
          .state('app.inbound.RaisePo.StockTransfer', {
          url: '/StockTransfer',
          templateUrl: 'views/inbound/toggle/raise_stock.html'
          })
          .state('app.inbound.RaisePo.PurchaseOrderPrint', {
          url: '/PurchaseOrderPrint',
          telmplateUrl: 'views/inbound/print/po_print.html'
          })
          .state('app.inbound.RaisePo.barcode', {
            url: '/Barcode',
            templateUrl: 'views/masters/toggles/barcode.html'
          })
          .state('app.inbound.RaisePo.PurchaseRequest', {
          url: '/PendingForApprovalPurchaseOrder',
          templateUrl: 'views/inbound/toggle/raise_pending_purchase.html'
          })
          .state('app.inbound.RaisePo.ApprovePurchaseRequest', {
          url: '/ApprovePendingPO',
          templateUrl: 'views/inbound/toggle/approve_pending_purchase.html'
          })
          .state('app.inbound.RaisePo.SavedPurchaseRequest', {
          url: '/SavedPendingPO',
          templateUrl: 'views/inbound/toggle/saved_pending_purchase.html'
          })
          // .state('app.inbound.RaisePo.pendingPOEnquiries', {
          // url: '/pendingPOEnquiries',
          // templateUrl: 'views/inbound/toggle/saved_pending_purchase.html'
          // })
          .state('app.inbound.RaisePo.submitResponseToEnquiry', {
          url: '/submitEnquiryResponse',
          templateUrl: 'views/inbound/toggle/enquiry_response.html'
          })


        .state('app.inbound.RevceivePo', {
          url: '/ReceivePO',
          permission: 'add_purchaseorder|change_mastersdoa|change_pocreditnote',
          templateUrl: 'views/inbound/receive_po.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                'scripts/controllers/outbound/pop_js/custom_order_details.js'
              ]).then(function() {
                return $ocLazyLoad.load([
                  'scripts/controllers/inbound/receive_po.js'
                ])
              }).then(function() {
                return $ocLazyLoad.load([
                  'scripts/controllers/inbound/receive_po_doa.js'
                ])
              }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/credit_note.js'
                ])
              });
            }]
          },
          data: {
            title: 'Receive PO',
          }
        })
          .state('app.inbound.RevceivePo.GRN', {
          url: '/GRN',
          templateUrl: 'views/inbound/toggle/generate_grn.html'
          })
          .state('app.inbound.RevceivePo.Vendor', {
          url: '/Vendor',
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
          .state('app.inbound.RevceivePo.CN', {
          url: '/CN',
          templateUrl: 'views/inbound/toggle/credit_nt.html'
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
            templateUrl: 'views/inbound/toggle/qc.html'
          })

          .state('app.inbound.QualityCheck.qc_print', {
             url: '/QcPrint',
             templateUrl: 'views/inbound/toggle/qc_print_toggle.html'
           })

          .state('app.inbound.QualityCheck.qc_detail', {
            url: '/QC_Detail',
            templateUrl: 'views/inbound/toggle/qc_detail.html'
          })

          .state('app.inbound.PrimarySegregation', {
          url: '/PrimarySegregation',
          permission: 'add_purchaseorder',
          templateUrl: 'views/inbound/primary_segregation.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/primary_segregation.js'
                  ]);
              }]
          },
          data: {
            title: 'Primary Segregation',
          }
        })
        .state('app.inbound.PrimarySegregation.AddSegregation', {
          url: '/AddSegregation',
          templateUrl: 'views/inbound/toggle/add_segregation.html'
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
            templateUrl: 'views/inbound/toggle/putaway_confirm.html'
          })
          .state('app.stockLocator.StockDetail.batch_detail', {
            url: '/Confirmation',
            templateUrl: 'views/stockLocator/toggles/batch_details.html'
          })
        .state('app.inbound.rtv', {
          url: '/rtv',
          // permission: 'add_polocation',
          templateUrl: 'views/inbound/total_rtvs.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/inbound/rtv.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/created_rtv.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Return to Vendor',
          }
        })
        .state('app.inbound.rtv.details', {
            url: '/details',
            templateUrl: 'views/inbound/toggle/rtv_details.html'
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
            templateUrl: 'views/inbound/toggle/scan_returns.html'
          })
          .state('app.inbound.SalesReturns.ScanReturnsPrint', {
            url: '/ScanReturnsPrint',
            templateUrl: 'views/inbound/toggle/scan_return_print.html'
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
            templateUrl: 'views/inbound/print/seller_inv.html'
          })
          .state('app.inbound.SellerInvoice.InvoiceE', {
            url: '/InvoiceE',
            templateUrl: 'views/outbound/print/empty_invoice.html'

          })

        .state('app.inbound.SupplierInvoice', {
          url: '/SupplierInvoices',
          templateUrl: 'views/inbound/supplier_invoices/supplier_invoices_main.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                    'scripts/controllers/inbound/supplier_invoices_main.js'
                ]).then( function() {
                    return $ocLazyLoad.load([
                        'scripts/controllers/inbound/supplier_invoices/po_challan.js'
                    ])
                }).then(function() {
                    return $ocLazyLoad.load([
                        'scripts/controllers/inbound/supplier_invoices/supplier_invoices.js'
                    ])
                });
            }]
          },
          data: {
            title: 'Supplier Invoice',
          }
        })
        .state('app.inbound.GrnEdit', {
          url: '/GrnEdit',
          templateUrl: 'views/inbound/grn_edit.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                    'scripts/controllers/inbound/grn_edit.js'
                ])
            }]
          },
          data: {
            title: 'GRN Edit',
          }
        })
        .state('app.inbound.SupplierInvoice.InvoiceM', {
            url: '/InvoiceM',
            templateUrl: 'views/inbound/print/supplier_inv.html'
         })
         .state('app.inbound.SupplierInvoice.InvoiceN', {
            url: '/InvoiceN',
            templateUrl: 'views/inbound/print/generate_inv.html',
          })
         .state('app.inbound.SupplierInvoice.InvoiceE', {
            url: '/InvoiceE',
            templateUrl: 'views/inbound/print/empty_invoice.html'
          })
          .state('app.inbound.SupplierInvoice.InvoiceD', {
            url: '/InvoiceD',
            templateUrl: 'views/inbound/print/d_generate_inv.html'
          })

        .state('app.inbound.AutoBackOrders', {
          url: '/AutoBackOrders?state',
          params: {
            state: 'orders',
          },
          templateUrl: 'views/inbound/auto_back_orders.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/pop_js/enquiry_details.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/app/my_order.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Auto Back Orders',
          }
        })
        .state('app.inbound.GrnEdit.GrnEditPopup', {
          url: '/GrnEditPopup',
          templateUrl: 'views/inbound/toggle/grn_edit_popup.html'
        })
        .state('app.inbound.MaterialPlanning', {
          url: '/MaterialPlanning',
          permission: 'change_replenushmentmaster',
          templateUrl: 'views/inbound/material_planning/material_planning_main.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                    'scripts/controllers/inbound/material_planning/material_planning.js'
                ]).then( function() {
                    return $ocLazyLoad.load([
                        'scripts/controllers/inbound/material_planning/material_planning_summary.js'
                    ])
                })
            }]
          },
          data: {
            title: 'Material Planning',
          }
        })

        //.state('app.inbound.PrimarySegregation.AddSegregation', {
        //  url: '/AddSegregation',
        //  templateUrl: 'views/inbound/toggle/add_segregation.html'
        //  })

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
            templateUrl: 'views/production/toggle/update_jo.html'
          })
          .state('app.production.RaiseJO.RWO', {
            url: '/RWO',
            templateUrl: 'views/production/toggle/update_rwo.html'
          })
          .state('app.production.RaiseJO.JobOrderPrint', {
            url: '/JobOrderPrint',
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
            templateUrl: 'views/production/toggle/confirmed_jo.html'
          })
          .state('app.production.RMPicklist.RawMaterialPicklist', {
            url: '/RawMaterialPicklist',
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
            templateUrl: 'views/production/toggle/receive_job_order.html'
          })
          .state('app.production.ReveiveJO.Rm', {
            url: '/Rm',
            templateUrl: 'views/production/toggle/rm_detail.html'
          })
          .state('app.production.ReveiveJO.Print', {
            url: '/Print',
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
            templateUrl: 'views/production/toggle/job_order_putaway.html'
          })
        .state('app.production.BackOrders', {
          url: '/BackOrders',
          templateUrl: 'views/production/back_orders.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/pop_js/common_backorder_po.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/production/back_orders.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Back Orders',
          }
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
          templateUrl: 'views/stockLocator/stock_summary_page.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/stockLocator/stock_summary/stock_summary.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/stockLocator/stock_summary/stock_summary_plant_sku.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/stockLocator/stock_summary/stock_summary_plant.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Stock Summary',
          }
        })

        .state('app.stockLocator.SkuClassification',{
          url:'/SkuClassification',
          templateUrl: 'views/stockLocator/skuclassification_datatable.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/skuclassification.js');
                    }]
          },
          data: {
            title: 'SkuClassification Master'
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
                return $ocLazyLoad.load([
                  'scripts/controllers/stockLocator/stock_detail.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/stockLocator/batch_level_stock.js'
                  ])
                });
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
            templateUrl: 'views/stockLocator/toggles/cycle_tg.html'
          })
          .state('app.stockLocator.CycleCount.ConfirmCycle', {
            url: '/ConfirmCycle',
            templateUrl: 'views/stockLocator/toggles/cycle_tg.html'
          })
        .state('app.stockLocator.MoveInventory', {
          url: '/MoveInventory',
          permission: 'change_inventoryadjustment',
          templateUrl: 'views/stockLocator/move_inventory.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load(['scripts/controllers/stockLocator/move_inventory.js'
                ]).then(function() {
                    return $ocLazyLoad.load(['scripts/controllers/stockLocator/auto_sellable.js'
                  ])
                }).then(function() {
                    return $ocLazyLoad.load(['scripts/controllers/stockLocator/vendor_stock_transfer.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Move Inventory',
          }
        })
          .state('app.stockLocator.MoveInventory.MoveLocationInventory', {
            url: '/MoveLocationInventory',
            templateUrl: 'views/stockLocator/toggles/mv_location_inventory_tg.html'
          })
          .state('app.stockLocator.MoveInventory.Inventory', {
            url: '/Inventory',
            templateUrl: 'views/stockLocator/toggles/mv_inventory_tg.html'
          })
          .state('app.stockLocator.MoveInventory.IMEI', {
            url: '/IMEI',
            templateUrl: 'views/stockLocator/toggles/imei.html'
          })
        .state('app.stockLocator.InventoryAdjustment', {
          url: '/InventoryAdjustment',
          permission: 'add_inventoryadjustment',
          templateUrl: 'views/stockLocator/inventory_adjustment.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                    return $ocLazyLoad.load(['scripts/controllers/stockLocator/inventory_adjustment.js'
                ]).then(function() {
                    return $ocLazyLoad.load(['scripts/controllers/stockLocator/new_inventory_adjustment.js'
                ])
            });
            }]
          },
          data: {
            title: 'Inventory Adjustment',
          }
        })
          .state('app.stockLocator.InventoryAdjustment.Adjustment', {
            url: '/Adjustment',
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
        .state('app.stockLocator.IMEITracker', {
          url: '/IMEITracker',
          permission: 'add_poimeimapping',
          templateUrl: 'views/stockLocator/imei_tracker.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/stockLocator/imei_tracker.js');
              }]
          },
          data: {
            title: 'Serial Number Tracker',
          }
        })

      // Outbound routes
      .state('app.outbound', {
          template: '<div ui-view></div>',
          abstract: true,
          url: '/outbound',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                {
                  serie: true,
                  files: [
                             'scripts/controllers/outbound/pop_js/common_backorder_po.js',
                             'scripts/controllers/outbound/pop_js/backorder_jo.js',
                             'scripts/controllers/outbound/pop_js/stock_transfer.js',
                             'scripts/controllers/outbound/pop_js/picklist.js',
                             'scripts/controllers/outbound/pop_js/manual_details.js',
                             'scripts/controllers/outbound/pop_js/custom_order_details.js',
                             'scripts/controllers/outbound/pop_js/reject_order.js',
                             'scripts/controllers/outbound/pop_js/enquiry_details.js'
                            ]
                        }]);
                    }]
          }
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

           .state('app.outbound.CreateOrders.DispatchSerialNumbers', {
              url: '/DispatchSerialNumbers',
              templateUrl: 'views/outbound/toggle/dispatch_serial_numbers.html'
            })

        .state('app.outbound.CreateCustomOrder', {
          url: '/CreateCustomOrder',
          permission: 'add_orderdetail',
          templateUrl: 'views/outbound/create_custom_order.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/outbound/create_custom_order.js');
            }]
          },
          data: {
            title: 'Customize Your Orders',
          }
        })
        .state('app.outbound.Ratings', {
          url: '/Ratings',
          templateUrl: 'views/outbound/ratings.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/outbound/ratings.js');
            }]
          },
          data: {
            title: 'Customers Ratings',
          }
        })
        .state('app.outbound.Ratings.Details', {
            url: '/Details',
            templateUrl: 'views/outbound/toggle/rating_details.html'
          })
        .state('app.outbound.ViewOrders', {
          url: '/ViewOrders',
          permission: 'add_picklist',
          templateUrl: 'views/outbound/view_orders.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                       // 'scripts/controllers/outbound/view_orders/custom_orders.js',
                       'scripts/controllers/outbound/view_orders/central_orders.js',
                       'scripts/controllers/outbound/view_orders/create_central_orders.js',
              ]).then( function() {
                return $ocLazyLoad.load('scripts/controllers/outbound/view_orders/stock_transfer/intra_st.js');
              }).then(function () {
                return $ocLazyLoad.load('scripts/controllers/outbound/view_orders/stock_transfer/inter_st.js');
              }).then(function () {
                return $ocLazyLoad.load('scripts/controllers/inbound/material_request_orders.js');
              }).then(function () {
                return $ocLazyLoad.load('scripts/controllers/outbound/view_orders/orders.js');
              }).then(function () {
                return $ocLazyLoad.load('scripts/controllers/outbound/view_orders/custom_orders.js');
              });
            }]
          },
          data: {
            title: 'View Orders',
          }
        })


          .state('app.outbound.ViewOrders.Picklist', {
            url: '/Picklist',
            templateUrl: 'views/outbound/toggle/batch_tg.html'
          })
          .state('app.outbound.ViewOrders.Transfer', {
            url: '/Transfer',
            templateUrl: 'views/outbound/toggle/transfer_tg.html'
          })
          .state('app.outbound.ViewOrders.OrderDetails', {
            url: '/OrderDetails',
            templateUrl: 'views/outbound/toggle/view_order_details.html'
          })
          .state('app.outbound.ViewOrders.StockTransferAltView', {
            url: '/StockTransferAltView',
            templateUrl: 'views/outbound/toggle/alt_view_order_details.html'
          })
          .state('app.outbound.ViewOrders.CustomOrderDetails', {
            url: '/CustomOrderDetails',
            templateUrl: 'views/outbound/toggle/custom_order_detail.html'
          })
          .state('app.outbound.ViewOrders.CentralOrderDetails', {
            url: '/CentralOrderDetails',
            templateUrl: 'views/outbound/toggle/central_order_detail.html'
          })
          .state('app.outbound.ViewOrders.GenerateInvoice', {
            url: '/Invoice',
            templateUrl: 'views/outbound/print/generate_inv.html'
          })
          .state('app.outbound.ViewOrders.DetailGenerateInvoice', {
            url: '/DetailInvoice',
            templateUrl: 'views/outbound/print/d_generate_inv.html'
          })
          .state('app.outbound.ViewOrders.InvoiceM', {
            url: '/InvoiceM',
            templateUrl: 'views/outbound/print/customer_inv.html'
          })
          .state('app.outbound.ViewOrders.InvoiceE', {
            url: '/InvoiceE',
            templateUrl: 'views/outbound/print/empty_invoice.html'
          })
        .state('app.outbound.PullConfirmation', {
          url: '/PullConfirmation',
          permission: 'add_picklistlocation',
          templateUrl: 'views/outbound/pull_confirmation.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/pop_js/picklist.js'
                ]).then( function() {
                 return $ocLazyLoad.load([
                   'scripts/controllers/outbound/pull_confirm/open_orders.js'
                 ])
                }).then( function() {
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
        .state('app.outbound.PullConfirmation.OrderDetails', {
            url: '/OrderDetails',
            templateUrl: 'views/outbound/toggle/view_order_details.html'
          })
          .state('app.outbound.PullConfirmation.Open', {
            url: '/Open',
            templateUrl: 'views/outbound/toggle/open_tg.html'
          })
          .state('app.outbound.PullConfirmation.Picked', {
            url: '/Picked',
            templateUrl: 'views/outbound/toggle/picked_tg.html'
          })
          .state('app.outbound.PullConfirmation.GenerateInvoice', {
            url: '/Invoice',
            templateUrl: 'views/outbound/print/generate_inv.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  {
                    insertBefore: '#load_styles_before',
                    files: [
                                'styles/custom/page.css'
                           ]
                  }
                ]);
              }]
            }
          })
          .state('app.outbound.PullConfirmation.InvoiceE', {
            url: '/InvoiceE',
            templateUrl: 'views/outbound/print/empty_invoice.html'
          })
          .state('app.outbound.PullConfirmation.InvoiceM', {
            url: '/InvoiceM',
            templateUrl: 'views/outbound/print/customer_inv.html'
          })
          .state('app.outbound.PullConfirmation.barcode', {
            url: '/Barcode',
            templateUrl: 'views/masters/toggles/barcode.html'
          })
          .state('app.outbound.PullConfirmation.DetailGenerateInvoice', {
            url: '/DetailInvoice',
            templateUrl: 'views/outbound/print/d_generate_inv.html'
          })
        .state('app.outbound.EnquiryOrders', {
          url: '/EnquiryOrders',
          templateUrl: 'views/outbound/enquiry_details.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/pending_manual_enquiry.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/enquiry_orders.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/manual_enquiry.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Marketing Enquiry Orders',
          }
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
              }).then( function() {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/shipment_info/gateout.js'
                ])
              }).then( function() {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/shipment_info/stock_transfer_shipment.js'
                ])
              });
            }]
          },
          data: {
            title: 'Shipment Info',
          }
        })
        .state('app.outbound.ShipmentInfo.InvoiceE', {
           url: '/InvoiceE',
           templateUrl: 'views/outbound/print/manifest_invoice.html'
         })

        .state('app.outbound.ShipmentInfo.Shipment', {
          url: '/Shipment',
          templateUrl: 'views/outbound/toggle/ship_tg.html'
        })
        .state('app.outbound.ShipmentInfo.ConfirmShipment', {
          url: '/ConfirmShipment',
          templateUrl: 'views/outbound/toggle/confirm_ship_tg.html'
        })
        .state('app.outbound.ShipmentInfo.ST_Shipment', {
          url: '/STShipment',
          templateUrl: 'views/outbound/toggle/st_ship_tg.html'
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
        .state('app.outbound.CreateAllocation', {
          url: '/CreateAllocation',
          permission: 'add_orderdetail',
          templateUrl: 'views/outbound/create_allocation.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/create_allocations/create_allocation.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/create_allocations/create_deallocation.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Create Allocation / Deallocation',
          }
        })
        .state('app.outbound.CreateStockTransfer', {
          url: '/CreateStockTransfer',
          permission: 'multi_warehouse',
          templateUrl: 'views/outbound/create_stock_transfer.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/stock_transfer/intra_st.js',
                    'scripts/controllers/outbound/stock_transfer/inter_st.js',
                  ])
              }]
          },
          data: {
            title: 'Create Stock Transfer',
          }
        })
        .state('app.outbound.ClosingStock', {
          url: '/ClosingStock',
          permission: 'change_consumptiondata',
          templateUrl: 'views/outbound/closing_stock_main.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/closing_stock.js',
                  ])
              }]
          },
          data: {
            title: 'Closing Stock',
          }
        })
        .state('app.outbound.CreateManualTest', {
          url: '/CreateManualTest',
          permission: 'add_consumptiondata',
          templateUrl: 'views/outbound/create_manual_test_main.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/create_manual_test.js',
                    'scripts/controllers/outbound/view_manual_test.js'
                  ])
              }]
          },
          data: {
            title: 'Manual Test',
          }
        })
        .state('app.outbound.CreateManualTest.confirmation', {
            url: '/Confirmation',
            templateUrl: 'views/outbound/toggle/confirm_manual_test.html'
          })
        .state('app.outbound.CustomerInvoices', {
          url: '/CustomerInvoices',
          templateUrl: 'views/outbound/customer_invoices.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/customer_invoices.js'
                  ]).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/outbound/customer_invoices/delivery_challan.js'
                    ])
                  }).then( function() {
                    return $ocLazyLoad.load([
                      'scripts/controllers/outbound/customer_invoices/customer_invoices.js'
                    ])
                  }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/stock_transfer_invoice.js',
                  ])
                }).then( function() {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/customer_invoices/cancelled_invoice.js'
                ]);
                })
              }]
          },
          data: {
            title: 'Customer Invoices',
          }
        })

        .state('app.outbound.CustomerInvoicesMain', {
          url: '/CustomerInvoicesMain',
          templateUrl: 'views/outbound/customer_invoices_main.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load([
                       'scripts/controllers/outbound/customer_invoices_main.js'
                        ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/material_request_challan.js',
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/stock_transfer_invoice.js',
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/inter_stock_sale_invoice.js',
                  ])
                }).then( function() {
            return $ocLazyLoad.load([
               'scripts/controllers/outbound/picklistdc.js',
          ])
        })
            }]
          },
          data: {
            title: 'Customer Invoices',
          }
        })
         .state('app.outbound.PullConfirmation.DeliveryChallan', {
            url: '/DeliveryChallan',
            templateUrl: 'views/outbound/print/empty_invoice_main.html'
         })
         .state('app.outbound.ViewOrders.DeliveryChallan', {
            url: '/DeliveryChallan',
            templateUrl: 'views/outbound/print/empty_invoice_main.html'
         })
         .state('app.outbound.CustomerInvoicesMain.InvoiceM', {
            url: '/InvoiceM',
            templateUrl: 'views/outbound/print/customer_inv_main.html'
         })
         .state('app.outbound.CustomerInvoicesMain.InvoiceN', {
            url: '/InvoiceN',
            templateUrl: 'views/outbound/print/generate_inv_main.html',
          })
         .state('app.outbound.CustomerInvoicesMain.InvoiceE', {
            url: '/InvoiceE',
            templateUrl: 'views/outbound/print/empty_invoice_main.html'
          })
          .state('app.outbound.CustomerInvoicesMain.InvoiceD', {
            url: '/InvoiceD',
            templateUrl: 'views/outbound/print/d_generate_inv_main.html'
          })
		  .state('app.outbound.CustomerInvoicesMain.StockTransferInvoiceE', {
            url: '/StockInvoice',
            templateUrl: 'views/outbound/print/empty_invoice.html'
          })

         .state('app.outbound.CustomerInvoices.InvoiceM', {
            url: '/InvoiceM',
            templateUrl: 'views/outbound/print/customer_inv.html'
         })
         .state('app.outbound.CustomerInvoicesMain.dc', {
            url: '/picklistdc',
            templateUrl: 'views/outbound/print/picklist_dc.html'
         })
         .state('app.outbound.CustomerInvoices.InvoiceN', {
            url: '/InvoiceN',
            templateUrl: 'views/outbound/print/generate_inv.html',
          })
         .state('app.outbound.CustomerInvoices.InvoiceE', {
            url: '/InvoiceE',
            templateUrl: 'views/outbound/print/empty_invoice.html'
          })
          .state('app.outbound.CustomerInvoices.InvoiceD', {
            url: '/InvoiceD',
            templateUrl: 'views/outbound/print/d_generate_inv.html'
          })
          .state('app.outbound.CustomerInvoices.StockTransferInvoiceE', {
            url: '/StockInvoice',
            templateUrl: 'views/outbound/print/empty_invoice.html'
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
      // Uploaded Po's route
      .state('app.uploadedPOs', {
          url: '/uploadedPOs',
          templateUrl: 'views/uploadedPos/uploadedPos.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/uploadedPos/uploadedPos.js');
              }]
          },
          data: {
            title: 'Uploaded PO\'s'
          }
        })
      .state('app.uploadedPOs.PO', {
            url: '/PO',
            templateUrl: 'views/uploadedPos/toggles/uploaded_po_update.html'
         })
      // Distributor's Orders
      .state('app.distributorOrders', {
          url: '/distributorOrders',
          templateUrl: 'views/distributorOrders/distributorOrders.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/distributorOrders/distributorOrders.js');
              }]
          },
          data: {
            title: 'Distributor\'s Orders'
          }
        })
      .state('app.distributorOrders.IndividualOrder', {
            url: '/IndividualOrder',
            templateUrl: 'views/distributorOrders/toggle/distributor_order_details.html'
         })
      // feedback form
      .state('app.feedback', {
          url: '/feedback',
          templateUrl: 'views/feedback/feedback.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/feedback/feedback.js');
              }]
          }
        })
      // Targets route
      .state('app.targets', {
          url: '/targets',
          templateUrl: 'views/targets/targets.html',
          authRequired: true,
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad){
              return $ocLazyLoad.load('scripts/controllers/targets/targets.js');
            }]
          },
          data: {
            title: 'Targets'
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
          templateUrl: 'views/payment_tracker/alternative_payment_tab.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/payment_tracker/payment_tracker.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/payment_tracker/outbound_payment_report.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/payment_tracker/payment_tracker_inbound.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/payment_tracker/inbound_payment_report.js'
                  ])
                });
              }]
          },
          data: {
            title: 'Pending Payment Tracker'
          }
        })
      // Track Orders Invoice Based
      .state('app.PaymentTrackerInvBased', {
          url: '/PaymentTrackerInvBased',
          templateUrl: 'views/payment_tracker/payment_tracker_inv_based.html',
          authRequired: true,
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/payment_tracker/payment_tracker_inv_based.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/payment_tracker/outbound_payment_report.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/payment_tracker/inbound_payment_tracker.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/payment_tracker/inbound_payment_report.js'
                  ])
                }).then( function() {
                    return $ocLazyLoad.load([{

                      insertBefore: '#load_styles_before',
                      files: [
                                'scripts/extentions/plugins/multiselect/multi-select.css'
                              ]
                      }, {
                      serie: true,
                      files: [
                                'scripts/extentions/plugins/multiselect/jquery.multi-select.js'
                              ]
                      }]).then(function () {
                        return $ocLazyLoad.load('scripts/controllers/payment_tracker/outbound_payment.js');
                  });
                });
              }]
          },
          data: {
            title: 'Payments'
          }
        })

      .state('app.PaymentTrackerInvBased.Inv_Details', {
            url: '/Inv_Details',
            templateUrl: 'views/payment_tracker/toggle/inv_details.html',
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
        .state('app.reports.IntegrationReport', {
          url: '/IntegrationReport',
          templateUrl: 'views/reports/integration_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/integration_report.js');
              }]
          },
          data: {
            title: 'Netsuite Integration Report',
          }
        })
        .state('app.reports.MRPExceptionReport', {
          url: '/MRPExceptionReport',
          templateUrl: 'views/reports/mrp_exception_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/mrp_exception_report.js');
              }]
          },
          data: {
            title: 'MRP Exception Report',
          }
        })
        .state('app.reports.MRPDepartmentReport', {
          url: '/MRPDepartmentReport',
          templateUrl: 'views/reports/mrp_department_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/mrp_department_report.js');
              }]
          },
          data: {
            title: 'MRP Department Report',
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
        }).state('app.reports.PR_AODReport', {
          url: '/PR_AODReport',
          templateUrl: 'views/reports/pr_as_on_date_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/pr_as_on_date_report.js');
              }]
          },
          data: {
            title: 'Pending PR As on Date',
          }
        }).state('app.reports.PR_PO_GRNReport', {
          url: '/PR_PO_GRNReport',
          templateUrl: 'views/reports/pr_po_grn_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/pr_po_grn_report.js');
              }]
          },
          data: {
            title: 'PR PO GRN Report',
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
         .state('app.reports.STGoodsReceiptNote', {
          url: '/STGoodsReceiptNote',
          templateUrl: 'views/reports/st_grn_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/st_grn_report.js');
              }]
          },
          data: {
            title: 'Stock Transfer Goods Receipt Note',
          }
        })
        .state('app.reports.MetroPOReport', {
          url: '/MetropolisPOReport',
          templateUrl: 'views/reports/metro_po_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/metro_po_report.js');
              }]
          },
          data: {
            title: 'Metropolis PO Report',
          }
        })
        .state('app.reports.ApprovalPOReport', {
          url: '/ApprovalPOReport',
          templateUrl: 'views/reports/approval_reports.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/approval_reports.js');
              }]
          },
          data: {
            title: 'Approval PO Report',
          }
        })
        .state('app.reports.ApprovalPOReport.ApprovalDetailReport', {
            url: '/ApprovalDetailReport',
            templateUrl: 'views/reports/toggles/approval_details.html',
          })
        .state('app.reports.STGoodsReceiptNote.PurchaseOrder', {
            url: '/STGoodsReceiptNote',
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
            title: 'Dispatch Summary',
          }
        })
        .state('app.reports.AllocationReport', {
          url: '/AllocationReport',
          templateUrl: 'views/reports/allocation.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/allocation.js');
              }]
          },
          data: {
            title: 'Allocation Report',
          }
        })
        .state('app.reports.DeAllocationReport', {
          url: '/DeAllocationReport',
          templateUrl: 'views/reports/deallocation.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/deallocation.js');
              }]
          },
          data: {
            title: 'DeAllocation Report',
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
        .state('app.reports.StockAgeing', {
          url: '/StockAgeingReport',
          templateUrl: 'views/reports/ageing_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/ageing_report.js');
              }]
          },
          data: {
            title: 'Ageing Report',
          }
        })
        .state('app.reports.StockExpired', {
          url: '/StockExpiredReport',
          templateUrl: 'views/reports/stock_expired.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/stock_expired.js');
              }]
          },
          data: {
            title: 'Expired Report',
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
        .state('app.reports.SupplierWisePOs.POs', {
            url: '/POs',
            templateUrl: 'views/reports/toggles/po_details.html',
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
            title: 'Sales Return',
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
            title: 'Inventory Aging',
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
            title: 'Stock Summary',
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
            title: 'Daily Production',
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
            title: 'Order Summary',
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
            title: 'Open JO',
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
        .state('app.reports.RMPicklistReport', {
          url: '/RMPicklistReport',
          templateUrl: 'views/reports/rm_picklist_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/rm_picklist_report.js');
              }]
          },
          data: {
            title: 'RM Picklist',
          }
        })
        .state('app.reports.StockLedgerReport', {
          url: '/StockLedgerReport',
          templateUrl: 'views/reports/stock_ledger_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/stock_ledger_report.js');
              }]
          },
          data: {
            title: 'Stock Ledger',
          }
        })
        .state('app.reports.ShipmentReport', {
          url: '/ShipmentReport',
          templateUrl: 'views/reports/shipment_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/shipment_report.js');
              }]
          },
          data: {
            title: 'Shipment Report',
          }
        })
        .state('app.reports.PoSupplierMailReport', {
          url: '/PoSupplierMailReport',
          templateUrl: 'views/reports/po_supplier_mail_report.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/reports/po_supplier_mail_report.js');
            }]
          },
          data: {
            title: 'PO Supplier Mail Report',
          }
        })
        .state('app.reports.POReport', {
          url: '/POReport',
          templateUrl: 'views/reports/po_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/po_report.js');
              }]
          },
          data: {
            title: 'Open PO Report',
          }
        })

        .state('app.reports.OpenorderReport', {
          url: '/OpenorderReport',
          templateUrl: 'views/reports/openorderreport.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/open_order.js');
              }]
          },
          data: {
            title: 'Open Order Report',
          }
        })

        .state('app.reports.FinancalReport', {
          url: '/FinancalReport',
          templateUrl: 'views/reports/financialreport.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/financial_report.js');
              }]
          },
          data: {
            title: 'Financal Report',
          }
        })
        .state('app.reports.Orderflow', {
          url: '/OrderFlowReport',
          templateUrl: 'views/reports/orderflowreport.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/orderflow.js');
              }]
          },
          data: {
            title: 'CENTRAL ORDER TRACKER',
          }
        })

        .state('app.reports.Stockcover', {
          url: '/StockCoverReport',
          templateUrl: 'views/reports/stock_cover.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/stock_cover.js');
              }]
          },
          data: {
            title: 'Stock Cover Report',
          }
        })

        .state('app.reports.DistributorWiseSalesReport', {
          url: '/DistributorSalesReport',
          templateUrl: 'views/reports/dist_sales_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/dist_sales_report.js');
              }]
          },
          data: {
            title: 'Distributor Wise Sales Report',
          }
        })
        .state('app.reports.ResellerWiseSalesReport', {
          url: '/ResellerSalesReport',
          templateUrl: 'views/reports/reseller_sales_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/reseller_sales_report.js');
              }]
          },
          data: {
            title: 'Reseller Wise Sales Report',
          }
        })
        .state('app.reports.ZoneTargetSummaryReport', {
          url: '/ZoneTargetSummaryReport',
          templateUrl: 'views/reports/zone_target_summary_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/zone_target_summary_report.js');
              }]
          },
          data: {
            title: 'Zone Targets Summary Report',
          }
        })
        .state('app.reports.ZoneTargetDetailedReport', {
          url: '/ZoneTargetDetailedReport',
          templateUrl: 'views/reports/zone_target_detailed_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/zone_target_detailed_report.js');
              }]
          },
          data: {
            title: 'Zone Targets Detailed Report',
          }
        })
        .state('app.reports.DistTargetSummaryReport', {
          url: '/DistTargetSummaryReport',
          templateUrl: 'views/reports/dist_target_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/dist_target_report.js');
              }]
          },
          data: {
            title: 'Distributor Targets Summary Report',
          }
        })
        .state('app.reports.DistTargetDetailedReport', {
          url: '/DistTargetDetailedReport',
          templateUrl: 'views/reports/dist_target_detailed_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/dist_target_detailed_report.js');
              }]
          },
          data: {
            title: 'Distributor Targets Detailed Report',
          }
        })
        .state('app.reports.ResellerTargetSummaryReport', {
          url: '/ResellerTargetSummaryReport',
          templateUrl: 'views/reports/reseller_target_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/reseller_target_report.js');
              }]
          },
          data: {
            title: 'Reseller Targets Summary Report',
          }
        })
        .state('app.reports.ResellerTargetDetailedReport', {
          url: '/ResellerTargetDetailedReport',
          templateUrl: 'views/reports/reseller_target_detailed_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/reseller_target_detailed_report.js');
              }]
          },
          data: {
            title: 'Reseller Targets Detailed Report',
          }
        })
        .state('app.reports.CorporateTargetReport', {
          url: '/CorporateTargetReport',
          templateUrl: 'views/reports/corp_target_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/corp_target_report.js');
              }]
          },
          data: {
            title: 'Corporate Targets Report',
          }
        })
        .state('app.reports.CorpResellerMappingReport', {
          url: '/CorporateResellerMappingReport',
          templateUrl: 'views/reports/corp_reseller_mapping_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/corp_reseller_mapping_report.js');
              }]
          },
          data: {
            title: 'Corporate Reseller Mapping Report',
          }
        })
        .state('app.reports.EnquiryStatusReport', {
          url: '/EnquiryStatusReport',
          templateUrl: 'views/reports/enquiry_status_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/enquiry_status_report.js');
              }]
          },
          data: {
            title: 'Enquiry Status Report',
          }
        })
        .state('app.reports.MaterialRequestReport', {
          url: '/MaterialRequestReport',
          templateUrl: 'views/reports/material_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/material_report.js');
              }]
          },
          data: {
            title: 'Material Request Report',
          }
        })
        .state('app.reports.StockTransferReport', {
          url: '/StockTransferReport',
          templateUrl: 'views/reports/stock_transfer_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/stock_transfer_report.js');
              }]
          },
          data: {
            title: 'Intra Stock Transfer Orders',
          }
        })
        .state('app.reports.SaleTransferReport', {
          url: '/SaleTransferReport',
          templateUrl: 'views/reports/sale_transfer_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/inter_sale_orders.js');
              }]
          },
          data: {
            title: 'Inter Sale Transfer Orders',
          }
        })
        .state('app.reports.StockReconciliationReport', {
          url: '/StockReconciliationReport',
          templateUrl: 'views/reports/stock_reconciliation_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/stock_reconciliation_report.js');
              }]
          },
          data: {
            title: 'Stock Reconciliation Report',
          }
        })
        .state('app.reports.RTVReport', {
          url: '/RTVReport',
          templateUrl: 'views/reports/rtv_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/rtv_report.js');
              }]
          },
          data: {
            title: 'RTV Report',
          }
        })
        .state('app.reports.CancelGRNReport', {
          url: '/CancelGRNReport',
          templateUrl: 'views/reports/cancel_grn_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/cancel_grn_report.js');
              }]
          },
          data: {
            title: 'Cancel GRN Report',
          }
        })
        .state('app.reports.CreditNoteReport', {
          url: '/CreditNoteReport',
          templateUrl: 'views/reports/credit_note_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/credit_note_report.js');
              }]
          },
          data: {
            title: 'Credit Note Report',
          }
        })
        .state('app.reports.CreditNoteReport.CreditNoteReportPrint', {
           url: '/CreditNoteReportPrint',
           templateUrl: 'views/reports/toggles/purchase_order.html',
        })
        .state('app.reports.OpenPOApprovalReport', {
          url: '/OpenPOApprovalReport',
          templateUrl: 'views/reports/open_po_approval_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/open_po_approval_report.js');
              }]
          },
          data: {
            title: 'OPEN PO APPROVAL Report',
          }
        })
        .state('app.reports.PRReportPerformance', {
          url: '/PRReportPerformance',
          templateUrl: 'views/reports/pr_performance_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/pr_performance_report.js');
              }]
          },
          data: {
            title: 'PR Performance Report',
          }
        })
        .state('app.reports.POReportPerformance', {
          url: '/POReportPerformance',
          templateUrl: 'views/reports/po_rerformance_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/po_performance_report.js');
              }]
          },
          data: {
            title: 'PO Performance Report',
          }
        })
        .state('app.reports.PRReport', {
          url: '/PRReport',
          templateUrl: 'views/reports/pr_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/pr_report.js');
              }]
          },
          data: {
            title: 'PR Report',
          }
        })
        .state('app.reports.PRReport.PRs', {
            url: '/PRs',
            templateUrl: 'views/reports/toggles/pr_details.html',
          })
        .state('app.reports.RTVReport.DebitNotePrint', {
           url: '/DebitNotePrint',
           templateUrl: 'views/reports/toggles/purchase_order.html',
        })
        .state('app.reports.DiscrepancyReport.print', {
           url: '/DescrepancyNotePrint',
           templateUrl: 'views/reports/toggles/purchase_order.html',
        })
        .state('app.reports.CurrentStockReport', {
          url: '/CurrentStockReport',
          templateUrl: 'views/reports/current_stock_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/current_stock_report.js');
              }]
          },
          data: {
            title: 'Current Stock Report',
          }
        })
        .state('app.reports.ApprovalPOSummaryReport', {
          url: '/ApprovalPOSummaryReport',
          templateUrl: 'views/reports/approval_po_summary_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/approval_po_summary_report.js');
              }]
          },
          data: {
            title: 'Approval PO Summary Report',
          }
        })
        .state('app.reports.ApprovalPODetailReport', {
          url: '/ApprovalPODetailReport',
          templateUrl: 'views/reports/approval_po_detail_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/approval_po_detail_report.js');
              }]
          },
          data: {
            title: 'Approval PO Detail Report',
          }
        })
        .state('app.reports.InventoryValueReport', {
          url: '/InventoryValueReport',
          templateUrl: 'views/reports/inventory_value_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/inventory_value_report.js');
              }]
          },
          data: {
            title: 'Inventory Value Report',
          }
        })
        .state('app.reports.BulkToRetailReport', {
          url: '/BulkToRetailReport',
          templateUrl: 'views/reports/bulk_to_retail_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/bulk_to_retail_report.js');
              }]
          },
          data: {
            title: 'Bulk to Retail Report',
          }
        })
        .state('app.reports.MarginReport', {
          url: '/MarginReport',
          templateUrl: 'views/reports/margin_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/margin_report.js');
              }]
          },
          data: {
            title: 'Margin Report',
          }
        })
        .state('app.reports.MoveInventoryReport', {
          url: '/MoveInventoryReport',
          templateUrl: 'views/reports/move_inventory_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/move_inventory_report.js');
              }]
          },
          data: {
            title: 'MoveInventory Report',
          }
        })
        .state('app.reports.BasaReport', {
          url: '/BASAReport',
          templateUrl: 'views/reports/basa_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/basa_report.js');
              }]
          },
          data: {
            title: 'BASA Report',
          }
        })
        .state('app.reports.CancelledInvoicesReport', {
          url: '/CancelInvoiceReport',
          templateUrl: 'views/reports/cancel_invoice_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/cancel_invoice_report.js');
              }]
          },
          data: {
            title: 'Cancelled Invoices Report',
          }
        })
        
        .state('app.reports.DiscrepancyReport', {
          url: '/DiscrepancyReport',
          templateUrl: 'views/reports/discrepancy_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/discrepancy_report.js');
              }]
          },
          data: {
            title: 'Discrepancy Report',
          }
        })
        .state('app.reports.BulkStockUpdate', {
          url: '/BulkStockUpdate',
          templateUrl: 'views/reports/bulk_stock_update.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/bulk_stock_update.js');
              }]
          },
          data: {
            title: 'Bulk Stock Update',
          }
        })
        .state('app.reports.creditNoteForm', {
          url: '/creditNoteForm',
          templateUrl: 'views/reports/credit_note_form.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/credit_note_form.js');
              }]
          },
          data: {
            title: 'Credit Note Form (Oracle Upload File)',
          }
        })
        .state('app.reports.ConsumptionData', {
          url: '/consumptionData',
          templateUrl: 'views/reports/consumption_data.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/consumption_data.js');
              }]
          },
          data: {
            title: 'Test Data',
          }
        })
        .state('app.reports.ConsumptionReport', {
          url: '/consumptionReport',
          templateUrl: 'views/reports/consumption_report.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/reports/consumption_report.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/reports/consumption_reversal.js'
                  ])
                })
              }]
          },
          data: {
            title: 'Consumption',
          }
        })
        .state('app.reports.ClosingStockReport', {
          url: '/closingStockReport',
          templateUrl: 'views/reports/closing_stock_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/closing_stock_report.js');
              }]
          },
          data: {
            title: 'Closing Stock Report',
          }
        })
        .state('app.reports.PlantMaster', {
          url: '/PlantMaster',
          templateUrl: 'views/reports/plant_dept_subsidary.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/plant_dept_sunsidarry_report.js');
              }]
          },
          data: {
            title: 'Subsidary - Plant - Department Master Report',
          }
        })
      // configuration route
      .state('app.configurations', {
          url: '/configurations',
          templateUrl: 'views/configurations/all_configurations.html',
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
                return $ocLazyLoad.load('scripts/controllers/configs/configurations.js')
                .then(function(){
                return $ocLazyLoad.load([
                    'scripts/controllers/configs/classification.js'
                  ])
                })
                .then(function(){
                  return $ocLazyLoad.load([
                      'scripts/controllers/configs/new_barcode_configurations.js'
                   ])
                 })
                .then(function(){
                  return $ocLazyLoad.load([
                      'scripts/controllers/configs/barcode_configurations.js'
                    ])
                  });
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

      //Porfile
      .state('app.Profile', {
          url: '/Profile',
          templateUrl: 'views/profile/profile.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/profile.js');
                    }]
          },
          data: {
            title: 'Profile'
          }
        })

      //supplier purchase order
      .state('app.PurchaseOrder', {
          url: '/PurchaseOrder',
          templateUrl: 'views/inbound/supplier_purchase_order.html',
		  resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/pop_js/custom_order_details.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/inbound/supplier_purchase_order.js'
                  ])
                }).then( function() {
                return $ocLazyLoad.load([
                  {
                  serie: true,
                        files: ['scripts/controllers/inbound/pop_jos/common_asn.js']}
                ])
              });
              }]
          },
          data: {
            title: 'Purchase Order'
          }
        })
      .state('app.PurchaseOrder.SKUDetails', {
            url: '/SKUDetails',
            templateUrl: 'views/inbound/toggle/supplier_po_sku_data.html'
          })
      //ASN Report
       .state('app.reports.ASNReport', {
          url: '/ASNReport',
          templateUrl: 'views/reports/asn_report.html',
          resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/reports/asn_report.js');
              }]
          },
          data: {
            title: 'ASN Report',
          }
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
        .state('user.smlogin', {
          url: '/sm_login',
          templateUrl: 'own/views/sm_login.html',
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
        .state('user.marshlogin', {
          url: '/marsh_login',
          templateUrl: 'own/views/marsh_login.html',
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
          templateUrl: 'views/forgot.html',
          resolve: {
            deps: ['$ocLazyLoad', function ($ocLazyLoad) {
              return $ocLazyLoad.load('scripts/controllers/forgot_password.js');
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
        .state('user.Corp Attire', {
          url: '/corp_attire_login',
          templateUrl: 'views/customers/corp_attire_login.html',
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
          .state('user.App.BrandCategorization', {
            url: '/BrandCategorization',
            templateUrl: 'views/outbound/app/create_orders/brandCategorization.html'
          })
          .state('user.App.PendingOrder', {
            url: '/PendingOrder',
            templateUrl: 'views/outbound/app/create_orders/pending_order.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/pending_order.js');
              }]
              }
            })
            .state('user.App.PendingOrder.PendingApprovalData', {
              url: '/PendingApprovalData',
              templateUrl: 'views/outbound/app/create_orders/pending_approval_popup.html',
              resolve: {
                deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                  return $ocLazyLoad.load('scripts/controllers/outbound/app/pending_order.js');
                }]
              }
            })
          .state('user.App.Categories', {
            url: '/Categories',
            templateUrl: 'views/outbound/app/create_orders/categories.html'
            // templateUrl: 'views/outbound/app/create_orders/catlog.html'
          })
          .state('user.App.Profile', {
            url: '/Profile',
            templateUrl: 'views/outbound/app/create_orders/profile.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/profile.js');
                      }]
            },
            data: {
              title: 'Profile'
            }
          })
          .state('user.App.feedback', {
            url: '/feedback',
            templateUrl: 'views/outbound/app/create_orders/feedback.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/feedback.js');
                      }]
            },
            data: {
              title: 'feedback'
            }
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
          .state('user.App.newStyle', {
            url: '/newStyle',
            templateUrl: 'views/outbound/app/create_orders/newstyle.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/newstyle.js');
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
          .state('user.App.Notifications', {
            url: '/Notifications',
            templateUrl: 'views/outbound/app/create_orders/notifications.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/notifications.js');
              }]
            }
          })

          .state('user.App.CorporateOrders', {
            url: '/CorporateOrders',
            templateUrl: 'views/outbound/app/create_orders/corporate_orders.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/corporate_orders.js');
              }]
            }
          })
          .state('user.App.MyOrders', {
            // url: '/MyOrders?state',
            url: '/MyOrders',
            params: {
              state: 'orders',
            },
            templateUrl: 'views/outbound/app/create_orders/your_orders.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load([
                  'scripts/controllers/outbound/app/my_order.js'
                ]).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/app/orders.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/app/market_enq.js'
                  ])
                }).then( function() {
                  return $ocLazyLoad.load([
                    'scripts/controllers/outbound/app/custom_orders.js'
                  ])
                });
              }]
            }
          })
          .state('user.App.MyOrders.OrderDetails', {
            url: '/OrderDetails',
            templateUrl: 'views/outbound/toggle/order_detail.html',
            })
          .state('user.App.MyOrders.CustomOrder', {
            url: '/CustomOrder',
            templateUrl: 'views/outbound/toggle/custom_detail_view.html',
            })
          .state('user.App.ManualEnquiry', {
            url: '/ManualEnquiry',
            templateUrl: 'views/outbound/app/create_orders/manual_enquiry.html',
            resolve: {
              deps: ['$ocLazyLoad', function ($ocLazyLoad) {
                return $ocLazyLoad.load('scripts/controllers/outbound/app/manual_enquiry.js');
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
