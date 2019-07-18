function EnquiryOrderDetails ($scope, Service, $modalInstance, items, Session) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;

  vm.model_data = items;
  vm.order_details = {};
  vm.status = 'enquiry';
  vm.date = new Date();

  vm.extend_statuses = ['pending', 'approval', 'rejected'];

  vm.loading = false;
  var url = "get_customer_enquiry_detail/";
  if (vm.model_data.url) {
    url = vm.model_data.url;
    delete vm.model_data.url;
  }

  vm.confirm_to_extend = function(){

    if (vm.order_details.extend_status && vm.order_details.extend_date) {
      vm.model_data['extend_status'] = vm.order_details.extend_status;
      vm.model_data['extended_date'] = vm.order_details.extend_date;

      Service.apiCall('extend_enquiry_date/', 'GET', vm.model_data).then(function(data) {
        if (data.message) {
          if (data.data == 'Admin'){
            Service.showNoty('Only Admin can process ');
          } else {
              Service.showNoty('Extend status changed');
          }
        } else {
          Service.showNoty('Something went wrong');
        }
      });
    } else {
      Service.showNoty('Please fill with extend status type and date');
    }
  }

  vm.getDetails = function() {

    vm.loading = true;
    Service.apiCall(url, "GET", vm.model_data).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_details = data.data;
        if(vm.order_details.extend_date) {
          var date = vm.order_details.extend_date.split("-")
          vm.order_details.extend_date = date[1]+"/"+date[2]+"/"+date[0];
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
  .controller('EnquiryOrderDetails', ['$scope', 'Service', '$modalInstance', 'items', 'Session', EnquiryOrderDetails]);
