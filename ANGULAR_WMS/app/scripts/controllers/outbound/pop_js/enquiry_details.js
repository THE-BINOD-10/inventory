angular.module('urbanApp', []).controller('EnquiryOrderDetails', ['$scope', 'Service', '$modalInstance', 'items',
function($scope, Service, $modalInstance, items) {

  var vm = this;
  vm.service = Service;

  vm.model_data = items;
  vm.order_details = []; 
  vm.status = 'enquiry';
  vm.date = new Date();

  vm.extend_status = ['Pending', 'Approval', 'Rejected'];

  vm.loading = false;
  var url = "get_customer_enquiry_detail/";
  if (vm.model_data.url) {
    url = vm.model_data.url;
    delete vm.model_data.url;
  }

  vm.confirm_to_extend = function(){
    
    if (vm.extend_type && vm.extended_date) {
      vm.model_data['extend_status'] = vm.extend_type;
      vm.model_data['extended_date'] = vm.extended_date;

      Service.apiCall('extend_enquiry_date/', 'GET', vm.model_data).then(function(data) {
        if (data.message) {
          Service.showNoty('Extend status changed');
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
      }   
      vm.loading = false;
    })  
  }
  vm.getDetails();

  vm.ok = function() {

    $modalInstance.close();
  }
}]);
