'use strict';

function BackorderJOPOP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $q, $modalInstance, items) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;
  vm.units = vm.service.units;

   vm.empty_data = {"title": "Update Job Order", "data": [{"product_code": "", "sub_data": [{"material_code": "", "material_quantity": '', "id": ''}], "product_description":'', 'new_sku': true}], "jo_reference": ""}

  vm.pop_data = {};
  vm.status_data = ""

  vm.getPoData = function(data){

    data = data.data;
    var url = "generate_order_jo_data/";
    if (items.url) {
      url = items.url;
    }
    Service.apiCall(url, "POST", data, true).then(function(data){
      if(data.message) {

        angular.copy(data.data, vm.pop_data);
        angular.forEach(vm.pop_data.data, function(temp){
          if(temp.sub_data.length == 0) {
            temp["sub_data"] = [{material_code: "", material_quantity: ""}];
          }
        });
      }
    });
  }

  vm.getPoData(items);

  function check_exist(sku_data, index) {

    var d = $q.defer();
    for(var i = 0; i < vm.pop_data.data.length; i++) {

      if(vm.pop_data.data[i].$$hashKey != sku_data.$$hashKey && vm.pop_data.data[i].product_code == sku_data.product_code) {

        d.resolve(false);
        vm.pop_data.data.splice(index, 1)
        alert("It is already exist in index");
        break;
      } else if( i+1 == vm.pop_data.data.length) {
        d.resolve(true);
      }
    }
    return d.promise;
  }

  vm.get_product_data = function(item, sku_data, index) {
      console.log(vm.pop_data);
      check_exist(sku_data, index).then(function(data){
        if(data) {
          var elem = $.param({'sku_code': item});;
          $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
          $http({
               method: 'POST',
               url:Session.url+"get_material_codes/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
                 // sku_data.sub_data = data;

                 sku_data.sub_data = data.materials;
                 sku_data.product_description = 1;
                 sku_data.description = data.product.description;
            console.log("success");
          });
        }
      });
  }

  vm.add_product = function () {
      var temp = {};
      angular.copy(vm.empty_data.data[0],temp);
      temp.sub_data[0]['new_sku'] = true;
      vm.pop_data.data.push(temp);
  }

  vm.html = ""
  vm.print_enable = false;
  vm.confirm_jo = function() {
      var elem = angular.element($('form:visible'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      Service.apiCall("confirm_jo/", "POST", elem, true).then(function(data){
        if(data.message) {
            if(data.data.search("<div") != -1) {
              vm.html = $(data.data)[0];
              var html = $(vm.html).closest("form").clone();
              angular.element(".modal-body:visible").html($(html).find(".modal-body > .form-group"));
              vm.print_enable = true;
            } else {
              vm.service.pop_msg(data.data)
            }
        }
      });
  }

  vm.print = print;
  function print() {
      colFilters.print_data(vm.html);
  }

  vm.update_data = function(data, index, last, first) {
      if (first && !(last)) {
        vm.remove_product(data);
      } else if (last) {
        data.sub_data.push({"material_code": "", "material_quantity": '' ,'new_sku': true})
      } else {
        data.sub_data.splice(index,1);
      }
  }

  vm.remove_product = function (data) {
      angular.forEach(vm.pop_data.data, function(item, index){
        if (item.$$hashKey == data.$$hashKey) {
          vm.pop_data.data.splice(index, 1);
        }
      });
  }
  vm.update_data_order = function(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].picked_quantity);
      }
      if(total < data.reserved_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.picked_quantity = data.reserved_quantity - total;
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {
    console.log(record);
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].picked_quantity);
    }
    if(data.reserved_quantity >= total){
      console.log(record.picked_quantity)
    } else {
      var quantity = data.reserved_quantity-total;
      if(quantity < 0) {
        quantity = total - parseInt(record.picked_quantity);
        quantity = data.reserved_quantity - quantity;
        record.picked_quantity = quantity;
      } else {
        record.picked_quantity = quantity;
      }
    }
  }

  vm.isLast = isLast;
  function isLast(check) {

    var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
    return cssClass;
  }

  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
}

angular
  .module('urbanApp')
  .controller('BackorderJOPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$q', '$modalInstance', 'items', BackorderJOPOP]);
