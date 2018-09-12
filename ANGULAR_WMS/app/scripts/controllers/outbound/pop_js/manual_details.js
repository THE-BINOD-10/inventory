function ManualOrderDetails ($scope, Service, $modalInstance, items, Session) {
  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;

  vm.model_data = items;
  vm.order_details = {};
  vm.save = true;
  vm.date = new Date();
  vm.edit_enable = true;

  vm.loading = false;
  var url = "get_manual_enquiry_detail/";
  if (vm.model_data.url) {
    url = vm.model_data.url;
    delete vm.model_data.url;
  }

  vm.disable_btn = false;
  vm.notify_to_sub_dist = function(form){
    if(form.$invalid) {
      Service.showNoty('Please fill required fields');
      return false;
    }
    vm.disable_btn = true;
    Service.apiCall('save_manual_enquiry_data/', 'POST', vm.model_data).then(function(data) {
      if (data.message) {
        if (data.data.msg == 'Success') {
          $modalInstance.close();
        }
        Service.showNoty(data.data);
      } else {
        Service.showNoty('Something went wrong');
      }
      vm.disable_btn = false;
    });
  }

  vm.convert_customorder_to_actualorder = function() {
  elem = {};
  angular.copy(vm.model_data, elem);
    vm.service.apiCall('convert_customorder_to_actualorder/', 'POST', elem).then(function(data){
        if(data.data.msg == 'Success'){
          $modalInstance.close();
          Service.showNoty('Order Placed Successfully');
        }else{
          Service.showNoty(data.data, 'warning');
        }
    })
  }


  vm.send_for_approval = function(form) {

    if(vm.model_data.ask_price || vm.model_data.expected_date || vm.model_data.remarks) {

      if(!vm.model_data.ask_price && vm.order_details.order.customization_type != 'Product Customization') {
        Service.showNoty('Please Fill Ask Price', 'warning');
        return false;
      } else if (!vm.model_data.expected_date) {
        Service.showNoty('Please Fill Expected Date', 'warning');
        return false;
      } else if (!vm.model_data.remarks) {
        Service.showNoty('Please Fill Remarks', 'warning');
        return false;
      }
    }

    vm.disable_btn = true;
    var data = {};
    angular.copy(vm.model_data, data);
    data['status'] = "pending_approval";
    Service.apiCall('request_manual_enquiry_approval/', 'POST', data).then(function(data) {
      if (data.message) {
        if (data.data.msg == 'Success') {
          $modalInstance.close();
        }
        Service.showNoty(data.data.msg);
      } else {
        Service.showNoty('Something went wrong');
      }
      vm.disable_btn = false;
    });
  }

  vm.approved = function(form) {

    var data = {};
    if(vm.model_data.ask_price || vm.model_data.expected_date || vm.model_data.remarks) {

      if(!vm.model_data.ask_price && vm.order_details.order.customization_type != 'Product Customization') {
        Service.showNoty('Please Fill Ask Price', 'warning');
        return false;
      } else if (!vm.model_data.expected_date) {
        Service.showNoty('Please Fill Expected Date', 'warning');
        return false;
      } else if (!vm.model_data.remarks) {
        Service.showNoty('Please Fill Remarks', 'warning');
        return false;
      }
    }
    angular.copy(vm.model_data, data);
    data['status'] = "approved";
    vm.disable_btn = true;
    Service.apiCall('request_manual_enquiry_approval/', 'POST', data).then(function(data) {
      if (data.message) {
        if (data.data.msg == 'Success') {
          $modalInstance.close();
        }
        Service.showNoty(data.data.msg);
      } else {
        Service.showNoty('Something went wrong');
      }
      vm.disable_btn = false;
    });
  }

  vm.getDetails = function() {

    vm.loading = true;
    console.log(Session);
    Service.apiCall(url, "GET", vm.model_data).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_details = data.data;
        if(vm.order_details.order.status == "confirm_order"){
            vm.model_data.confirmed_price = vm.order_details.data[vm.order_details.data.length - 1].ask_price;
        }
        if(vm.order_details.enq_details.expected_date && vm.model_data.from == 'pending_approval') {

          vm.model_data.expected_date = vm.order_details.enq_details.expected_date;
          vm.model_data.ask_price = vm.order_details.enq_details.ask_price;
          vm.model_data.remarks = vm.order_details.enq_details.remarks;
        }
      }
      vm.loading = false;
    })
  }
  vm.getDetails();

  vm.ok = function() {

    $modalInstance.close();
  }
};

angular
  .module('urbanApp')
    .controller('ManualOrderDetails', ['$scope', 'Service', '$modalInstance', 'items', 'Session', ManualOrderDetails]);
