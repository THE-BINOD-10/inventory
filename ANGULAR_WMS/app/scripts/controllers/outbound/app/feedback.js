;(function(){

'use strict';

function feedBackForm($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  var vm = this;
  vm.service = Service;
  vm.session = Session;
  vm.title = 'Customer Profile';
  vm.first_name = vm.session.user_profile.first_name;
  vm.email = vm.session.user_profile.email;
  vm.user_id = vm.session.userId;
  vm.user_type = Session.roles.permissions.user_type
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
    var elem = {category: '', is_catalog:true, customer_id: Session.userId, file: true}
    vm.styles_loading = true;
    vm.styles = [];
    Service.apiCall("get_sku_catalogs/", "POST", elem).then(function(data) {
      if(data.message) {
        vm.styles = data.data.data;
      }
      vm.styles_loading = false;
    });
    vm.feedBackType = ['Product Complaint', 'Product Suggestion', 'Technical Support', 'Product Feedback', 'Others']
  }
  vm.base();
  vm.logo_loading = false;
  vm.submit = function(form){
    vm.temp_images_files =[]
    if(form.$valid) {
      var formData = new FormData();
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var el = $("#image-upload");
      if (el.length) {
        var files = el[0].files;
      }
      $.each(files, function(i, file) {
        formData.append('files-' + i, file);
      });
      $.each(elem, function(i, val) {
          formData.append(val.name, val.value);
      });
      $.ajax({url:Session.url+"create_feedback_form/",
               method:"POST",
               data:formData,
               processData : false,
               contentType : false,
               xhrFields: {
                 withCredentials: true},
              'success': function(response) {
//                  var response = JSON.parse(response);
                  if(response.message == "success") {
                    vm.service.showNoty("Successfully updated Feedback data");
                    vm.clearFiles()
                  } else {
                    vm.service.pop_msg(response.message);                  }
                }
              }).then(function(data){
        if(data.message) {
          console.log(data.message);
        }
      });
    } else {
      vm.service.showNoty("Please Enter the required Fields");
    }
  }
  var imagesPreview = function(input, placeToInsertImagePreview) {
    if (input.files) {
      var filesAmount = input.files.length;
      for (var i = 0; i < filesAmount; i++) {
        var reader = new FileReader();
        reader.onload = function(event) {
          if(filesAmount == 1) {
            $($.parseHTML('<div class="col-lg-8 col-md-8 col-sm-12 col-xs-12 dyn_imgs no-padding m5" align="center"><img src="'+event.target.result+'" width="100%"></div>')).appendTo(placeToInsertImagePreview);
          } else {
            $($.parseHTML('<div class="col-md-3 dyn_imgs no-padding m5"><img src="'+event.target.result+'" width="100%"></div>')).appendTo(placeToInsertImagePreview);
          }
        }
        reader.readAsDataURL(input.files[i]);
      }
    }
  };
  $('#image-upload').on('change', function() {
    $("div.multi_imgs_display").empty();
    imagesPreview(this, 'div.multi_imgs_display');
  });

  vm.clearFiles = function(){
    $('#image-upload').val('');
    $("div.multi_imgs_display").empty();
    vm.model_data.feedbackType = '';
    vm.model_data.sku = '';
    vm.model_data.url = '';
    vm.model_data.remarks = ''
    vm.model_data.sku_id = ''
  }

  vm.upload_name = [];
  $scope.$on("fileSelected", function (event, args) {
    $scope.$apply(function () {
      vm.upload_name = [];
      if (args.msg == 'success') {
        angular.forEach(args.file, function(data){
          vm.upload_name.push(data.name)
        })
      } else {
        Service.showNoty(args.msg, 'warning');
      }
    });
  });
}

angular
  .module('urbanApp')
    .controller('feedBackForm', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', feedBackForm]);
})();
