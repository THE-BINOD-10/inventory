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

  vm.submit = function(form){

      var formData = new FormData();
      var logo_file = $('#logo')[0].files;

      if (logo_file.length > 0) {
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
                  } else {
                    vm.service.pop_msg(response.message);
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
