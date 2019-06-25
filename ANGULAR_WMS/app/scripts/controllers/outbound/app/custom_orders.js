FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('CustomOrdersTbl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.order_id = "";
    vm.status = "";
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.user_type = vm.permissions.user_type;
    vm.service = Service;
    vm.display = true;

    //default values
    if(!vm.permissions.grn_scan_option) {
      vm.permissions.grn_scan_option = "sku_serial_scan";
    }
    if(!vm.permissions.barcode_generate_opt) {
      vm.permissions.barcode_generate_opt = 'sku_code';
    }
    if(vm.permissions.barcode_generate_opt == 'sku_ean') {
      vm.permissions.barcode_generate_opt = 'sku_code';
    }

    //process type;
    vm.po_qc = true;
    vm.po_qc = (vm.permissions.receive_process == "receipt-qc")? true: false;
    vm.g_data = Data.receive_po;

    var sort_no = (vm.g_data.style_view)? 1: 0;
    vm.filters = {'datatable': 'CustomOrdersTbl', 'search0':'', 'search1':'', 'search2': '', 'search3': ''};
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('order', [sort_no, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        })
        .withOption('headerCallback', function(header) {
            if (!vm.headerCompiled) {
                vm.headerCompiled = true;
                $compile(angular.element(header).contents())($scope);
            }
        })
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    var columns = ['ID', 'Enquiry ID', 'Enquiry Date', 'Customer Name', 'Style Name', 'Customization', 'SKU Code', 'Status'];
    vm.dtColumns = vm.service.build_colums(columns);

    var row_click_bind = 'td';
    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
      $(row_click_bind, nRow).unbind('click');
      $(row_click_bind, nRow).bind('click', function() {
        $scope.$apply(function() {
          let url = "get_manual_enquiry_detail/?user_id="+Session.userId+"&enquiry_id=";
          vm.service.apiCall(url+aData['ID']).then(function(data){
            if(data.message) {
              vm.order_details = data.data;
              if(vm.order_details.data == 'Get Manual Enquiry Detail Failed'){
                Service.showNoty(vm.order_details.data, 'warning');
              }else {
                vm.order_id = vm.order_details.order.id;
                vm.status = 'manual_enquiry';
                vm.title = "Custom Order";
                $state.go('user.App.MyOrders.CustomOrder');
              }
            }
          });
        });
      });
      return nRow;
    }

  vm.close = function() {
    $state.go('user.App.MyOrders', {'state': 'orders'})
    vm.dtInstance.reloadData();
  }
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
    vm.model_data['enquiry_id'] = vm.order_details.order.id;
    vm.model_data['enq_status'] = 'marketing_pending';
    Service.apiCall('save_manual_enquiry_data/', 'POST', vm.model_data).then(function(data) {
      if (data.message) {
        if (data.data == 'Success') {
          var temp = {};
          angular.copy(vm.model_data, temp);
          temp['username'] = Session.userName;
          temp['date'] =  vm.moment.format("YYYY-MM-DD");
          vm.order_details.data.push(temp)
          vm.model_data.ask_price = '';
          vm.model_data.expected_date= ''
          vm.model_data.remarks = '';
          Service.showNoty(data.data);
          vm.dtInstance.reloadData();
        }
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
    // vm.model_data.ask_price = '';
    vm.model_data.expected_date= ''
    vm.model_data.remarks = '';
  }

  vm.accept_or_hold = function(){
    vm.client_name_header = vm.order_details.order.customer_name;
    if (vm.po_number_header && vm.client_name_header) {
      swal({
          title: "Confirm the Order or Hold the Stock!",
          text: "Custom Order Text",
          type: "warning",
          showCancelButton: true,
          confirmButtonText: "Confirm Order",
          closeOnConfirm: true
          },
          function(isConfirm){
            // var elem = {'order_id': vm.order_id, 'uploaded_po': vm.upload_file_name};
            if (!vm.upload_file_name) {
              Service.showNoty('Upload the Image First', 'warning');
              return false;
            }
            var elem = {'order_id': vm.order_id};
            if(isConfirm){
                elem['enq_status'] = 'confirm_order'
            }else{
                 return false;
            }
            elem['po_number'] = vm.po_number_header;
            vm.service.apiCall('confirm_or_hold_custom_order/', 'POST', elem).then(function(data){
              if(data.data.msg == 'Success') {
                 if(isConfirm) {
                   vm.upload_po(vm.po_number_header, vm.client_name_header);
                   Service.showNoty('Order Confirmed Successfully');
                   vm.dtInstance.reloadData();
                   vm.po_number_header = '';
                   vm.client_name_header = '';
                 } else {
                   Service.showNoty('Placed Enquiry Order Successfully');
                 }
              } else {
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
            vm.dtInstance.reloadData();
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
          vm.dtInstance.reloadData();
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
        vm.upload_image(args.file);
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
  vm.upload_image = function(image_files) {

    var formData = new FormData();
    var files = image_files;

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
})();
