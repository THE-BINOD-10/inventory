angular.module('urbanApp', []).controller('ManualOrderDetails', ['$scope', 'Service', '$modalInstance', 'items', 'Session',
function($scope, Service, $modalInstance, items, Session) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;

  vm.model_data = items;
  vm.order_details = {};
  vm.status = 'enquiry';
  vm.save = true;
  vm.date = new Date();

  vm.extend_statuses = ['pending', 'approval', 'rejected'];

  vm.loading = false;
  var url = "get_manual_enquiry_detail/";
  if (vm.model_data.url) {
    url = vm.model_data.url;
    delete vm.model_data.url;
  }

  vm.disable_btn = false;
  vm.send_for_approval = function(form){
    if(form.$invalid) {
      Service.showNoty('Please fill required fields');
      return false;
    }
    vm.disable_btn = true;
    Service.apiCall('save_manual_enquiry_data/', 'POST', vm.model_data).then(function(data) {
      if (data.message) {
        if (data.data == 'Success') {
          $modalInstance.close();
        }
        Service.showNoty(data.data);
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
      }
      vm.loading = false;
    })
  }
  vm.getDetails();

  vm.ok = function() {

    $modalInstance.close();
  }
}]);
