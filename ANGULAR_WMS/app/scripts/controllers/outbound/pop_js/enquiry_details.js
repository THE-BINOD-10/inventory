angular.module('urbanApp', []).controller('EnquiryOrderDetails', ['$scope', 'Service', '$modalInstance', 'items',
function($scope, Service, $modalInstance, items) {

  var vm = this;
  vm.service = Service;

  vm.model_data = items;
  vm.order_details = []; 
  vm.status = 'enquiry';

  vm.loading = false;
  var url = "get_customer_enquiry_detail/";
  if (vm.model_data.url) {
    url = vm.model_data.url;
    delete vm.model_data.url;
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
