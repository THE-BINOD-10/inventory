;(function(){

'use strict';

function ProfileUpload($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  var vm = this;
  vm.service = Service;
  vm.session = Session;
  vm.title = 'Customer Profile';
  vm.first_name = vm.session.user_profile.first_name;
  vm.email = vm.session.user_profile.email;
  vm.user_id = vm.session.userId;
  vm.is_portal_lite = Session.roles.permissions.is_portal_lite;

  vm.upload_file_name = "";
  $scope.$on("fileSelected", function (event, args) {
    $scope.$apply(function () {
      vm.upload_file_name = args.file.name;
    });
  });

  vm.base = function(){

    var send = {'user_id':vm.user_id};
    Service.apiCall("get_cust_profile_info/", "POST", send).then(function(data){
      if(data.message) {
        vm.model_data = data.data.data;
      }
    });
  }
  vm.base();
  vm.logo_loading = false;
  vm.remove_image = function(logo) {
    var el = document.getElementById('logo').value;
    var image = vm.model_data.logo;
    var data = {'user_id': Session.userId, 'image': image};
    Service.apiCall("remove_customer_profile_image/", "POST", data).then(function(data){
      if (data.message == 'Success') {
        vm.model_data.logo = '';
        document.getElementById('logo').value = '';
        Service.showNoty('Image Deleted Successfully');
      }
    });
  }

  vm.logo_loading = false;
  vm.submit = function(form){

      var formData = new FormData();
      var logo_file = $('#logo')[0].files;

      if (logo_file.length > 0) {
        vm.logo_loading = true;
        $.each(logo_file, function(i, file) {
          formData.append('logo', file);
        });
      }
      formData.append('user_id', vm.user_id);
      formData.append('gst_number', vm.model_data.gst_number);
      formData.append('address', vm.model_data.address);
      formData.append('phone_number', vm.model_data.phone_number);
      formData.append('bank_details', vm.model_data.bank_details);
      $.ajax({url:Session.url+"update_cust_profile/",
               method:"POST",
               data:formData,
               processData : false,
               contentType : false,
               xhrFields: {
                 withCredentials: true},
              'success': function(response) {
                  var response = JSON.parse(response);
                  if(response.message == "success") {
                    vm.service.showNoty("Successfully updated Profile data");
                    $scope.$apply(function () {
                      vm.logo_loading = false;
                      vm.model_data.logo = response.data[0];
                    });
                  } else {
                    vm.service.pop_msg(response.message);
                    $scope.$apply(function () {
                      vm.logo_loading = false;
                    });
                  }
                }
              }).then(function(data){
        if(data.message) {
          console.log(data.message);
        }
      });
  }
}

angular
  .module('urbanApp')
    .controller('ProfileUpload', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', ProfileUpload]);
})();
