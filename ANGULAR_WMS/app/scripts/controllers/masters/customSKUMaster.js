'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CustomSKUMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$rootScope', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $rootScope) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'CustomSKUMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':''}
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
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Template Name').withTitle('Template Name'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date')
    ];

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              vm.service.apiCall('get_product_properties/?data_id='+aData.DT_RowAttr['data-id']).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  vm.update = true;
                  vm.title = "Update Custom SKU";
                  $state.go('app.masters.CustomSKUMaster.AddCustomSKU');
                }
              });
            });
        });
    }

  var empty_data = {name:'', property_name: '', property_type:'', selected_cats: [], attributes: [{attribute_name:'', description:'', new: true}]};
  vm.model_data = {};
  vm.template_types = {};
  vm.template_values= [];
  vm.base = function() {

    vm.title = "Add Custom SKU";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
    vm.service.apiCall('get_sku_field_names/').then(function(data){
      if(data.message) {
        vm.template_types = data.data.template_types;  
        vm.model_data.property_type = vm.template_types[0].field_name;
        vm.template_values = vm.template_types[0].field_data;
        vm.model_data.property_name = vm.template_values[0];
      }
    })
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.CustomSKUMaster');
  }

  vm.add = add;
  function add() {

    vm.base();
    $state.go('app.masters.CustomSKUMaster.AddCustomSKU');
    vm.multiRefresh("brands");
    vm.multiRefresh("cats");
    vm.multiRefresh("sizes");
  } 

  vm.change_template_values = function(){

    angular.forEach(vm.template_types, function(data) {
      if(vm.model_data.property_type == data.field_name){
        vm.template_values = data.field_data;
        vm.model_data.property_name = vm.template_values[0];
      }
    })
  }

  vm.custom = function(url, form) {
    var elem = $(form).serializeArray()
    var formData = new FormData()
    var files = $("form").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });

    $.each(elem, function(i, val) {
        formData.append(val.name, val.value);
    });

    $rootScope.process = true;
    $.ajax({url: Session.url+url,
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              if(response.indexOf("Success") > -1) {
                vm.service.refresh(vm.dtInstance);
                vm.close();
              } else {
                vm.service.pop_msg(response);
              }
              $rootScope.process = false;
            }});
  }

  vm.submit = submit;
  function submit(data) {
    if (data.$valid) {
      vm.custom('create_update_custom_sku_template/', form);
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

  vm.remove_attribute = function(index,attribute) {

   if(vm.update) {
     vm.service.apiCall('delete_product_attribute/?data_id='+attribute.id+"&name="+vm.model_data.name);
   }
   vm.model_data.attributes.splice(index, 1);
  }

  vm.brands = [];
  vm.catss = []
  //Get all brands
  vm.getBrands = function() {

    vm.service.apiCall("get_sku_categories/").then(function(data){
      if (data.message) {

        vm.brands = data.data.brands;
        vm.catss = data.data.categories;
        vm.multiRefresh("brands")
      }
    })
  }

  vm.getBrands();

  // On change of brands
  vm.changeCat = function(brand) {

    console.log(brand);
    if(!brand) {

      vm.cats = [];
      vm.multiRefresh("cats")
    } else if(brand.length > 0) {

      vm.getCats(brand);
    } else {
      vm.cats = [];
      vm.multiRefresh("cats")
    }
  }

  vm.cats = [];
  // Get categories
  vm.getCats = function(brands) {

    var send = brands.join("<<>>")
    vm.service.apiCall("get_categories_list/?brand="+send).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.cats = data.data;
        vm.multiRefresh("cats");
       }
    })
  }

  vm.sizes = [];
  //get all size names
  vm.getSizes = function() {

    vm.service.apiCall("get_size_names/").then(function(data){

      console.log(data.data);
      if(data.message) {

        vm.sizes = data.data.size_names;
        vm.multiRefresh("sizes");
      }
    })
  }
  vm.getSizes();

  vm.multiRefresh = function(name) {

    $timeout(function() {
      $("."+name).chosen("destroy");
      $("."+name).chosen();
    }, 500);
  }

  vm.changeCatList = function(data){

    console.log(data);
  }
}

