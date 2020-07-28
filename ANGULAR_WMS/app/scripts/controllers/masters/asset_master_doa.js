'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('AssetMasterDOATable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.user_profile = Session.user_profile;
  vm.user_profile.warehouse_type = Session.user_profile.warehouse_type;
  vm.warehouse_level = Session.user_profile.warehouse_level;
  vm.model_data = {};
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
                        batch_based: 0,
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
                      "uom_type_list": ["Base", "Purchase", "Storage", "Consumption"],
                      sku_rel_imgs_show:[],
                      sku_files:[],
                    }
  vm.model_data = {};
  vm.dtInstance = {};
     $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

  angular.copy(empty_data, vm.model_data);

  vm.filters = {'datatable': 'AssetMasterDOA', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
     vm.dtInstance = {};
     $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });
     vm.dtColumns = [
      DTColumnBuilder.newColumn('requested_user').withTitle('Requested User'),
      DTColumnBuilder.newColumn('sku_desc').withTitle('Asset Description'),
      DTColumnBuilder.newColumn('asset_type').withTitle('Asset Type'),
      DTColumnBuilder.newColumn('sku_category').withTitle('Asset Category'),
      DTColumnBuilder.newColumn('sku_class').withTitle('Asset Class'),
      DTColumnBuilder.newColumn('doa_status').withTitle('Status'),
      DTColumnBuilder.newColumn('request_type').withTitle('Request Type'),
     ];
  if(vm.warehouse_level==0) {
      vm.dtColumns.push(DTColumnBuilder.newColumn('warehouse').withTitle('Warehouse'))
    }

  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    $('td', nRow).unbind('click');
    $('td', nRow).bind('click', function() {
      $scope.$apply(function() {
        vm.model_data = {};
        vm.suggest_id = aData.DT_RowAttr["data-id"]
        angular.copy(empty_data, vm.model_data);
        vm.highlight_data = {};
        vm.highlight_color = 'green';
        vm.service.apiCall("get_sku_master_doa_record/", "GET", {data_id: aData.DT_RowAttr["data-id"], is_asset:true}).then(function(data) {
         if (data.message) {
          vm.update=true;
          if (data.data.data.wms_code == ''){
          vm.model_data.sku_data = data.data.data;
          vm.sku_types = ['', 'FG', 'RM'];
          vm.files = [];
          vm.qc_data = ['Disable','Enable'];
          vm.status_data = ['Inactive','Active'];
          vm.block_for_po_list = ['Yes', 'No'];
          vm.qc = vm.qc_data[0];
          vm.status = vm.status_data[0];
          vm.block_options = vm.block_for_po_list[0];
          vm.model_data.uom_data = [];
          vm.mix_sku_list = {"No Mix": "no_mix", "Mix Within Group": "mix_group"};
          vm.sku_measurement_types = vm.service.units;
          vm.model_data.category_list = vm.model_data.sku_data.category_list;
          vm.model_data.class_list = vm.model_data.sku_data.class_list;
          $state.go('app.masters.AssetMaster.Mapping');
          vm.title = "Add Asset";
          } else if (data.data.data.sku_data.wms_code !='') {
            data = data.data.data;
          vm.update=true;
          vm.highlight_data = data.highlight_dict;
          vm.model_data.serial_number = vm.permissions.use_imei;
          vm.model_data.user_type = vm.permissions.user_type;
          vm.model_data.sku_data = data.sku_data;
          vm.model_data.market_data = data.market_data;
          vm.model_data.uom_data = data.uom_data;
          vm.model_data.zones = data.zones;
          vm.sku_types = ['', 'FG', 'RM'];
          vm.model_data.groups = data.groups;
          vm.model_data.sizes_list =  data.sizes_list;
          vm.model_data.category_list =  data.category_list;
          vm.model_data.class_list = data.class_list;
          vm.model_data.combo_data = data.combo_data;
          vm.qc_data = ['Disable','Enable'];
          vm.status_data = ['Inactive','Active'];
          vm.qc = vm.qc_data[0];
          vm.status = vm.status_data[0];
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

//          index = vm.sku_types.indexOf(vm.model_data.sku_data.sku_type);
//          vm.model_data.sku_data.sku_type = vm.sku_types[index];

          vm.model_data.sku_data.status = vm.status_data[vm.model_data.sku_data.status];
          vm.model_data.sku_data.qc_check = vm.qc_data[vm.model_data.sku_data.qc_check];

          vm.isEmptyMarket = (data.market_data.length > 0) ? false : true;
          vm.isEmptyUOM = (data.uom_data.length > 0) ? false : true;
          vm.combo = (vm.model_data.combo_data.length > 0) ? true: false;
          vm.model_data.sku_data.image_url = vm.service.check_image_url(vm.model_data.sku_data.image_url);
//          vm.change_size_type(vm.model_data.sku_data.size_type);
          if(vm.model_data.sku_data.ean_number == "0") {

              vm.model_data.sku_data.ean_number = "";
          }
          if(vm.model_data.sku_data.enable_serial_based) {
            vm.model_data.sku_data.enable_serial_based = true
          } else {
            vm.model_data.sku_data.enable_serial_based = false
          }
          $(".sales_return_reasons").importTags(vm.model_data.sales_return_reasons||'');
          $state.go('app.masters.AssetMaster.Mapping');
          vm.title = "Update Asset";
          }}});
      });
    });
   return nRow;
  }

  //close popup
  vm.close = function() {
    $state.go('app.masters.AssetMaster');
  }
  vm.change_status_data = function(){
    vm.service.apiCall('change_status_sku_doa/', "GET", {data_id: vm.suggest_id}).then(function(response){
      vm.service.refresh(vm.dtInstance);
      console.log("SUCCESS")
      vm.close();
    });
  }
  vm.delete_sku = function(data) {
    vm.service.apiCall('sku_rejected_sku_doa/', "GET", {data_id: vm.suggest_id}).then(function(response){
      vm.close();
      vm.service.refresh(vm.dtInstance);
      console.log("SUCCESS")
    });
  }
  vm.market_send = {market_sku_type:[],marketplace_code:[],description:[],market_id:[]}
  vm.update_sku = update_sku;
  function update_sku() {
    var data = {
             "image": vm.files
           }
    var elem = angular.element($('form'));
    elem = elem[1];
    elem = $(elem).serializeArray();
    elem.push({name:'ean_numbers', value:$('.ean_numbers').val()});
    // elem.push({name:'substitutes', value:$('.substitutes').val()});
    elem.push({name:'is_asset', value:true});
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

    vm.process = true;
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
                  if (response == "New WMS Code Added" || response == "Updated Successfully"){
                    vm.change_status_data();
                  }
                }
              } else {
                vm.pop_msg(response);
              }
              vm.process = false;
//              vm.close();
//              vm.dtInstance.reload();
            }});
  }

  vm.success = function(data) {
    if ( data.$valid ){
      if ("Add Asset" == vm.title) {
          vm.url = "insert_sku/";
      }else{
          vm.url = "update_sku/";
      }
      vm.update_sku();
    }
  }

  vm.root_path = function(value){
    $rootScope.type = value
    $state.go('app.masters.ImageBulkUpload')
  }
  vm.base = function() {

    vm.title = "Add SKU";
    vm.update = false;
    vm.combo = false;
    angular.copy(empty_data, vm.model_data);
  }

  vm.delete_sku = function(data) {
    vm.service.apiCall('sku_rejected_sku_doa/', "GET", {data_id: vm.suggest_id}).then(function(response){
      console.log("SUCCESS")
      vm.close();
    });
  }
  vm.reload = function() {
    vm.service.refresh(vm.dtInstance);
  }
  vm.add_uom = function() {

    vm.model_data.uom_data.push({uom_type: "",uom_name: "",conversion: "", uom_id: "", disable: false});
    vm.isEmptyUOM = false;
  }
  vm.remove_uom = function(index, id) {

        vm.model_data.uom_data.splice(index,1);
        if (id) {
          vm.service.apiCall('delete_uom_master/', "GET", {data_id: id}).then(function(response){
            console.log("success");
          })
        };
  }
  vm.pop_msg =  function(msg) {
    $(".insert-status > h4").text(msg);
    $timeout(function () {
      $(".insert-status > h4").text("");
    }, 3000);
  }
  vm.remove_market = function(index, id) {

        vm.model_data.market_data.splice(index,1);
        if (id) {
          vm.service.apiCall('delete_market_mapping/', "GET", {data_id: id}).then(function(data){
            console.log("success");
          })
        };
  }

  }
