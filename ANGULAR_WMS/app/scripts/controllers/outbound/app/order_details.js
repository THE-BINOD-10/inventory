;(function(){

'use strict';

function AppOrderDetails($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.service = Service;

  vm.order_id = "";
  vm.status = "";
  vm.intermediate_order = false;
  if($stateParams.intermediate_order) {
    vm.intermediate_order = $stateParams.intermediate_order;
  }
  if($stateParams.orderId && $stateParams.state) {
    vm.order_id = $stateParams.orderId;
    vm.status = $stateParams.state;
  } else {
    $state.go("user.App.MyOrders");
  }

  var url = "get_customer_order_detail/?order_id=";
  if (vm.intermediate_order == 'true') {
    url = "get_intermediate_order_detail/?order_id=";
  }
  if(vm.status == "enquiry") {
    url = "get_customer_enquiry_detail/?enquiry_id=";
  } else if (vm.status == "manual_enquiry") {
    url = "get_manual_enquiry_detail/?user_id="+Session.userId+"&enquiry_id=";
  }
  vm.loading = true;
  vm.order_details = {}
  vm.open_order_detail = function(){

    vm.order_details = {}
    Service.apiCall(url+vm.order_id).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_details = {}
        vm.order_details = data.data;
        vm.client_name_header = data.data.order.customer_name
      }
      vm.loading = false;
    })
  }
  vm.open_order_detail();

  vm.getStatus = function(order_qty, pick_qty) {

    if(pick_qty == 0) {

      return "Open";
    } else if ((order_qty - pick_qty) == 0) {

      return "Dispatched";
    } else {

      return "Partially Dispatched";
    }
  }

  // custom orders
  //
  vm.moment = moment();
  vm.date = new Date()
  vm.disable_btn = false;
  vm.edit = function(form){
    if(form.$invalid) {
      Service.showNoty('Please fill required fields');
      return false;
    }
    vm.disable_btn = true;
    vm.model_data['user_id'] = Session.userId;
    vm.model_data['enquiry_id'] = vm.order_details.order.enquiry_id;
    vm.model_data['status'] = 'marketing_pending';
    Service.apiCall('save_manual_enquiry_data/', 'POST', vm.model_data).then(function(data) {
      if (data.message) {
        if (data.data == 'Success') {
          var temp = {};
          angular.copy(vm.model_data, temp);
          temp['username'] = Session.userName;
          temp['date'] =  vm.moment.format("YYYY-MM-DD");
          vm.order_details.data.push(temp)
          vm.model_data.ask_price = '';
          vm.model_data.extended_date = '';
          vm.model_data.remarks = '';
        }
        Service.showNoty(data.data);
      } else {
        Service.showNoty('Something went wrong');
      }
      vm.disable_btn = false;
    });
  }
  vm.clear_flag = false;
  vm.clear = function(){
    vm.clear_flag = true;
    vm.edit_enable = false;
  }

    vm.accept_or_hold = function(){
      if (vm.po_number_header && vm.client_name_header) {
        swal({
            title: "Confirm the Order or Hold the Stock!",
            text: "Custom Order Text",
            type: "warning",
            showCancelButton: true,
            confirmButtonText: "Confirm Order",
            cancelButtonText: "Block Stock",
            closeOnConfirm: true
            },
            function(isConfirm){
              // var elem = {'order_id': vm.order_id, 'uploaded_po': vm.upload_file_name};
              var elem = {'order_id': vm.order_id};
              if(isConfirm){
                  elem['status'] = 'confirm_order'
              }else{
                  elem['status'] = 'hold_order'
              }
              elem['po_number'] = vm.po_number_header;
              // var formData = new FormData();
              // var el = $("#file");
              // var files = el[0].files;
              //
              // $.each(files, function(i, file) {
              //   formData.append('po_file', file);
              // });

              // var data = {'user_id': Session.userId, 'enquiry_id': vm.order_details.order.enquiry_id}
              // $.each(elem, function(key, value) {
              //   formData.append(key, value);
              // });
              vm.service.apiCall('confirm_or_hold_custom_order/', 'POST', elem  ).then(function(data){
                    if(data.data.msg == 'Success') {
                       if(isConfirm){
                         vm.upload_po(vm.po_number_header, vm.client_name_header);
                         Service.showNoty('Order Confirmed Successfully');
                       }else{
                         Service.showNoty('Placed Enquiry Order Successfully');
                       }
                    }else{
                        Service.showNoty(data.data, 'warning');
                    }
              })
            }
          );
      } else {
        Service.showNoty('Please fill the PO Number', 'warning');
      }
    }

    vm.upload_po = function(po, name) {

      var formData = new FormData();
      var el = $("#file");
      var files = el[0].files;

      if(files.length == 0){

        return false;
      }

      $.each(files, function(i, file) {
        formData.append('po_file', file);
      });

      formData.append('po_number', po);
      formData.append('customer_name', name);

      vm.uploading = true;
      $.ajax({url: Session.url+'upload_po/',
              data: formData,
              method: 'POST',
              processData : false,
              contentType : false,
              xhrFields: {
                  withCredentials: true
              },
              'success': function(response) {
                if(response == 'Uploaded Successfully') {

                  Service.showNoty(response);
                } else {
                  Service.showNoty(response, 'warning');
                }
                vm.uploading = false;
              },
              'error': function(response) {
                console.log('fail');
                Service.showNoty('Something Went Wrong', 'warning');
                vm.uploading = false;
              }
      });
    }

  vm.image_loding = {};
  vm.remove_image = function(index) {

    var image = vm.order_details.style.images[index];
    var data = {'user_id': Session.userId, 'enquiry_id': vm.order_details.order.enquiry_id, 'image': image};
    vm.image_loding[index] = true;
    Service.apiCall('remove_manual_enquiry_image/', 'POST', data).then(function(data) {
      if (data.message) {
        if (data.data == 'Success') {
          Service.showNoty('Image Deleted Successfully');
          vm.order_details.style.images.splice(index, 1);
        } else {
          Service.showNoty(data.data, 'warning');
        }
      } else {
        Service.showNoty('Something went wrong', 'danger');
      }
      vm.image_loding[index] = false;
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

  vm.uploaded_po = '';
  $scope.uploadPo = function(args){
    vm.upload_file_name = "";
    $scope.$apply(function () {
      vm.upload_file_name = args.files;
      vm.uploaded_po = args.files[0].name;
    });
  }

  vm.uploading = false;
  vm.upload_image = function() {

    var formData = new FormData();
    var el = $("#image-upload");
    var files = el[0].files;

    $.each(files, function(i, file) {
      formData.append('po_file', file);
    });

    var data = {'user_id': Session.userId, 'enquiry_id': vm.order_details.order.enquiry_id}
    $.each(data, function(key, value) {
      formData.append(key, value);
    });
    vm.uploading = true;
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
                angular.forEach(response.data, function(url) {
                  vm.order_details.style.images.push(url);
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
}

angular
  .module('urbanApp')
  .controller('AppOrderDetails', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppOrderDetails]);

})();
