'use strict';

function AttributesPOP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $q, $modalInstance, items) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;
  vm.input_types = ['Input', 'Number', 'Textarea'];

  vm.empty_data = {'id': '', 'attribute_name': '', 'attribute_type': 'Input'}

  vm.pop_data = {};
  vm.status_data = "";
  vm.status_data = [];

  vm.getAttrData = function(){
    vm.service.apiCall('get_user_attributes_list/', "GET", {attr_model: 'sku'}).then(function(data){
      data = data.data;
      if(data.status && data.data.length) {
        vm.status_data = vm.status_data.concat(data.data);
      }
      else {
        vm.status_data.push(vm.empty_data);
      }
      console.log(vm.status_data);
    });
  }
    vm.getAttrData();
//  }
//
//  vm.getPoData(items);
//
//  function check_exist(sku_data, index) {
//
//    var d = $q.defer();
//    for(var i = 0; i < vm.pop_data.data.length; i++) {
//
//      if(vm.pop_data.data[i].$$hashKey != sku_data.$$hashKey && vm.pop_data.data[i].product_code == sku_data.product_code) {
//
//        d.resolve(false);
//        vm.pop_data.data.splice(index, 1)
//        alert("It is already exist in index");
//        break;
//      } else if( i+1 == vm.pop_data.data.length) {
//        d.resolve(true);
//      }
//    }
//    return d.promise;
//  }
//
//  vm.get_product_data = function(item, sku_data, index) {
//      console.log(vm.pop_data);
//      check_exist(sku_data, index).then(function(data){
//        if(data) {
//          var elem = $.param({'sku_code': item});;
//          $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
//          $http({
//               method: 'POST',
//               url:Session.url+"get_material_codes/",
//               withCredential: true,
//               data: elem}).success(function(data, status, headers, config) {
//                 // sku_data.sub_data = data;
//
//                 sku_data.sub_data = data.materials;
//                 sku_data.product_description = 1;
//                 sku_data.description = data.product.description;
//            console.log("success");
//          });
//        }
//      });
//  }
//
  vm.add_attribute = function () {
      var temp = {};
      angular.copy(vm.empty_data,temp);
      vm.status_data.push(temp);
  }


  vm.save_attribute = function() {
      var elem = angular.element($('form:visible'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem.push({name:"attr_model", value:"sku"})
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      Service.apiCall("save_update_attribute/", "POST", elem, true).then(function(data){
        if(data.data.message == 'Updated Successfully') {
          $modalInstance.close(vm.status_data);
        }
        else {
              vm.service.pop_msg(data.data)
        }
      });
  }
//
//  vm.print = print;
//  function print() {
//      colFilters.print_data(vm.html);
//  }
//
  vm.delete_attr = function(data, index) {
      debugger;
      if (data.id) {
        vm.update_attr_status(data);
      }
      else {
        vm.status_data.splice(index,1);
      }
  }
//
//  vm.remove_product = function (data) {
//      angular.forEach(vm.pop_data.data, function(item, index){
//        if (item.$$hashKey == data.$$hashKey) {
//          vm.pop_data.data.splice(index, 1);
//        }
//      });
//  }
//  vm.update_data_order = function(index, data, last) {
//    console.log(data);
//    if (last) {
//      var total = 0;
//      for(var i=0; i < data.sub_data.length; i++) {
//        total = total + parseInt(data.sub_data[i].picked_quantity);
//      }
//      if(total < data.reserved_quantity) {
//        var clone = {};
//        angular.copy(data.sub_data[index], clone);
//        clone.picked_quantity = data.reserved_quantity - total;
//        data.sub_data.push(clone);
//      }
//    } else {
//      data.sub_data.splice(index,1);
//    }
//  }
//
//  vm.cal_quantity = cal_quantity;
//  function cal_quantity(record, data) {
//    console.log(record);
//    var total = 0;
//    for(var i=0; i < data.sub_data.length; i++) {
//        total = total + parseInt(data.sub_data[i].picked_quantity);
//    }
//    if(data.reserved_quantity >= total){
//      console.log(record.picked_quantity)
//    } else {
//      var quantity = data.reserved_quantity-total;
//      if(quantity < 0) {
//        quantity = total - parseInt(record.picked_quantity);
//        quantity = data.reserved_quantity - quantity;
//        record.picked_quantity = quantity;
//      } else {
//        record.picked_quantity = quantity;
//      }
//    }
//  }
//
//  vm.isLast = isLast;
//  function isLast(check) {
//
//    var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
//    return cssClass;
//  }
//
  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
}

angular
  .module('urbanApp')
  .controller('AttributesPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$q', '$modalInstance', 'items', AttributesPOP]);
