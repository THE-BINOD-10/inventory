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

  vm.upload_name = [];
  $scope.$on("fileSelected", function (event, args) {
    $scope.$apply(function () {
      vm.upload_name = [];
      if (args.msg == 'success') {
        angular.forEach(args.file, function(data){vm.upload_name.push(data.name)});
        vm.upload_image();
      } else {
        Service.showNoty(args.msg, 'warning');
      }
    });
  });

  vm.uploading = false;
  vm.upload_image = function() {

    var formData = new FormData();
    var el = $("#image-upload1");
    var files = el[0].files;

    $.each(files, function(i, file) {
      formData.append('po_file', file);
    });

    var data = {'user_id': Session.userId, 'enquiry_id': vm.order_details.order.enquiry_id,
                'enq_det_id': vm.order_details.order.enq_det_id}
    $.each(data, function(key, value) {
      formData.append(key, value);
    });
    vm.uploading = true;
    vm.art_image_uploaded = false;
    $.ajax({url: Session.url+'save_manual_enquiry_image/',
          data: formData,
          method: 'POST',
          processData : false,
          contentType : false,
          xhrFields: {
              withCredentials: true
          },
          'success': function(response) {
            response = JSON.parse(response);
            if(response.msg == 'Success') {

              Service.showNoty(response.msg);
              $scope.$apply(function() {
                vm.upload_name = [];
                vm.uploading = false;
                vm.art_image_uploaded = true;
                angular.forEach(response.data, function(url) {
                  vm.order_details.style.art_images.push(url);
                })
              });
              $("input[type='file']").val('');
            } else {
              Service.showNoty(response.msg, 'warning');
              $scope.$apply(function() { vm.uploading = false; })
            }
          },
          'error': function(response) {
            console.log('fail');
            Service.showNoty('Something Went Wrong', 'warning');
            $scope.$apply(function() { vm.uploading = false; })
          }
    });
  }


  vm.disable_btn = false;
  vm.notify_to_designer = function(form){
    vm.disable_btn = true;
    var designer_elems = {};
    angular.copy(vm.model_data, designer_elems);
    designer_elems['enq_status'] = 'pending_artwork';
    vm.service.apiCall('notify_designer/', 'POST', designer_elems).then(function(data) {
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

  vm.convert_customorder_to_enquiryorder = function() {
  elem = {};
  angular.copy(vm.model_data, elem);
    vm.service.apiCall('convert_customorder_to_enquiryorder/', 'POST', elem).then(function(data){
        if(data.data.msg == 'Success'){
          $modalInstance.close();
          Service.showNoty('Enquiry Order Placed Successfully');
        }else{
          Service.showNoty(data.data, 'warning');
        }
    })
  }

  vm.upload_artwork = function() {
    if (!vm.art_image_uploaded){
      Service.showNoty('Upload the image first');
      return;
    }
    var data = {};
    angular.copy(vm.model_data, data);
    data['status'] = "artwork_submitted";
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

  vm.calcuateExpectedDate = function(){
    var numberOfDaysToAdd = parseInt(vm.model_data.lead_time);
    var farthesWarehouseLt = parseInt(vm.order_details.far_wh_leadtime);
    var currentDate = new Date();
    currentDate.setDate(currentDate.getDate() + numberOfDaysToAdd + farthesWarehouseLt);
    var dd = currentDate.getDate();
    var mm = currentDate.getMonth() + 1;
    var y = currentDate.getFullYear();
    vm.model_data.expected_date = mm + '/'+ dd + '/'+ y;
  }


  vm.send_for_approval = function(form) {

    if(vm.model_data.ask_price || vm.model_data.expected_date || vm.model_data.remarks) {

      if(!vm.model_data.ask_price && vm.order_details.order.customization_type != 'Product Customization') {
        Service.showNoty('Please Fill Ask Price', 'warning');
        return false;
      } else if (!vm.model_data.expected_date && vm.permissions.user_type != 'sm_purchase_admin') {
        Service.showNoty('Please Fill Expected Date', 'warning');
        return false;
      } else if (!vm.model_data.remarks) {
        Service.showNoty('Please Fill Remarks', 'warning');
        return false;
      }else if (!vm.model_data.lead_time && vm.permissions.user_type == 'sm_purchase_admin') {
        Service.showNoty('Please Fill Lead Time in Days', 'warning');
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
        if(vm.order_details.order.status == "confirm_order" || vm.order_details.order.status == 'hold_order'){
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
