'use strict';

function RegisterCtrl($rootScope ,$scope, $state, $http, Auth, Session, Service) {

  var vm = this;
  vm.session = Session;
  vm.service = Service;

  vm.step = 1;
  vm.upload_status = true;
  vm.upload_file = "";

  //step status
  vm.service.apiCall("get_update_setup_state/").then(function(data){

    if(data.message) {

      if (data.data.data.current_state == "") {
        change_state("1");
      } else if(data.data.data.current_state == "1") {
        change_state("2");
      } else if(data.data.data.current_state == "2") {
        change_state("3");
      }
    }
  })

  function change_state(step) {

    var state = Number(step);
    vm.step = state;
    vm.title = vm.titles[state - 1];
    vm.upload_file = "";
    $state.go("app.Register."+vm.states[state - 1]);
    vm.upload_status = true;
  }

  //step 1 
  $scope.files = [];
  $scope.$on("fileSelected", function (event, args) {
        $scope.$apply(function () {
            $scope.files.push(args.file);
            $scope.uploadFile(args.url);
        });
    });
  $state.go("app.Register.One");
  $scope.uploadFile = function(data){
    var file = $scope.files[0];
               
    var uploadUrl = Session.url+data;

    var fd = new FormData();
    fd.append('files', file);

    $http.post(uploadUrl, fd, {
      transformRequest: angular.identity,
      headers: {'Content-Type': undefined}
    })
    .success(function(data){
      if (data == "Success") {
        vm.upload_status = false;
        vm.upload_file = "Uploaded";
        vm.service.apiCall("get_update_setup_state/", "POST", {step_count: vm.step})
      } else {
        vm.upload_status = true;
        vm.upload_file = "Invalid File";
      }
      $scope.files = [];
    })
    .error(function(){
      vm.upload_status = true;
      $scope.files = [];
      vm.upload_file = "Invalid File";
    }); 
  };

  vm.states = ["One", "Two", "Three"];
  vm.titles = ["Setup your warehouse","Add Products","Add Product-Location Mapping"];
  vm.title = vm.titles[0];
  vm.state_change = function() {

    if(!(vm.upload_status) && (vm.step < 3)) {
      Auth.status();
      vm.step = vm.step + 1;
      vm.title = vm.titles[vm.step-1];
      vm.upload_file = "";
      $state.go("app.Register."+vm.states[vm.step-1]);
      vm.upload_status = true;
    } else if (vm.step == 3) {

      vm.completed = true;
      $state.go("app.Register.Completed");
    }
  }

  vm.skip = function () {

    vm.service.apiCall("load_demo_data/?first_time=true")
    vm.completed = true;
    $state.go("app.Register.Completed");
  }

  /*window.onhashchange = function() {
    console.log("back");
    //$state.go('app.Register.'+vm.states[vm.step-1], {}, { reload: true});
  }*/

  vm.completed = false;
  vm.dashboard = function() {

    Session.roles.permissions["setup_status"] = false;
    $state.go("app.dashboard");
  }
}

angular
  .module('urbanApp')
  .controller('RegisterCtrl', ['$rootScope' ,'$scope', '$state', '$http', 'Auth', 'Session', 'Service', RegisterCtrl]);
