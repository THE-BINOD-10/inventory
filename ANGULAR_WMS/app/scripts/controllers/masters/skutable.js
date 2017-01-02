'use strict';

var app = angular.module('urbanApp', ['datatables'])
app.controller('SKUMasterTable',['$scope', '$http', '$state', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', '$log', 'colFilters' , 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, $log, colFilters, Service) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;

    vm.filters = {'datatable': 'SKUMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':'', 'search6': ''}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url:  Session.url+'results_data/',
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

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('WMS SKU Code').withTitle('WMS SKU Code').renderWith(function(data, type, full, meta) {
                        full.image_url = vm.service.check_image_url(full.image_url);
                        return '<img style="width: 35px;height: 40px;display: inline-block;margin-right: 10px;" src='+full.image_url+'>'+'<p style=";display: inline-block;">'+ full['WMS SKU Code'] +'</p>';
                        }),
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
        DTColumnBuilder.newColumn('SKU Type').withTitle('SKU Type'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
        DTColumnBuilder.newColumn('SKU Class').withTitle('SKU Class'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('Status').withTitle('Status').renderWith(function(data, type, full, meta) {
                          return vm.service.status(data);
                        }).withOption('width', '80px')
    ];

    var empty_data = {
                      sku_data:{
                        sku_code:"",
                        wms_code:"",
                        sku_group:"",
                        sku_desc:"",
                        sku_type:"",
                        zone:"",
                        sku_class:"",
                        sku_category:"",
                        threshold_quantity:"",
                        online_percentage:"",
                        status:0,
                        qc_check:1,
                        sku_brand: "",
                        sku_size: "",
                        style_name: "",
                        image_url:"images/wms/dflt.jpg",
                      },
                      "zones":[],
                      "groups":[],
                      "market_data": [{
                        "market_id":"",
                        "market_sku_type":"",
                        "marketplace_code":"",
                        "description":"",
                        "disable": false,
                        }
                      ],
                      "market_list":["Flipkart","Snapdeal","Paytm","Amazon","Shopclues","HomeShop18","Jabong","Indiatimes","Myntra"],
                      "sizes_list":[]
                    }
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.update_data = {};
    vm.zone_id = "red";
    vm.status_data = ['Inactive','Active'];
    vm.sku_types = ['', 'FG', 'RM'];
    vm.status = vm.status_data[0];
    vm.qc_data = ['Disable','Enable'];
    vm.qc = vm.qc_data[0]
    vm.market_list = [];
    vm.market;
    vm.market_data = [];
    vm.files = [];
    $scope.$on("fileSelected", function (event, args) {
        $scope.$apply(function () {            
            vm.files.push(args.file);
        });
    });
    vm.isEmptyMarket = false 
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                vm.model_data = {};
                angular.copy(empty_data, vm.model_data);
                vm.service.apiCall("get_sku_data/", "GET", {data_id: aData.DT_RowAttr["data-id"]}).then(function(data) {

                 if (data.message) {
                  data = data.data;
                  vm.update=true;
                  vm.model_data.sku_data = data.sku_data;
                  vm.model_data.market_data = data.market_data;
                  vm.model_data.zones = data.zones;
                  vm.model_data.groups = data.groups;
                  vm.model_data.sizes_list =  data.sizes_list;
                  vm.model_data.combo_data = data.combo_data;
                  var index = vm.model_data.zones.indexOf(vm.model_data.sku_data.zone);
                  vm.model_data.sku_data.zone = vm.model_data.zones[index];
                  
                  for (var j=0; j<vm.model_data.market_data.length; j++) {
                    var index = vm.model_data.market_list.indexOf(vm.model_data.market_data[j].market_sku_type);
                    vm.model_data.market_data[j].market_sku_type = vm.model_data.market_list[index];
                    vm.model_data.market_data[j]['disable'] = true;
                  };

                  var group_index = vm.model_data.groups.indexOf(vm.model_data.sku_data.sku_group);
                  vm.model_data.sku_data.sku_group = vm.model_data.groups[group_index];

                  index = vm.sku_types.indexOf(vm.model_data.sku_data.sku_type);
                  vm.model_data.sku_data.sku_type = vm.sku_types[index];
 
                  vm.model_data.sku_data.status = vm.status_data[vm.model_data.sku_data.status];
                  vm.model_data.sku_data.qc_check = vm.qc_data[vm.model_data.sku_data.qc_check];
 
                  vm.isEmptyMarket = (data.market_data.length > 0) ? false : true;
                  vm.combo = (vm.model_data.combo_data.length > 0) ? true: false;
                  vm.model_data.sku_data.image_url = vm.service.check_image_url(vm.model_data.sku_data.image_url);
                  vm.change_size_type(vm.model_data.sku_data.size_type);
                  $state.go('app.masters.SKUMaster.update');
                 }
                });
                vm.title ="Update SKU";
            });
        });
        return nRow;
    }

    vm.close = function() {

      angular.copy(empty_data, vm.model_data);
      $state.go('app.masters.SKUMaster');
    }

  //*****************
  vm.url = 'update_sku/';
  vm.market_send = {market_sku_type:[],marketplace_code:[],description:[],market_id:[]}
  vm.update_sku = update_sku;
  function update_sku() {

    var data = {
             "image": vm.files
           }
    var elem = angular.element($('form'));
    elem = elem[0];
    elem = $(elem).serializeArray();
    for (var i=0;i<elem.length;i++) {
      if(elem[i].name == "market_sku_type") {
        elem[i].value = vm.model_data.market_list[parseInt(elem[i].value)];
      } else if(elem[i].name == "status") {
        elem[i].value = vm.status_data[parseInt(elem[i].value)];
      } else if(elem[i].name == "qc_check") {
        elem[i].value = (elem[i].value == "?") ? "": vm.qc_data[parseInt(elem[i].value)];
      } else if(elem[i].name == "zone_id") {
        elem[i].value = (elem[i].value == "?") ? "": vm.model_data.zones[parseInt(elem[i].value)];
      } else if(elem[i].name == "sku_type") {
        elem[i].value = (elem[i].value == "?") ? "": vm.sku_types[parseInt(elem[i].value)];
      } else if(elem[i].name == "sku_group") {
        elem[i].value = (elem[i].value == "?") ? "": vm.model_data.groups[parseInt(elem[i].value)];
      }
    }

    var formData = new FormData()
    var files = $("#update_sku").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });

    $.each(elem, function(i, val) {
        formData.append(val.name, val.value);
    });

    $.ajax({url: Session.url+vm.url,
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              if(response.indexOf("Added") > -1 || response.indexOf("Updated") > -1) {
                vm.service.refresh(vm.dtInstance);
                vm.close();
              } else {
                vm.pop_msg(response); 
              }
            }});
  }

  vm.submit = function(data) {
    if ( data.$valid ){
      if ("Add SKU" == vm.title) {
        vm.url = "insert_sku/";
      } else {
        vm.url = "update_sku/";
      }
      vm.update_sku();
    }
  }

  vm.remove_market = function(index, id) {

        vm.model_data.market_data.splice(index,1);
        if (id) {
          vm.service.apiCall('delete_market_mapping/', "GET", {data_id: id}).then(function(data){
            console.log("success");
          })
        };
  }

  vm.add_market = function() {

    vm.model_data.market_data.push({description: "",market_id: "",market_sku_type: "",marketplace_code: "", disable: false});
    vm.isEmptyMarket = false;
  }

  vm.base = function() {

    vm.title = "Add SKU";
    vm.update = false;
    vm.combo = false;
    angular.copy(empty_data, vm.model_data);
  }
  vm.base();

  vm.add = function() {

    vm.base();
    vm.service.apiCall('get_zones_list/').then(function(data){
      if(data.message) {
        data = data.data;
        vm.model_data.zones = data.zones;
        vm.model_data.sku_data.zone = vm.model_data.zones[0];
        vm.model_data.groups = data.sku_groups;
        vm.model_data.sku_data.sku_group = '';
        vm.model_data.market_list = data.market_places;
        vm.model_data.sizes_list = data.sizes_list;
        vm.model_data.sku_data.sku_size = vm.model_data.sizes_list[0];
        vm.model_data.sku_data.size_type = "Default";
        vm.change_size_type();
      }
    });
    vm.model_data.sku_data.status = vm.status_data[1];
    vm.model_data.sku_data.qc_check = vm.qc_data[1];
    $state.go('app.masters.SKUMaster.update');
  }

  vm.pop_msg =  function(msg) {
    $(".insert-status > h4").text(msg);
    $timeout(function () {
      $(".insert-status > h4").text("");
    }, 3000);
  }

  vm.change_size_type = function(item) {

    if(!(item)) {
      item = "Default";
    }
    angular.forEach(vm.model_data.sizes_list, function(record) {

      if(item == record.size_name)  {
        vm.model_data.sizes = record.size_values;

        if(vm.model_data.sku_data.sku_size && (vm.model_data.sizes.indexOf(vm.model_data.sku_data.sku_size) != -1)) {
          console.log("it is there")
        } else {
          vm.model_data.sku_data.sku_size = vm.model_data.sizes[0];
        }
      }     
    })
  }

  vm.find_sizes = function(item) {

    if(item) {
      angular.forEach(vm.model_data.sizes_list, function(record) {

        if(record.size_values.indexOf(item) != -1) {
          vm.model_data.sizes = record.size_values;
        }
      })
    } else {
      angular.forEach(vm.model_data.sizes_list, function(record) {
        if(record.size_name == '') {
          record.size_values.push('');
          vm.model_data.sizes = record.size_values;
          vm.model_data.sku_data.sku_size = '';
        }
      })
    }
  }
}

app.directive('fileUpload', function () {
    return {
        scope: true,        //create a new scope
        link: function (scope, el, attrs) {
            el.bind('change', function (event) {
                var files = event.target.files;
                //iterate files since 'multiple' may be specified on the element
                for (var i = 0;i<files.length;i++) {
                    //emit event upward
                    scope.$emit("fileSelected", { file: files[i] });
                }                                       
            });
        }
    };
});
