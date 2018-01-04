;(function(){

'use strict';

var app = angular.module('urbanApp');

app.controller('CorporateOrders', ['$scope', 'Service', 'Data', '$modal', 'Session', CorporateOrders]);

function CorporateOrders($scope, Service, Data, $modal, Session) {

  var vm = this;

  vm.you_orders = false;
  vm.orders_loading = false;
  vm.order_data = {data: []};
  vm.index = '';
  vm.show_no_data = false;
  vm.get_orders = function(){

    vm.orders_loading = true;

    vm.index = vm.order_data.data.length  + ':' + (vm.order_data.data.length + 20)
    var data = {index: vm.index}
    Service.apiCall("pending_pos/", 'GET', data).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_data.data = vm.order_data.data.concat(data.data.data);
        Data.corporate_orders = vm.order_data.data;
        if(data.data.data.length == 0) {
          vm.show_no_data = true
        }
      }
      vm.orders_loading = false;
    })
  }

  if (!Data.corporate_orders) {
    vm.get_orders();
  } else {
    vm.order_data.data = Data.corporate_orders;
  }

  // Scrolling Event Function
  vm.scroll = function(e) {
    console.log("scroll")
    if($(".your_orders:visible").length && !vm.orders_loading && !vm.show_no_data) {
        vm.get_orders();
    }
  }

  vm.uploadPO = function(order, index) {

    var formData = new FormData();
    var el = $("#"+order.po_number);
    var files = el[0].files;

    if(files.length == 0){

      Service.showNoty("Please Select File", "success", "topRight");
      return false;
    }

    $.each(files, function(i, file) {
      formData.append('po_file', file);
    });

    angular.forEach(order, function(value, key){

      formData.append(key, value);
    })

    order.uploading = true;
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

                vm.order_data.data.splice(index, 1);
                Data.corporate_orders = vm.order_data.data;
                Service.showNoty(response);
              } else {
                Service.showNoty(response, 'warning');
              }
              order.uploading = false;
            },
            'error': function(response) {
              console.log('fail');
              Service.showNoty('Something Went Wrong', 'warning');
              order.uploading = false;
            }
    });
  }
}

})();
