'use strict';

var app = angular.module('urbanApp', ['datatables'])
app.controller('SKUMasterTable',['$scope', '$http', '$state', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', '$log', 'colFilters' , 'Service', '$rootScope', '$modal',ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, $log, colFilters, Service, $rootScope, $modal) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_profile = Session.user_profile;

    vm.filters = {'datatable': 'SKUMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':'', 'search6': '', 'search6': ''}
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
                        return '<img style="width: 35px;height: 40px;display: inline-block;margin-right: 10px;" src='+encodeURI(full.image_url)+'>'+'<p style=";display: inline-block;">'+ full['WMS SKU Code'] +'</p>';
                        }),
        DTColumnBuilder.newColumn('EAN Number').withTitle('EAN Number'),
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
    ];

    if(!vm.permissions.add_networkmaster && !vm.permissions.priceband_sync || Session.parent.userName == 'isprava_admin'){
      vm.dtColumns.push(DTColumnBuilder.newColumn('SKU Type').withTitle('SKU Type'))
    }
    vm.dtColumns.push(
      DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
        DTColumnBuilder.newColumn('SKU Class').withTitle('SKU Class'),
       )
    if(!vm.permissions.add_networkmaster && !vm.permissions.priceband_sync || Session.parent.userName == 'isprava_admin'){
      vm.dtColumns.push( DTColumnBuilder.newColumn('Color').withTitle('Color'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone'),)
    }
    vm.dtColumns.push(
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date'),
        DTColumnBuilder.newColumn('Updation Date').withTitle('Updation Date'),
        )
    if(!vm.permissions.add_networkmaster && !vm.permissions.priceband_sync || Session.parent.userName == 'isprava_admin'){
      vm.dtColumns.push(DTColumnBuilder.newColumn('Combo Flag').withTitle('Combo Flag'))
    }
    if(Session.parent.userName != 'isprava_admin'){
      if(vm.permissions.add_networkmaster || vm.permissions.priceband_sync){
          vm.dtColumns.push(DTColumnBuilder.newColumn('MRP').withTitle('MRP'),
           DTColumnBuilder.newColumn('HSN Code').withTitle('HSN Code'),
           DTColumnBuilder.newColumn('Tax Type').withTitle('Tax Type')
            )
        }}
    vm.dtColumns.push( DTColumnBuilder.newColumn('Status').withTitle('Status').renderWith(function(data, type, full, meta) {
                          return vm.service.status(data);
                        }).withOption('width', '80px'))

    var sku_attr_list = [];
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
                        sub_category: "",
                        primary_category: "",
                        threshold_quantity:"",
                        online_percentage:"",
                        status:0,
                        qc_check:1,
                        sku_brand: "",
                        sku_size: "",
                        style_name: "",
                        mix_sku: "",
                        ean_number: "",
                        load_unit_handle: "0",
                        hot_release: 0,
                        image_url:"images/wms/dflt.jpg",
                        measurement_type: "",
                        block_options: "No"
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
                      "market_list":["Flipkart","Snapdeal","Paytm","Amazon","Shopclues","HomeShop18","Jabong","Indiatimes","Myntra",
                                     "Voonik","Mr Voonik","Vilara", "Limeroad"],
                      "sizes_list":[],
                      sku_rel_imgs_show:[],
                      sku_files:[],
                    }
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.update_data = {};
    vm.zone_id = "red";
    vm.status_data = ['Inactive','Active'];
    vm.block_for_po_list = ['Yes', 'No'];
    vm.sku_types = ['', 'FG', 'RM'];
    vm.status = vm.status_data[0];
    vm.qc_data = ['Disable','Enable'];
    vm.qc = vm.qc_data[0];
    vm.block_options = vm.block_for_po_list[0];
    vm.market_list = [];
    vm.market;
    vm.market_data = [];
    vm.files = [];
    vm.mix_sku_list = {"No Mix": "no_mix", "Mix Within Group": "mix_group"};
    vm.sku_measurement_types = vm.service.units;
    if (Service.searched_wms_code != '') {
      vm.model_data.sku_data.sku_code = Service.searched_wms_code;
    };

    function readImage(input) {
      var deferred = $.Deferred();

      var files = input.file;
      if (files) {
          var fr= new FileReader();
          fr.onload = function(e) {
              deferred.resolve(e.target.result);
          };
          fr.readAsDataURL( files );
      } else {
          deferred.resolve(undefined);
      }

      return deferred.promise();
    }

    $scope.$on("fileSelected", function (event, args) {
      console.log(vm.model_data.sku_files);
      vm.model_data.sku_files.push(args.file);
      if (args.url.split(":")[1] == "sku_rel_imgs") {
        readImage(args).done(function(base64Data){
          $("#sku_files").val('');

          $scope.$apply(function () {
            vm.model_data.sku_rel_imgs_show.push(base64Data);
          });
        });
      } else {
        $scope.$apply(function () {
          vm.files.push(args.file);
        });
      }
    });

    vm.fileClose = function($index, sku_code, url){
      if (url != undefined) {
        vm.service.apiCall(url, "GET", {sku_code:sku_code, index: $index}).then(function(data) {
          if (data.message == 'Deleted Successfuly') {
            console.log('Success');
          }
        });
      } else {
        vm.model_data.sku_rel_imgs_show.splice($index,1);
        vm.model_data.sku_files.splice($index,1);
      }
    }

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
                  vm.model_data.serial_number = vm.permissions.use_imei;
                  vm.model_data.user_type = vm.permissions.user_type;
                  vm.model_data.sku_data = data.sku_data;
                  vm.model_data.market_data = data.market_data;
                  vm.model_data.zones = data.zones;
                  vm.model_data.groups = data.groups;
                  vm.model_data.sizes_list =  data.sizes_list;
                  vm.model_data.combo_data = data.combo_data;
                  vm.model_data.product_types = data.product_types;
                  vm.model_data.sub_categories = data.sub_categories;
                  var index = vm.model_data.zones.indexOf(vm.model_data.sku_data.zone);
                  vm.model_data.sku_data.zone = vm.model_data.zones[index];
                  vm.model_data.attributes = data.attributes;
                  vm.model_data.measurement_type = data.sku_data.measurement_type;
                  //vm.model_data.enable_serial_based = data.sku_data.enable_serial_based;
                  angular.forEach(vm.model_data.attributes, function(attr_dat){
                    if(data.sku_attributes[attr_dat.attribute_name])
                    {
                      attr_dat.attribute_value = data.sku_attributes[attr_dat.attribute_name];
                    }
                  });
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
                  if(vm.model_data.sku_data.ean_number == "0") {

                      vm.model_data.sku_data.ean_number = "";
                  }
                  if(vm.model_data.sku_data.enable_serial_based) {
                    vm.model_data.sku_data.enable_serial_based = true
                  } else {
                    vm.model_data.sku_data.enable_serial_based = false
                  }
                  $(".sales_return_reasons").importTags(vm.model_data.sales_return_reasons||'');
                  $state.go('app.masters.SKUMaster.update');
                 }
                });
                vm.title ="Update SKU";
            });
        });
        return nRow;
    }

    vm.addValidation = function(){

      $('.bootstrap-tagsinput').find('input').attr("autocomplete", "off");
    }

    vm.close = function() {
      angular.copy(empty_data, vm.model_data);
      vm.service.searched_wms_code = "";
      vm.service.searched_sup_code = '';
      if (vm.service.is_came_from_raise_po) {
        vm.service.searched_wms_code = vm.model_data.sku_data.sku_code;
        $state.go('app.inbound.RaisePo.PurchaseOrder');
      } else if (vm.service.is_came_from_create_order) {
        $state.go('app.outbound.CreateOrders');
      } else {
        $state.go('app.masters.SKUMaster');
      }
    }

    vm.b_close = vm.close;

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
    elem.push({name:'ean_numbers', value:$('.ean_numbers').val()});
    for (var i=0;i<elem.length;i++) {
      //if(elem[i].name == "market_sku_type") {
      //  elem[i].value = vm.model_data.market_list[parseInt(elem[i].value)];
      //} else
      if (vm.model_data.user_type != 'distributor' && vm.model_data.user_type != 'warehouse') {
        if(elem[i].name == "status") {
          elem[i].value = vm.status_data[parseInt(elem[i].value)];
        } else if(elem[i].name == "qc_check") {
          elem[i].value = (elem[i].value == "?") ? "": vm.qc_data[parseInt(elem[i].value)];
        } else if(elem[i].name == "sku_type") {
          elem[i].value = (elem[i].value == "?") ? "": vm.sku_types[parseInt(elem[i].value)];
        } else if(elem[i].name == "measurement_type") {
          elem[i].value = (elem[i].value.indexOf("? ") != -1) ? "": elem[i].value;
        }
      }
    }
    var formData = new FormData()
    var files = $("#update_sku").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });
    // SKU Related Files
    $.each(vm.model_data.sku_files, function(i, file) {
        formData.append('sku-related-files-' + i, file);
    });

    vm.related_files = $("#update_sku").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });

    $.each(elem, function(i, val) {
        formData.append(val.name, val.value);
    });

    $rootScope.process = true;
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
                if (vm.service.is_came_from_raise_po && response.indexOf("Added") > -1) {
                  vm.service.searched_wms_code = vm.model_data.sku_data.sku_code;
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.sku.wms_code = vm.model_data.sku_data.sku_code;
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.description = vm.model_data.sku_data.sku_desc;
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.sku.price = vm.model_data.sku_data.price;
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.supplier_code = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.order_quantity = 1
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.measurement_unit = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.mrp = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.price = vm.model_data.sku_data.price;
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.sgst_tax = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.cgst_tax = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.igst_tax = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.utgst_tax = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.cess_tax = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.remarks = ''
                  vm.service.raise_po_data.data[vm.service.sku_id_index].fields.dedicated_seller = ''
                  $state.go('app.inbound.RaisePo.PurchaseOrder');
                } else if (vm.service.is_came_from_create_order && response.indexOf("Added") > -1) {
                  vm.service.create_order_data.data[vm.service.sku_id_index].sku_id = vm.model_data.sku_data.sku_code;
                  vm.service.create_order_data.data[vm.service.sku_id_index].description = vm.model_data.sku_data.sku_desc;
                  vm.service.create_order_data.data[vm.service.sku_id_index].price = vm.model_data.sku_data.price;
                  vm.service.create_order_data.data[vm.service.sku_id_index].capacity = ''
                  vm.service.create_order_data.data[vm.service.sku_id_index].quantity = 1
                  vm.service.create_order_data.data[vm.service.sku_id_index].mrp = ''
                  vm.service.create_order_data.data[vm.service.sku_id_index].invoice_amount = ''
                  vm.service.create_order_data.data[vm.service.sku_id_index].discount = ''
                  vm.service.create_order_data.data[vm.service.sku_id_index].discount_percentage = ''
                  vm.service.create_order_data.data[vm.service.sku_id_index].total_amount = ''
                  vm.service.create_order_data.data[vm.service.sku_id_index].remarks = ''
                  vm.service.searched_wms_code = vm.model_data.sku_data.sku_code;
                  $state.go('app.outbound.CreateOrders');
                } else {
                  vm.service.refresh(vm.dtInstance);
                  vm.close();
                }
              } else {
                vm.pop_msg(response);
              }
              $rootScope.process = false;
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

  vm.add = function() {

    vm.base();
    vm.service.apiCall('get_zones_list/').then(function(data){
      if(data.message) {
        data = data.data;
        vm.model_data.serial_number = vm.permissions.use_imei;
        vm.model_data.zones = data.zones;
        vm.model_data.product_types = data.product_types;
        vm.model_data.sku_data.product_type = '';
        vm.model_data.sku_data.zone = vm.model_data.zones[0];
        vm.model_data.groups = data.sku_groups;
        vm.model_data.sku_data.sku_group = '';
        vm.model_data.market_list = data.market_places;
        vm.model_data.sizes_list = data.sizes_list;
        vm.model_data.sub_categories = data.sub_categories;
        vm.model_data.sku_data.sku_size = vm.model_data.sizes_list[0];
        vm.model_data.sku_data.size_type = "Default";
        vm.change_size_type();
        vm.model_data.attributes = data.attributes;
        angular.forEach(vm.model_data.attributes, function(record) {
          record.attribute_value = '';
        });
      }
    });
    vm.model_data.sku_data.status = vm.status_data[1];
    vm.model_data.sku_data.qc_check = vm.qc_data[0];
    $state.go('app.masters.SKUMaster.update');
  }

  vm.base();
  if (Service.searched_wms_code != '') {
    vm.add();
    vm.model_data.sku_data.sku_code = Service.searched_wms_code;
  };

  vm.barcode = function() {

      vm.barcode_title = 'Barcode Generation';
      vm.model_data['format_types'] = [];//['format1', 'format2', 'format3', 'Bulk Barcode'];
      var key_obj = {};//{'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'Bulk Barcode': 'Details'};
      vm.service.apiCall('get_format_types/').then(function(data){
        $.each(data['data']['data'], function(ke, val){
          vm.model_data['format_types'].push(ke);
          });
          key_obj = data['data']['data'];
      });


      vm.model_data['barcodes'] = [{'sku_code':'', 'quantity':''}];

      $state.go('app.masters.SKUMaster.barcode');
  }

  vm.pop_msg =  function(msg) {
    $(".insert-status > h4").text(msg);
    $timeout(function () {
      $(".insert-status > h4").text("");
    }, 3000);
  }

  vm.root_path = function(value){
    $rootScope.type = value
    $state.go('app.masters.ImageBulkUpload')
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
          //vm.model_data.sku_data.sku_size = vm.model_data.sizes[0];
          vm.model_data.sku_data.sku_size = '';
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

  vm.uploadFile = function (input) {
      if (input.files && input.files[0]) {
          var reader = new FileReader();
          reader.readAsDataURL(input.files[0]);
          reader.onload = function (e) {

              $('#photo-id').attr('src', e.target.result);
              var canvas = document.createElement("canvas");
              var imageElement = document.createElement("img");

              imageElement.setAttribute = $('<img>', { src: e.target.result });
              var context = canvas.getContext("2d");
              imageElement.setAttribute.load(function()
              {
                  // debugger;
                  canvas.width = this.width;
                  canvas.height = this.height;


                  context.drawImage(this, 0, 0);
                  var base64Image = canvas.toDataURL("image/png");

                  var data = base64Image.replace(/^data:image\/\w+;base64,/, "");

                  vm.model.Logo = data;
              });
          }
      }
  }

  vm.addAttributes = function() {
    var send_data = {}
    angular.copy(vm.attr_model_data, send_data);
    var modalInstance = $modal.open({
      templateUrl: 'views/masters/toggles/attributes.html',
      controller: 'AttributesPOP',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      //windowClass: 'full-modal',
      resolve: {
        items: function () {
          return send_data;
        }
      }
    });

    modalInstance.result.then(function (result_dat) {
      vm.model_data.attributes = result_dat;
    });
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
