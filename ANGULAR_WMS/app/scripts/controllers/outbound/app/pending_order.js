'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PendingOrderTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
	  vm.session_roles = Session.roles;
    vm.priceband_sync = vm.session_roles.permissions.priceband_sync;
    vm.display_sku_cust_mapping = vm.session_roles.permissions.display_sku_cust_mapping;
    vm.user_role = vm.session_roles.user_role;
    vm.model_data = {};
    vm.is_portal_lite = Session.roles.permissions.is_portal_lite;
    vm.date = new Date();

    /*if (Session.roles.permissions.is_portal_lite) {
      if (vm.location != '/App/PendingOrder') {
        
        $state.go('user.App.PendingOrder');
      }
    }*/

    vm.filters = {'datatable': 'OrderApprovals', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

		vm.dtColumns = [
			DTColumnBuilder.newColumn('approve_id').withTitle('Approval Id'),
			DTColumnBuilder.newColumn('user').withTitle('Customer User'),
			//DTColumnBuilder.newColumn('remarks').withTitle('Remarks').notVisible(),
			DTColumnBuilder.newColumn('status').withTitle('Status').renderWith(function(data, type, full, meta) {
              var status_name = '';
		console.log(vm.user_role);
                if (data == 'accept' && full.approving_user_role.toLowerCase() == 'hod') {
                    status_name = "Pending - To be approved by ADMIN";
		    if (vm.user_role.toLowerCase() == 'user') {
                      vm.show_quantity = true;
                    } else if (vm.user_role.toLowerCase() == 'hod') {
                      vm.show_quantity = true;
                    } else if (vm.user_role.toLowerCase() == 'admin') {
                      vm.show_quantity = false;
                    }
                } else if (data == 'accept' && full.approving_user_role == 'admin') {
                    status_name = "Accepted by ADMIN";
                    vm.show_quantity = true;
                } else if (data == 'pending' && full.approving_user_role == 'hod') {
                    status_name = "Pending - To be approved by "+ full.approving_user_role.toUpperCase();
					if (vm.user_role == 'user') {
                      vm.show_quantity = true;
					} else if (vm.user_role == 'hod') {
					  vm.show_quantity = false;
					} else if (vm.user_role == 'admin') {
					  vm.show_quantity = true;
					}
                } else if (data == 'accept') {
                    status_name = 'Accepted';
                    vm.show_quantity = true;
                } else if (data == 'reject') {
                    status_name = 'Rejected by ' + full.approving_user_role.toUpperCase();
                    vm.show_quantity = true;
                }
                return status_name;
			}).withOption('width', '230px'),
			DTColumnBuilder.newColumn('date').withTitle('Date'),
		];

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(vm.model_data)
                angular.copy(aData, vm.model_data);

				        if (vm.model_data.status == 'accept' && vm.model_data.approving_user_role == 'hod') {
                    if (vm.user_role == 'user') {
                      vm.show_quantity = true;  
                    } else if (vm.user_role == 'hod') {
                      vm.show_quantity = true;
                    } else if (vm.user_role == 'admin') {
                      vm.show_quantity = false;
                    }
                } else if (vm.model_data.status == 'accept' && vm.model_data.approving_user_role == 'admin') {
                    vm.show_quantity = true;
                } else if (vm.model_data.status == 'pending' && vm.model_data.approving_user_role == 'hod') {
                    if (vm.user_role == 'user') {
                      vm.show_quantity = false;  
                    } else if (vm.user_role == 'hod') {
                      vm.show_quantity = false;
                    } else if (vm.user_role == 'admin') {
                      vm.show_quantity = true;
                    }
                } else if (vm.model_data.status == 'accept') {
                    vm.show_quantity = true;
                } else if (vm.model_data.status == 'reject') {
                    vm.show_quantity = true;
                }

                vm.service.apiCall("order_approval_sku_details/", "GET", vm.model_data).then(function(data) {

                  if(data.message) {

                    if (data.data.status) {

                      vm.model_data.data = [];
                      angular.copy(data.data.data, vm.model_data.data);
                      vm.update = true;
                      vm.title = "Modify Order Approvals";
                      $state.go('user.App.PendingOrder.PendingApprovalData');
                    }
                  } else {

                    $state.go('user.App.PendingOrder.PendingApprovalData');
                  }
                });
            });
        });
    }

  vm.close_popup = function() {
    $state.go('user.App.PendingOrder');
  }

  vm.submit = submit;
  function submit(data) {
    if (data.$valid) {
      if (vm.model_data.tax_type) {
        if ("Add Customer" == vm.title) {
          vm.customer('insert_customer/');
        } else {
          vm.model_data['data-id'] = vm.model_data.DT_RowId;
          vm.customer('update_customer_values/');
        }
      } else {
        vm.service.pop_msg('Please select tax type');
      }
    }
  }

  /*
  vm.status_data = ["Inactive", "Active"];
  vm.customer_roles = ["User", "HOD", "Admin"];
  var empty_data = {customer_id: "", name: "", email_id: "", address: "", phone_number: "", status: "", create_login: false,
                    login_created: false, tax_type: "", margin: 0, customer_roles: ""};

  vm.base = function() {
    vm.title = "Add Customer";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
    vm.model_data.status = vm.status_data[1];
    vm.model_data.role = vm.customer_roles[0];
  }
  vm.base();

  vm.get_customer_id = function() {

    vm.service.apiCall("get_customer_master_id/").then(function(data){
      if(data.message) {

        vm.model_data["customer_id"] = data.data.customer_id;
        vm.all_taxes = data.data.tax_data;
        vm.model_data["price_type_list"] = data.data.price_types;
        vm.model_data["logged_in_user_type"] = data.data.logged_in_user_type;
        vm.model_data["level_2_price_type"] = data.data.level_2_price_type;
        vm.model_data["price_type"] = data.data.price_type;
      }
    });
  }
  vm.get_customer_id();

  vm.add = add;
  function add() {

    vm.base();
    vm.get_customer_id();
    $state.go('app.masters.CustomerMaster.customer');
  }

  vm.customer = function(url) {
    var send = {}
    var send = $("form").serializeArray()
    var data = $.param(send);
    vm.service.apiCall(url, 'POST', send, true).then(function(data){
      if(data.message) {
        if(data.data == 'New Customer Added' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = submit;
  function submit(data) {
    if (data.$valid) {
      if (vm.model_data.tax_type) {
        if ("Add Customer" == vm.title) {
          vm.customer('insert_customer/');
        } else {
          vm.model_data['data-id'] = vm.model_data.DT_RowId;
          vm.customer('update_customer_values/');
        }
      } else {
        vm.service.pop_msg('Please select tax type');
      }
    } else if (!(data.phone_number.$valid)) {
      vm.service.pop_msg('Invalid phone number');
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }
  */

  vm.update_cartdata_for_approval = function(approve_status, approve_id, quantity) {
    var send = {}
    if (vm.display_sku_cust_mapping) {
      send['approval_status'] = approve_status
      send['approving_user_role'] = vm.user_role
	    send['approve_id'] = approve_id
      send['quantity'] = quantity
    }

    if (vm.user_role == "admin" && vm.model_data.shipment_date) {

      vm.update_cart_data(send);
    } else if (vm.user_role == "admin" && !(vm.model_data.shipment_date)) {

      vm.service.showNoty('Please fill required fields');
    } else {

      vm.update_cart_data(send);
    }
  }

  vm.update_cart_data = function(send){

    vm.service.apiCall("update_cartdata_for_approval/", "POST", send).then(function(response){

        if(response.message) {

          if(response.data.message == "success") {

            vm.service.showNoty('Your Order Has Been Sent for Approval', "success", "topRight");
            vm.service.refresh(vm.dtInstance);
            vm.close_popup();
          } else {

            vm.insert_cool = true;
            vm.data_status = true;
            vm.service.showNoty(response.data, "danger", "bottomRight");
          }
        }
    });
  }

  vm.after_admin_approval = function(approve_status, approve_id, quantity) {
    var send = {}
    send = $("form").serializeArray()

    /*
    angular.foreach(send, function(obj) {
      if (obj['name'] == "serial_no") {
        obj['name'] = "approve_id"
      }
    })
    */
    send.push({'name' : 'approval_status', 'value' : approve_status})
    send.push({'name' : 'approving_user_role', 'value' : vm.user_role})
    send.push({'name' : 'approve_id', 'value' : approve_id})


    vm.service.apiCall("after_admin_approval/", "POST", send).then(function(response){
        if(response.message) {
          if(response.data.message == "success") {
            swal({
              title: "Success!",
              text: "Your Order Has Been Placed",
              type: "success",
              showCancelButton: false,
              confirmButtonText: "OK",
              closeOnConfirm: true
              },
              function(isConfirm){
                $state.go("user.App.newStyle");
              }
            )
          } else {
            vm.insert_cool = true;
            vm.data_status = true;
            vm.service.showNoty(response.data, "danger", "bottomRight");
          }
        }
    });
  }



}

