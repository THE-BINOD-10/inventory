;(function(){

'use strict';

function ProfileUpload($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  var vm = this;
  vm.service = Service;
  vm.session = Session;
  vm.title = 'Customer Profile';
  vm.first_name = vm.session.user_profile.first_name;
  vm.email = vm.session.user_profile.email;

  vm.upload_file_name = "";
  $scope.$on("fileSelected", function (event, args) {
    $scope.$apply(function () {
      vm.upload_file_name = args.file.name;
    });
  });

  vm.submit = function(form){
    
    if (!($("#logo")[0].files.length)){
      vm.service.showNoty("Please select logo to upload");
    } else {
      var formdata = $('#form').serializeArray();
      formdata.push({'name':'logo', 'value':$('#logo')[0].files});
      Service.apiCall("upload_logo/", "GET", formdata).then(function(data){
        if(data.message) {
          console.log(data.message);
        }
      });
    }
  }
}

angular
  .module('urbanApp')
    .controller('ProfileUpload', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', ProfileUpload]);
})();
