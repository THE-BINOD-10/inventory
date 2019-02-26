FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('ReceivePOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.self_life_ratio = Number(vm.permissions.shelf_life_ratio) || 0;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;
    vm.parent_username = Session.parent.userName;
    vm.milkbasket_users = ['milkbasket', 'milkbasket_noida', 'milkbasket_test', 'milkbasket_bangalore'];
    vm.milkbasket_file_check = ['milkbasket'];
    vm.display_approval_button = false;
    vm.supplier_id = '';
    vm.order_id = 0;
    vm.invoice_readonly ='';
    vm.receive_po_mandatory_fields = {};
    if(vm.permissions.receive_po_mandatory_fields) {
      angular.forEach(vm.permissions.receive_po_mandatory_fields.split(','), function(field){
        console.log(field+'\n');
        if (!vm.receive_po_mandatory_fields[field]) {
          vm.receive_po_mandatory_fields[field] = field;
        }
      })
    }
    console.log(vm.receive_po_mandatory_fields);
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
    vm.filters = {'datatable': 'ReceivePO', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': '',
                  'search6': '', 'search7': '', 'search8': '', 'search9': '', 'search10': '', 'style_view': vm.g_data.style_view};
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

    var columns = ['PO No', 'PO Reference', 'Customer Name', 'Order Date', 'Expected Date', 'Total Qty', 'Receivable Qty', 'Received Qty',
                   'Remarks', 'Supplier ID/Name', 'Order Type', 'Receive Status'];
    vm.dtColumns = vm.service.build_colums(columns);

    var row_click_bind = 'td';
    if(vm.g_data.style_view) {
      var toggle = DTColumnBuilder.newColumn('PO No').withTitle(' ').notSortable()
                 .withOption('width', '25px').renderWith(function(data, type, full, meta) {
                   return "<i ng-click='showCase.addRowData($event, "+JSON.stringify(full)+")' class='fa fa-plus-square'></i>";
                 })
      row_click_bind = 'td:not(td:first)';
    } else {

      var toggle = DTColumnBuilder.newColumn('PO No').withTitle(' ').notSortable().notVisible();
    }
    vm.dtColumns.unshift(toggle);
    vm.dtInstance = {};
    vm.poDataNotFound = function() {
      $(elem).removeClass();
      $(elem).addClass('fa fa-plus-square');
      Service.showNoty('Something went wrong')
    }
    vm.addRowData = function(event, data) {
      console.log(data);
      var elem = event.target;
      if (!$(elem).hasClass('fa')) {
        return false;
      }
      var data_tr = angular.element(elem).parent().parent();
      if ($(elem).hasClass('fa-plus-square')) {
        $(elem).removeClass('fa-plus-square');
        $(elem).removeClass();
        $(elem).addClass('glyphicon glyphicon-refresh glyphicon-refresh-animate');
        vm.order_id = data['PO No'].split("_")[1];
        Service.apiCall('get_receive_po_style_view/?order_id='+vm.order_id).then(function(resp){
          if (resp.message){

            if(resp.data.status) {
              var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='13'><dt-po-data data='"+JSON.stringify(resp.data)+"' preview='showCase.preview'></dt-po-data></td></tr>")($scope);
              data_tr.after(html)
              data_tr.next().toggle(1000);
              $(elem).removeClass();
              $(elem).addClass('fa fa-minus-square');
            } else {
              vm.poDataNotFound();
            }
          } else {
            vm.poDataNotFound();
          }
        })
      } else {
        $(elem).removeClass('fa-minus-square');
        $(elem).addClass('fa-plus-square');
        data_tr.next().remove();
      }
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $(row_click_bind, nRow).unbind('click');
        $(row_click_bind, nRow).bind('click', function() {
            $scope.$apply(function() {
              // vm.supplier_id = aData['DT_RowId'];
              vm.round_off = false;
                vm.supplier_id = aData['Supplier ID/Name'].split('/')[0];
                vm.service.apiCall('get_supplier_data/', 'GET', {supplier_id: aData['DT_RowId']}).then(function(data){
                  if(data.message) {
                    vm.serial_numbers = [];
                    vm.skus_total_amount = 0;
                    angular.copy(data.data, vm.model_data);
                    vm.send_for_approval_check(event, vm.model_data);
                    vm.title = "Generate GRN";
                    if (vm.industry_type == 'FMCG') {
                      vm.extra_width = {
                        'width': '1400px'
                      };
                    } else {
                      vm.extra_width = {
                        'width': '900px'
                      };
                    }
                    vm.model_data.dc_level_grn = false;
                    if(vm.model_data.dc_grn == 'on') {
                      vm.model_data.dc_level_grn = true;
                    }
                    vm.shelf_life = vm.model_data.data[0][0].shelf_life;
                    for(var par_ind=0;par_ind < vm.model_data.data.length;par_ind++)
                    {
                      vm.calc_total_amt(event, vm.model_data, 0, par_ind);
                    }
                    if(vm.model_data.uploaded_file_dict && Object.keys(vm.model_data.uploaded_file_dict).length > 0) {
                      vm.model_data.uploaded_file_dict.file_url = vm.service.check_image_url(vm.model_data.uploaded_file_dict.file_url);
                    }

//                    angular.forEach(vm.model_data.data, function(row){
//                      angular.forEach(row, function(sku){
//                        sku['buy_price'] = sku.price;
//                        sku['discount_percentage'] = 0;
//                      });
//                    });

                    console.log('MRP is: '+vm.model_data.data[0][0].buy_price);
                    if(vm.permissions.use_imei) {
                      fb.push_po(vm.model_data);
                    }
                    if(aData['Order Type'] == "Vendor Receipt") {
                      $state.go('app.inbound.RevceivePo.Vendor');
                    } else {
                      $state.go('app.inbound.RevceivePo.GRN');
                    }
                  }
                });
            });
        });
        return nRow;
    }

    $(document).on('keydown', 'input.detectTab', function(e) {
      var keyCode = e.keyCode || e.which;

      var fields_count = 0;

      if (vm.permissions.pallet_switch || vm.industry_type=='FMCG') {
        fields_count = (this.closest('#tab_count').childElementCount-2);
      } else {
        fields_count = (this.closest('#tab_count').childElementCount-1);
      }

      var cur_td_index = (this.parentElement.nextElementSibling.cellIndex);

      if (this.closest('#tab_count').cells[0].children[1].tagName == 'UL') {

        var sku_index = (this.closest('#tab_count').cells[0].children[2].value);
      } else {

        var sku_index = (this.closest('#tab_count').cells[0].children[1].value);
      }


      if ((keyCode == 9) && (fields_count === cur_td_index)) {
        e.preventDefault();
        vm.add_wms_code(Number(sku_index), false);
      }
    });

    /*$(document).on('keydown', 'input.detectReceiveTab', function(e) {
      var keyCode = e.keyCode || e.which;

      if (keyCode == 9) {
        e.preventDefault();
        vm.add_wms_code(Number(this.parentNode.children[1].value), false);
      }
    });*/

    $scope.getExpiryDate = function(index, parent_index){
        var mfg_date = new Date(vm.model_data.data[parent_index][index].mfg_date);
        var shelf_life = vm.model_data.data[parent_index][index].shelf_life;
        if(!shelf_life || shelf_life=='') {
          shelf_life = 0;
        }
        var expiry = new Date(mfg_date.getFullYear(),mfg_date.getMonth(),mfg_date.getDate()+shelf_life);
        //vm.model_data.data[parent_index][index].exp_date = (expiry.getMonth() + 1) + "/" + expiry.getDate() + "/" + expiry.getFullYear();
        var row_data = vm.model_data.data[parent_index][index]
        if (!row_data.exp_date || row_data.exp_date == ''){
            row_data.exp_date = (expiry.getMonth() + 1) + "/" + expiry.getDate() + "/" + expiry.getFullYear();
        }
        //$('.mfgDate').each(function(){
            //if($(this).val() != ""){
                //var mfg_date = new Date($(this).val());
                //var expiry = new Date(mfg_date.getFullYear(),mfg_date.getMonth(),mfg_date.getDate()+vm.shelf_life);
                //var response = (expiry.getMonth() + 1) + "/" + expiry.getDate() + "/" + expiry.getFullYear() ;
                //vm.model_data.data[parent_index][index]['exp_date'] = response;
                //$(this).parent().next().find('.expiryDatePicker').datepicker("setDate", response);
            //}
        //});


    }

    vm.check_exp_date = function(sel_date, shelf_life_ratio, index, parent_index){
      var mfg_date = new Date(vm.model_data.data[parent_index][index].mfg_date);
      var exp_date = new Date(sel_date);

      if (exp_date < mfg_date && vm.model_data.data[parent_index][index].mfg_date) {
        Service.showNoty('Your selected date is less than manufacturer date.');
        vm.model_data.data[parent_index][index].exp_date = '';
      } else if(!vm.model_data.data[parent_index][index].mfg_date){

        Service.showNoty('Please choose manufacturer date first');
        vm.model_data.data[parent_index][index].exp_date = '';
      } else {
        var shelf_life = vm.model_data.data[parent_index][index].shelf_life;
        if(!shelf_life || shelf_life=='') {
          shelf_life = 0; 
        }
        if (shelf_life && shelf_life_ratio) {
          var res_days = (shelf_life * (shelf_life_ratio / 100));
          var cur_date = new Date();
          if(new Date(exp_date) > new Date()){

            var timeDiff = Math.abs(exp_date.getTime() - cur_date.getTime());
            var diffDays = Math.ceil(timeDiff / (1000 * 3600 * 24));

            // alert('Result days are: '+res_days+'\n Days left are: '+diffDays);
            if (diffDays < res_days) {
              Service.showNoty('Product has crossed acceptable shelf life ratio');
              //vm.model_data.data[0][0].exp_date = '';
            }

          } else {
            Service.showNoty('Please choose proper date');
            vm.model_data.data[parent_index][index].exp_date = '';
          }
        }
      }
    }

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.model_data = {};
    vm.dis = true;

    vm.close = close;
    function close() {

      vm.model_data = {};
      vm.html = "";
      vm.scanned_wms =[]
      vm.invoice_readonly_option = false
      vm.print_enable = false;
      if(vm.permissions.use_imei) {
        fb.stop_fb();
        vm.imei_list = [];
      }
      vm.sort_items = [];
      vm.sort_flag = false;
      vm.display_approval_button = false;
      $state.go('app.inbound.RevceivePo');
    }

    vm.update_data = update_data;
    function update_data(index, data) {
      if (Session.roles.permissions['pallet_switch'] || vm.industry_type == 'FMCG') {
        if (index == data.length-1) {
          var new_dic = {};
          angular.copy(data[0], new_dic);
          new_dic.receive_quantity = 0;
          new_dic.value = "";
          new_dic.pallet_number = "";
          new_dic.batch_no = "";
          new_dic.manf_date = "";
          new_dic.exp_date = "";
          new_dic.total_amt = "";
          new_dic.temp_json_id = "";
          data.push(new_dic);
        } else {
          if(data[index]['temp_json_id']) {
            var json_delete_data = {'model_name': 'PO', 'json_id': data[index]['temp_json_id']}
            vm.service.apiCall('delete_temp_json/', 'POST', json_delete_data, true).then(function(data){
              if(data.message) {
                console.log("Temp Json deleted");
              }
            });
          }
          data.splice(index,1);
        }

      }
    }

    vm.new_sku = false
    vm.add_wms_code = add_wms_code;
    function add_wms_code(index=0, flag=true) {
      if (index==vm.model_data.data.length-1 && !flag || !index && flag) {
        if (flag) {

          vm.model_data.data.push([{"wms_code":"", "po_quantity":0, "receive_quantity":"", "price":"", "dis": false,
                                  "order_id": '', "is_new": true, 'mrp': 0, "unit": "",
                                  "buy_price": "", "cess_percent": "", "tax_percent": "", "apmc_percent": "",
                                  "total_amt": "", "discount_percentage": 0,
                                  "sku_details": [{"fields": {"load_unit_handle": ""}}]}]);
        } else {

          $scope.$apply(function() {
            vm.model_data.data.push([{"wms_code":"", "po_quantity":0, "receive_quantity":"", "price":"", "dis": false,
                                    "order_id": '', "is_new": true, 'mrp': 0, "unit": "",
                                    "buy_price": "", "cess_percent": "", "tax_percent": "", "apmc_tax": "",
                                    "total_amt": "", "discount_percentage": 0,
                                    "sku_details": [{"fields": {"load_unit_handle": ""}}]}]);
          });
        }
      }
    }
    vm.get_sku_details = function(data, selected) {

      data.wms_code = selected.wms_code;
      data.measurement_unit = selected.measurement_unit;
      data.sku_desc = selected.sku_desc;
      data.po_quantity = 0;
      data.price = 0;
      if (Number(selected.mrp)) {
        data.mrp = selected.mrp;
      } else {
        data.mrp = 0;
      }
      data.description = selected.sku_desc;
      data.tax_percent = 0;
      data.cess_percent = 0;
      data.apmc_percent = 0;
      data.discount_percentage = 0;

      data.sku_details[0].fields.load_unit_handle = selected.load_unit_handle;
      $timeout(function() {$scope.$apply();}, 1000);

      if (!vm.supplier_id){
        return false;
      } else {
        var supplier = vm.supplier_id;
        vm.service.apiCall('get_mapping_values/', 'GET', {'wms_code':data.wms_code, 'supplier_id': supplier}).then(function(resp){
          if(Object.values(resp).length) {
            data.price = resp.data.price;
            data.supplier_code = resp.data.supplier_code;
            data.ean_number = resp.data.ean_number;
            data.buy_price = resp.data.price;

            data.row_price = (Number(data.value) * Number(data.price));
            vm.getTotals();
          }
        });
        vm.get_supplier_sku_prices(data.wms_code).then(function(sku_data){
            sku_data = sku_data[0];
            data.tax_type = sku_data.tax_type.replace(" ","_").toLowerCase();
            // data.tax_type = 'intra_state';

            // data["taxes"] = [];
            // data.taxes.push({'cgst_tax':0.25, 'sgst_tax':0.25, 'cess_tax': 5});
            data["taxes"] = sku_data.taxes;
            vm.get_tax_value(data);
        })
      }
    }

    vm.get_supplier_sku_prices = function(sku) {

       var d = $q.defer();
       var data = {sku_codes: sku, suppli_id: vm.supplier_id}
       // var data = {sku_codes: sku, suppli_id: 825}
       vm.service.apiCall("get_supplier_sku_prices/", "POST", data).then(function(data) {

         if(data.message) {
           d.resolve(data.data);
         }
       });
       return d.promise;
    }

    vm.get_tax_value = function(sku_data) {

     var tax = 0;
     for(var i = 0; i < sku_data.taxes.length; i++) {

       // if(sku_data.fields.price <= sku_data.taxes[i].max_amt && sku_data.fields.price >= sku_data.taxes[i].min_amt) {

         sku_data.cess_percent = sku_data.taxes[i].cess_tax;
         sku_data.apmc_percent = sku_data.taxes[i].apmc_tax;
         if(sku_data.tax_type == "intra_state") {

           tax = sku_data.taxes[i].sgst_tax + sku_data.taxes[i].cgst_tax;
         } else if (sku_data.tax_type == "inter_state") {
           tax = sku_data.taxes[i].igst_tax;
         }
         break;
       // }
     }

     sku_data.tax_percent = tax;
     return tax;
   }

    vm.submit = submit;
    function submit(form) {
      if (form.$valid) {

        var abs_inv_value = vm.absOfInvValueTotal(vm.model_data.invoice_value, vm.skus_total_amount);

        if (vm.permissions.receive_po_invoice_check && abs_inv_value <= 3){

          vm.save_sku();
        } else if (vm.permissions.receive_po_invoice_check && abs_inv_value >= 3) {

          colFilters.showNoty("Your entered invoice value and total value does not match");
        } else {

          vm.save_sku();
        }
      } else {
        colFilters.showNoty("Fill Required Fields");
      }
    }

    vm.save_sku = function(){
      var that = vm;
      if(vm.milkbasket_file_check.indexOf(vm.parent_username) >= 0 && !vm.model_data.dc_level_grn &&
          vm.display_approval_button && Object.keys(vm.model_data.uploaded_file_dict).length == 0) {
        if($(".grn-form").find('[name="files"]')[0].files.length < 1) {
          colFilters.showNoty("Uploading file is mandatory");
          return
        }
      }
      if($(".grn-form").find('[name="files"]')[0].files.length > 0){
        var size_check_status = vm.file_size_check($(".grn-form").find('[name="files"]')[0].files[0]);
        if(size_check_status){
          colFilters.showNoty("File Size should be less than 10 MB");
          return
        }
      }
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem.push({'name': 'display_approval_button', value: vm.display_approval_button})
      var form_data = new FormData();
      console.log(form_data);
      var files = $(".grn-form").find('[name="files"]')[0].files;
      $.each(files, function(i, file) {
        form_data.append('files-' + i, file);
      });
      $.each(elem, function(i, val) {
        form_data.append(val.name, val.value);
      });
      vm.service.apiCall('update_putaway/', 'POST', form_data, true, true).then(function(data){
        if(data.message) {
          if(data.data == 'Updated Successfully') {
            vm.close();
            vm.service.refresh(vm.dtInstance);
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

    vm.absOfInvValueTotal = function(inv_value, total_value){

      return Math.abs(inv_value - total_value);
    }
  vm.scanned_wms =[]
    vm.check_sku_pack = function(event,pack_id)
    {
        event.stopPropagation();
        if (event.keyCode == 13 )
        {
           vm.service.apiCall('check_sku_pack_scan/', 'GET', {'pack_id':pack_id}).then(function(data){
             if (data.data.flag)
               {
                 for(var i=0; i<vm.model_data.data.length; i++)
                 {
                   if (vm.model_data.data[i][0].wms_code.indexOf(vm.scanned_wms) == -1 || vm.scanned_wms.length == 0)
                   {
                     if(vm.model_data.data[i][0].po_quantity > vm.model_data.data[i][0].value && vm.model_data.data[i][0].po_quantity >= (vm.model_data.data[i][0].value+data.data.quantity))
                      {
                       if(vm.model_data.data[i][0].wms_code == data.data.sku_code)
                        {
                          vm.model_data.data[i][0].pack_id = pack_id
                          if(!vm.model_data.data[i][0].num_packs)
                          {
                            vm.model_data.data[i][0].num_packs =0
                          }
                          vm.model_data.data[i][0].num_packs +=1;
                          vm.model_data.data[i][0].value += data.data.quantity
                          if (vm.model_data.data[i][0].price)
                          {
                            vm.model_data.data[i][0].total_amt =  vm.model_data.data[i][0].price * vm.model_data.data[i][0].value
                           }
                           break;
                         }
                       else
                        {
                          if(!vm.model_data.data[i][0].value)
                           {
                             Service.showNoty('Pack Id is not matched to SKU', 'error', 'topRight')
                           }
                        }
                      }
                  else if(vm.model_data.data[i][0].po_quantity == vm.model_data.data[i][0].value)
                      {
                           vm.scanned_wms.push(vm.model_data.data[i][0].wms_code)
                      }
                  else
                    {
                    Service.showNoty('Recived quantity is greater than PO quantity', 'error', 'topRight')
                    }
                   }
                 }

               }
            else{
                Service.showNoty(data.data.status, 'error', 'topRight')
                }
            });
        }
    }


    vm.absOfQtyTolerence = function(inv_value, total_value){
      return Math.abs(1.1*inv_value);
    }

    // vm.skus_total_amount

    vm.html = "";
    vm.confirm_grn = function(form) {
      // var data = [];
      // data.push({name: 'batch_no', value: form.batch_no.$viewValue});
      // data.push({name: 'mrp', value: form.mrp.$viewValue});
      // data.push({name: 'manf_date', value: form.manf_date.$viewValue});
      // data.push({name: 'exp_date', value: form.exp_date.$viewValue});
      // data.push({name: 'po_unit', value: form.po_unit.$viewValue});
      // data.push({name: 'tax_per', value: form.tax_per.$viewValue});
      if (form.$valid) {
        if(vm.milkbasket_file_check.indexOf(vm.parent_username) >= 0 && !vm.model_data.dc_level_grn &&
            Object.keys(vm.model_data.uploaded_file_dict).length == 0){
          if($(".grn-form").find('[name="files"]')[0].files.length < 1) {
            colFilters.showNoty("Uploading file is mandatory");
            return
          }
        }
        if($(".grn-form").find('[name="files"]')[0].files.length > 0){
          var size_check_status = vm.file_size_check($(".grn-form").find('[name="files"]')[0].files[0]);
          if(size_check_status){
            colFilters.showNoty("File Size should be less than 10 MB");
            return
          }
        }
        if (vm.permissions.receive_po_invoice_check && vm.model_data.invoice_value){

          var abs_inv_value = vm.absOfInvValueTotal(vm.model_data.invoice_value, vm.model_data.round_off_total);

          if (vm.permissions.receive_po_invoice_check && abs_inv_value <= 3){

            vm.confirm_grn_api();
          } else if (vm.permissions.receive_po_invoice_check && abs_inv_value >= 3) {

            colFilters.showNoty("Your entered invoice value and total value does not match");
          }
        } else if (vm.permissions.receive_po_invoice_check && !(vm.model_data.invoice_value)){

          colFilters.showNoty("Please Fill The Invoice Value Field");
        } else {

          vm.confirm_grn_api();
        }
      } else {
        colFilters.showNoty("Fill Required Fields");
      }
    }

    vm.confirm_grn_api = function(){

      if(check_receive()){
        var that = vm;
        var elem = angular.element($('form'));
        elem = elem[0];

        var buy_price = parseInt($(elem).find('input[name="buy_price"]').val());
        var mrp = parseInt($(elem).find('input[name="mrp"]').val());

        if(buy_price > mrp) {
          pop_msg("Buy Price should be less than or equal to MRP");
          return false;
        }
        elem = $(elem).serializeArray();
        var form_data = new FormData();
        console.log(form_data);
        var files = $(".grn-form").find('[name="files"]')[0].files;
        $.each(files, function(i, file) {
          form_data.append('files-' + i, file);
        });
        $.each(elem, function(i, val) {
          form_data.append(val.name, val.value);
        });
        var url = "confirm_grn/"
        if(vm.po_qc) {
          url = "confirm_receive_qc/"
        }
        vm.service.apiCall(url, 'POST', form_data, true, true).then(function(data){
          if(data.message) {
            if(data.data.search("<div") != -1) {
              vm.extra_width = {}
              vm.html = $(data.data);
              vm.extra_width = {}
              //var html = $(vm.html).closest("form").clone();
              //angular.element(".modal-body").html($(html).find(".modal-body"));
              angular.element(".modal-body").html($(data.data));
              vm.print_enable = true;
              vm.service.refresh(vm.dtInstance);
              if(vm.permissions.use_imei) {
                fb.generate = true;
                fb.remove_po(fb.poData["id"]);
              }
            } else {
              pop_msg(data.data)
            }
          }
        });
      }
    }

    function check_receive() {
      var status = false;
      for(var i=0; i<vm.model_data.data.length; i++)  {
        angular.forEach(vm.model_data.data[i], function(sku){
          if(sku.value > 0) {
            status = true;
          }
        });
      }

      if(status){
        return true;
      } else {
        pop_msg("Please Update the received quantity");
        return false;
      }
    }

    vm.close_po = close_po;
    vm.closed_po = {};
    function close_po(data) {
        var elem = angular.element($('form'));
        vm.closed_po['elem'] = $(elem[0]).serializeArray();
        swal2({
          title: 'Do you want to close the PO',
          text: '',
          input: 'text',
          confirmButtonColor: '#d33',
          // cancelButtonColor: '#d33',
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          showLoaderOnConfirm: true,
          inputOptions: 'Testing',
          inputPlaceholder: 'Type Reason',
          confirmButtonClass: 'btn btn-danger',
          cancelButtonClass: 'btn btn-default',
          showCancelButton: true,
          preConfirm: function (text) {
            return new Promise(function (resolve, reject) {
              vm.closed_po.elem.push({name: 'remarks', value: text});
              vm.service.apiCall('close_po/', 'POST', vm.closed_po.elem, true).then(function(data){
                if(data.message) {
                  if(data.data == 'Updated Successfully') {
                    vm.close();
                    vm.service.refresh(vm.dtInstance);
                    resolve();
                  } else {
                    Service.showNoty(data.data)
                  }
                }
              });
            })
          },
          allowOutsideClick: false,
          // buttonsStyling: false
        }).then(function (text) {
            swal2({
              type: 'success',
              title: 'Received PO is Deleted!',
              // html: 'Submitted text is: ' + text
            })
        });

    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
        vm.message = "";
      }, 2000);
      vm.service.refresh(vm.dtInstance);
    }

    vm.receive_quantity_change = function(data) {

      if(Session.user_profile.user_type == "marketplace_user") {
        if(Number(data.po_quantity) < Number(data.value)) {
          data.value = data.po_quantity;
        }
      }
    }

    vm.sort_items = [];
    vm.sort_flag = false;
    vm.scan_sku = function(event, field) {
      if (event.keyCode == 13 && field.length > 0) {
        console.log(field);
        vm.model_data.scan_sku = "";
        vm.scan_sku_disable = true;
        if(vm.permissions.barcode_generate_opt == "sku_serial" && vm.permissions.use_imei) {
          vm.service.apiCall('check_generated_label/', 'GET',{'label': field, 'order_id': vm.model_data.po_id}).then(function(data){
            if(data.message) {
              if(data.data.message == 'Success') {
                field = data.data.data.label;
                var sku_code = data.data.data.sku_code;
                if ((vm.fb.poData.serials.indexOf(field) != -1) || (vm.imei_list.indexOf(field) != -1)){

                  Service.showNoty("Serial Number already Exist");
                  $('textarea[name="scan_sku"]').trigger('focus').val('');
                } else {

                  for(var i=0; i<vm.model_data.data.length; i++) {
                    var temp = vm.model_data.data[i][0];
                    if(temp.wms_code == sku_code) {
                      if(vm.po_qc) {
                        vm.current_index = i;
                        //vm.model_data0["sku_data"] = data1.sku_details[0].fields;
                        vm.imei_list.push(field);
                        vm.accept_qc(vm.model_data.data[i], field);
                        qc_details();
                      } else {
                        vm.po_imei_scan(vm.model_data.data[i][0], field)
                      }
                      vm.current_sku = "";
                      break;
                    }
                  }
                }
              } else {
                Service.showNoty(data.data.message);
              }
            } else {
              Service.showNoty("Something went wrong");
            }
            vm.scan_sku_disable = false;
          })
        } else {
          vm.service.apiCall('check_sku/', 'GET',{'sku_code': field}).then(function(data){
            if(data.message) {
              vm.field = data.data.sku_code;
              vm.sort_flag = false;
              for(var i=0; i<vm.model_data.data.length; i++) {

                angular.forEach(vm.model_data.data[i], function(sku){

                  // vm.sku_list_1.push(sku.wms_code);
                  if(vm.field == sku.wms_code){
                    // $timeout(function() {
                      //vm.sort_items = [];
                      //vm.sort_items.push(vm.model_data.data[i]);
                      if(i != 0) {
                        var temp_dict = [];
                        angular.copy(vm.model_data.data[0], temp_dict);
                        angular.copy(vm.model_data.data[i], vm.model_data.data[0]);
                        angular.copy(temp_dict, vm.model_data.data[i]);
                      }
                      //vm.show_sel_item_top(vm.model_data.data[i]);
                    // }, 500);
                      $("input[attr-name='imei_"+vm.field+"']").trigger('focus');
                    //vm.sort_flag = true;
                  }
                });
              }
              if (vm.permissions.use_imei) {
                vm.sku_list_1 = [];
                for(var i=0; i<vm.model_data.data.length; i++) {

                  angular.forEach(vm.model_data.data[i], function(sku){

                    vm.sku_list_1.push(sku.wms_code);
                  });
                }

                if (vm.sku_list_1.indexOf(vm.field) == -1){

                  if (data.data.sku_code && data.data.sku_code == vm.field) {

                    Service.showNoty(vm.field+' Does Not Exist');
                  } else {

                    vm.addNewScannedSku(event, field);
                  }
                }
              } else {
                vm.sku_list_1 = [];
                for(var i=0; i<vm.model_data.data.length; i++) {

                  angular.forEach(vm.model_data.data[i], function(sku, temp_sku_ind){

                    vm.sku_list_1.push(sku.wms_code);
                    if(vm.field == sku.wms_code){
                      if(sku.value < sku.po_quantity) {
                        sku["value"] = Number(sku["value"]) + 1;
                        vm.calc_total_amt(event, vm.model_data, Number(i), temp_sku_ind);
                      } else {
                         Service.showNoty("Received Quantity Equal To PO Quantity");
                      }
                      $('textarea[name="scan_sku"]').trigger('focus').val('');
                    }
                  });
                }
                if (vm.sku_list_1.indexOf(vm.field) == -1){

                  if (data.data.sku_code && data.data.sku_code == vm.field) {

                    Service.showNoty(vm.field+' Does Not Exist');
                  } else {

                    vm.addNewScannedSku(event, field);
                  }
                }
              }
            } else {
              Service.showNoty("Something went wrong");
            }
            vm.scan_sku_disable = false;
          });
        }
      }
    }

    vm.show_sel_item_top = function(record){
      for(var i=0; i<vm.model_data.data.length; i++) {
        angular.forEach(vm.model_data.data[i], function(sku){
          if (record[0].wms_code != sku.wms_code) {
            vm.sort_items.push(vm.model_data.data[i]);
          } else {
            $("input[attr-name='imei_"+record[0].wms_code+"']").trigger('focus');
          }
        })
      }
    }
    vm.change_overall_discount =function(){
      var discount = 0;
      var total = 0;
      if(vm.model_data.overall_discount) {
        discount = vm.model_data.overall_discount;
      }
      if(vm.model_data.round_off_total) {
        total = vm.model_data.round_off_total;
      }
      if(total>discount)
      {
        vm.calc_total_amt(event, vm.model_data, 0, 0);
      }
      else{
        vm.model_data.overall_discount = 0;
      }
    }

    vm.addNewScannedSku = function(event, field){

      vm.marginData = {scanned_val: field, map_sku_code: ''};
      var mod_data = vm.marginData;
      var modalInstance = $modal.open({
        templateUrl: 'views/inbound/toggle/add_new_sku.html',
        controller: 'addNewSkuCtrl',
        controllerAs: '$ctrl',
        size: 'md',
        backdrop: 'static',
        keyboard: false,
        resolve: {
          items: function () {
            return mod_data;
          }
        }
      });

      modalInstance.result.then(function (selectedItem) {

        vm.scan_sku(event, field);
      })
    }

    FUN.scan_sku = vm.scan_sku;

    vm.po_imei_scan = function(data1, field) {
      field = field.toUpperCase();
      if(data1["imei_list"].indexOf(field) != -1) {

        Service.showNoty("IMEI Already Scanned");
        return false;
      }
      data1.value = parseInt(data1.value)+1;
      vm.serial_numbers.push(field);
      data1["imei_list"].push(field);
      fb.change_serial(data1, field);
      vm.current_sku = "";
      data1.imei_number = "";
      if(vm.permissions.grn_scan_option == "sku_serial_scan") {
        $('textarea[name="scan_sku"]').trigger('focus').val('');
      }
    }

    vm.qc_details = qc_details;
    function qc_details() {

      $state.go('app.inbound.RevceivePo.qc_detail');
      $timeout(function() {
        if(vm.permissions.grn_scan_option == "serial_scan") {
          focus('focusIMEI');
        }
      }, 2000);
    }

    vm.showOldQty = false;
    vm.goBack = function() {
      vm.showOldQty = true;
      $state.go('app.inbound.RevceivePo.GRN');
    }

    vm.imei_list = [];
    vm.model_data1 = {};
    vm.po_qc_imei_scan = function(data1, index) {

      //vm.service.apiCall('check_imei_exists/', 'GET',{imei: data1.imei_number}).then(function(data){
      //  if(data.message) {
      //    if (data.data == "") {
            data1.sku_details[0].fields = data1.sku_details[0].fields.toUpperCase();
            vm.current_index = index;
            vm.model_data1["sku_data"] = data1.sku_details[0].fields;
            vm.imei_list.push(data1.imei_number);
            vm.accept_qc(data1, data1.imei_number);
            qc_details();
            data1.imei_number = "";
            vm.current_sku = "";
      //    } else {
      //      Service.showNoty(data.data);
      //    }
      //    data1.imei_number = "";
      //  }
      //})
    }

    vm.from_qc_scan = function(event, field) {
      event.stopPropagation();
      if (event.keyCode == 13 && field.length > 0) {
        field = field.toUpperCase();
        if (!vm.current_sku && (vm.permissions.grn_scan_option == "sku_serial_scan")) {

          focus('focusSKU');
          Service.showNoty("Scan SKU first before scaning IMEI");
        } else if (vm.imei_list.indexOf(field) > -1) {

          Service.showNoty("IMEI Already Scanned");
        } else if(vm.model_data.data[vm.current_index][0].po_quantity == vm.model_data.data[vm.current_index][0].value && (vm.permissions.barcode_generate_opt != 'sku_serial')) {

          Service.showNoty("PO quanity already equal to Receive Quantity for with SKU Code");
        } else {

          fb.check_imei(field).then(function(resp) {
            if (resp.status) {
              Service.showNoty("Serial Number already Exist in other PO: "+resp.data.po);
              vm.current_sku = "";
              if(vm.permissions.grn_scan_option == "sku_serial_scan") {
                focus('focusSKU');
              }
            } else {
              if(vm.permissions.barcode_generate_opt == 'sku_serial' || vm.permissions.barcode_generate_opt == 'sku_code') {
                vm.service.apiCall('check_imei_exists/', 'GET',{imei: field, sku_code: vm.model_data.data[vm.current_index][0].wms_code}).then(function(data){
                  if(data.message) {
                    if (data.data == "") {
                      vm.imei_list.push(field);
                      vm.accept_qc(vm.model_data.data[vm.current_index], field);
                      if(vm.permissions.grn_scan_option == "sku_serial_scan") {
                        focus('focusSKU');
                        vm.current_sku = "";
                      }
                    } else {
                      Service.showNoty(data.data);
                    }
                  }
                })
              } else {
                vm.service.apiCall('check_generated_label/', 'GET',{'label': field, 'order_id': vm.model_data.po_id}).then(function(data){
                  if(data.message) {
                    if(data.data.message == 'Success') {
                      var sku_code = data.data.data.sku_code;
                      for(var i = 0; i < vm.model_data.data.length; i++) {

                        var temp = vm.model_data.data[i][0];
                        if(temp.wms_code == sku_code) {

                          vm.current_sku = sku_code;
                          vm.enable_button = true;
                          vm.reason_show = false;
                          vm.current_index = i;
                          break;
                        }
                      }
                      if(status) {
                        Service.showNoty("SKU Not Found");
                        return false;
                      }
                      vm.imei_list.push(field);
                      vm.accept_qc(vm.model_data.data[vm.current_index], field);
                      vm.current_sku = "";
                    } else {
                      Service.showNoty(data.data.message);
                    }
                  }
                })
              }
            }
          })
          console.log(vm.current_index);
        }
        vm.serial_scan = "";
      }
    }

    vm.serial_numbers = [];
    vm.check_imei_exists = function(event, data1, index) {
      event.stopPropagation();
      if (event.keyCode == 13 && data1.imei_number.length > 0 && data1["disable"] != true) {
        data1.imei_number = data1.imei_number.toUpperCase();
        //if(vm.imei_list.indexOf(data1.imei_number) > -1) {

        //  Service.showNoty("IMEI Already Scanned");

        if (vm.fb.poData.serials.indexOf(data1.imei_number) != -1){

          Service.showNoty("Serial Number already Exist");
          data1.imei_number = "";
          //if(vm.permissions.barcode_generate_opt != "sku_serial") {
          //  $('textarea[name="scan_sku"]').trigger('focus').val('');
          //}
          if(vm.permissions.grn_scan_option == "sku_serial_scan") {
            $('textarea[name="scan_sku"]').trigger('focus').val('');
          }
        } else {

          data1["disable"] = true;
          fb.check_imei(data1.imei_number).then(function(resp) {
            if (resp.status) {
              Service.showNoty("Serial Number already Exist in other PO: "+resp.data.po);
              data1.imei_number = "";
              //if(vm.permissions.barcode_generate_opt != "sku_serial") {
              //  $('textarea[name="scan_sku"]').trigger('focus').val('');
              //}
              if(vm.permissions.grn_scan_option == "sku_serial_scan") {
                $('textarea[name="scan_sku"]').trigger('focus').val('');
              }
              data1["disable"] = false;
            } else {
              if(vm.permissions.barcode_generate_opt != "sku_serial") {
                vm.service.apiCall('check_imei_exists/', 'GET',{imei: data1.imei_number, sku_code: data1.wms_code}).then(function(data){
                  if(data.message) {
                    if (data.data == "") {
                      if(vm.po_qc) {
                        vm.po_qc_imei_scan(data1, index)
                      } else {
                        vm.po_imei_scan(data1, data1.imei_number)
                      }
                    } else {
                      Service.showNoty(data.data);
                      data1.imei_number = "";
                    }
                  }
                  data1["disable"] = false;
                })
              } else {
                vm.service.apiCall('check_generated_label/', 'GET',{'label': data1.imei_number, 'order_id': vm.model_data.po_id}).then(function(data){
                  if(data.message) {
                    if(data.data.message == 'Success') {
                      data1.imei_number = data.data.data.label;
                      var sku_code = data.data.data.sku_code;
                      if (data1.wms_code != sku_code) {
                        Service.showNoty("Scanned label belongs to "+sku_code);
                        data1.imei_number = "";
                        return false;
                      }
                      if(vm.po_qc) {
                        vm.po_qc_imei_scan(data1, index)
                      } else {
                        vm.po_imei_scan(data1, data1.imei_number)
                      }
                    } else {
                       Service.showNoty(data.data.message);
                       data1.imei_number = "";
                    }
                  }
                  data1["disable"] = false;
                })
              }
            }
          })
        }
      }
    }

    vm.current_sku = "";
    vm.change_sku_scan = function(event, sku) {

      if (event.keyCode == 13 && sku.length > 0) {
        event.stopPropagation();
        vm.service.apiCall('check_sku/', 'GET',{'sku_code': sku}).then(function(data){
          if(data.message) {
            sku = data.data.sku_code;
            var status = true;
            for(var i = 0; i < vm.model_data.data.length; i++) {

              var data = vm.model_data.data[i][0];
              if(data.wms_code == sku) {

                vm.current_sku = sku;
                vm.enable_button = true;
                vm.reason_show = false;
                vm.current_index = i;
                focus('focusIMEI');
                status = false;
                break;
              }
            }
            if(status) {

              Service.showNoty("SKU Not Found");
            }
            vm.change_sku = "";
          }
        })
      }
    }

    vm.print_grn = function() {
      vm.service.print_data(vm.html, "Generate GRN");
    }


    vm.barcode = function() {

      vm.barcode_title = 'Barcode Generation';

      vm.model_data['barcodes'] = [];

      angular.forEach(vm.model_data.data, function(barcode_data){

        var quant = barcode_data[0].value;

        var sku_det = barcode_data[0].wms_code;

        vm.model_data['barcodes'].push({'sku_code': sku_det, 'quantity': quant})

      })

      var modalInstance = $modal.open({
        templateUrl: 'views/outbound/toggle/barcodes.html',
        controller: 'Barcodes',
        controllerAs: 'pop',
        size: 'lg',
        backdrop: 'static',
        keyboard: false,
        resolve: {
          items: function () {
            console.log(model_data);
            return model_data;
          }
        }
      });

      modalInstance.result.then(function (selectedItem) {
      });
      //$state.go('app.inbound.RevceivePo.barcode');
    }

    vm.gen_barcode = function() {
      vm.barcode_title = 'Barcode Generation';
      vm.model_data['barcodes'] = [];

	  vm.model_data['format_types'] = [];
      var key_obj = {};//{'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'Bulk Barcode': 'Details'};
      vm.service.apiCall('get_format_types/').then(function(data){
        $.each(data['data']['data'], function(ke, val){
          vm.model_data['format_types'].push(ke);
          });
          key_obj = data['data']['data'];
      });
    Data.receive_jo_barcodes = false;
	  var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var list = [];
      var dict = {};
      $.each(elem, function(num, key){
      	if(!dict.hasOwnProperty(key['name'])){
        	dict[key['name']] = key['value'];
      	}else{
        	list.push(dict);
         	dict = {}
            dict[key['name']] = key['value'];
      	}
      });
	  list.push(dict);
	  vm.model_data['barcodes'] = list;
      vm.model_data.have_data = true;
      //$state.go('app.inbound.RevceivePo.barcode');
      var modalInstance = $modal.open({
        templateUrl: 'views/outbound/toggle/barcodes.html',
        controller: 'Barcodes',
        controllerAs: 'pop',
        size: 'lg',
        backdrop: 'static',
        keyboard: false,
        windowClass: 'z-2021',
        resolve: {
          items: function () {
            return vm.model_data;
          }
        }
      });

      modalInstance.result.then(function (selectedItem) {
        console.log(selectedItem);
      });
    }

    vm.vendor_receive = function(data) {

      if(data.$valid) {

        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall("confirm_vendor_received/", 'GET', elem, true).then(function(data){

          if(data.message) {

            if(data.data == "Updated Successfully") {

              vm.service.refresh(vm.dtInstance);
              vm.close();
            } else {
              pop_msg(data.data);
            }
          }
        });
      }
    }

    //firebase integrations
    var fb = {};
    vm.fb = fb;

  function po_fb_functions() {

    fb["poData"] = {serials: []};
    fb["generate"] = false;

    fb["exists"] = function(data) {
      var d = $q.defer();
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/").orderByChild("po").equalTo(data.po_reference).once("value", function(snapshot) {
        if(snapshot.val()) {
          var po = {}
          angular.forEach(snapshot.val(), function(data,v){
            po = data;
            po['id'] = v;
          })
          d.resolve({status: true, data: po});
        } else {
          d.resolve({status: false});
        }
      });
      return d.promise;
    }

    fb["push"] = function(data){
      var po = {};
      po["po"] = data.po_reference;
      po["serials"] = "";
      angular.forEach(data.data, function(sku){
        var fb_key = sku[0].sku_details[0].pk;
        //var fb_key = sku[0].wms_code;
        po[fb_key] = {};
        sku[0].value = 0;
        sku[0]["imei_list"] = [];
        po[fb_key]["quantity"] = sku[0].value;
        po[fb_key]["wms_code"] = sku[0].wms_code;
        po[fb_key]["serials"] = "";
      })
      console.log(po);
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId).push(po).then(function(data){
        console.log(data);
        fb.poData = po;
        fb.poData['id'] = data.path.o[2];
        console.log(fb.poData);
        fb.po_change_event();
        fb.po_generate_event();
        vm.fb.process = false;
      })
    }

    fb["push_po"] = function(data) {
      vm.fb.process = true;
      fb.exists(data).then(function(po){

        console.log(po);
        if(!po.status) {
          fb.push(data);
        } else {
          fb.poData = po.data;
          fb.change_po_data(fb.poData);
          fb.po_generate_event();
        }
      })
    }

    fb["change_serial"] = function(data, serial) {

      console.log(data.wms_code, serial);
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ data.sku_details[0].pk +"/serials/").push(serial);
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+vm.fb.poData.id+"/serials/").push(serial);
    }

    fb["change_po_data"] = function(data) {

      vm.fb.poData['serials'] = Object.values(vm.fb.poData['serials']);
      vm.serial_numbers = Object.values(vm.fb.poData['serials']);
      angular.forEach(vm.model_data.data, function(data){
        if(vm.fb.poData[data[0].sku_details[0].pk]) {
          data[0].value = Object.keys(vm.fb.poData[data[0].sku_details[0].pk]['serials']).length;
          data[0]['imei_list'] =  Object.values(vm.fb.poData[data[0].sku_details[0].pk]['serials']);
        }
      })
      fb.po_change_event();
      vm.fb.process = false;
      $timeout(function() {
        $scope.$apply();
      }, 500);
    }

    fb["po_change_event"] = function() {

        angular.forEach(vm.model_data.data, function(sku_data) {
          firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+sku_data[0].sku_details[0].pk+"/serials/").on("child_added", function(sku) {
            if(sku_data[0].imei_list.indexOf(sku.val()) == -1 && sku.val()) {
              sku_data[0].imei_list.push(sku.val());
              sku_data[0].value++;
              vm.serial_numbers.push(sku.val());
              $timeout(function() {
                $scope.$apply();
              }, 500);
            }
          })
        })

        /*firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+vm.fb.poData.id+"/").on("child_changed", function(sku) {
          console.log(sku.val());
          var response = sku.val();
          if(response["wms_code"]){
            for(var i=0; i < vm.model_data.data.length; i++) {
              if(response.wms_code == vm.model_data.data[i][0]['wms_code']) {
                vm.model_data.data[i][0]['value'] = Object.keys(response.serials).length;
                vm.model_data.data[i][0]['imei_list'] = Object.values(response.serials);
                vm.fb.poData[response.wms_code]['serials'] = Object.values(response.serials);
                $timeout(function() {
                  $scope.$apply();
                }, 500);
                break;
              }
            }
          } else {
            vm.fb.poData.serials = Object.values(response);
            vm.serial_number = vm.fb.poData.serials;
          }
        });*/
    }

    fb["po_generate_event"] = function() {

      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/").on("child_removed", function(po) {

        var delete_po = po.val();
        if(fb.poData.po == delete_po["po"] && vm.model_data.po_reference == delete_po["po"]) {
          fb.poData = {};
          if (!(fb.generate)) {

             SweetAlert.swal({
               title: '',
               text: 'Generated GRN Successfully',
               type: 'success',
               showCancelButton: false,
               confirmButtonColor: '#33cc66',
               confirmButtonText: 'Ok',
               closeOnConfirm: true,
             },
             function (status) {
               vm.close();
               }
             );
            //vm.close();
          }
        }
        console.log(po);
      })
    }

    fb["remove_po"] = function(po) {

      if(po) {
        firebase.database().ref("/GRNLogs/"+Session.parent.userId+"/").push(vm.fb.poData);
        firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+po).once("value", function(data){
          data.ref.remove()
            .then(function() {
              console.log("Remove succeeded.")
            })
            .catch(function(error) {
              console.log("Remove failed: " + error.message)
            });
          console.log(data.ref.remove())
        })
      }
    }

    fb["stop_listening"] = function(po) {

      var data = po;

      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+data.id+"/").off();
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/").off();
    }

    fb["stop_fb"] = function() {

      fb.stop_listening(fb.poData);
      fb["poData"] = {serials: []};
      fb["generate"] = false;
    }

    fb["check_imei"] = function(imei) {
      var d = $q.defer();
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/").once("value", function(snapshot){
        if(snapshot.val()) {
          var found = false;
          var po_data = snapshot.val();
          angular.forEach(po_data, function(po) {
            if (typeof(po.serials) != "string") {
              angular.forEach(po.serials, function(serial) {
                if (imei == serial) {
                  found = true;
                  d.resolve({status: true, data: po});
                }
              })
            }
          })
          d.resolve({status: found});
        } else {
          d.resolve({status: false});
        }
      });
      return d.promise;
    }
  }


  function po_qc_fb_functions() {

    fb["poData"] = {serials: []};
    fb["generate"] = false;
    fb["add_new"] = false;

    fb["exists"] = function(data) {
      var d = $q.defer();
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/").orderByChild("po").equalTo(data.po_reference).once("value", function(snapshot) {
        if(snapshot.val()) {
          var po = {}
          angular.forEach(snapshot.val(), function(data,v){
            po = data;
            po['id'] = v;
          })
          d.resolve({status: true, data: po});
        } else {
          d.resolve({status: false});
        }
      });
      return d.promise;
    }

    fb["push"] = function(data){
      var po = {};
      po["po"] = data.po_reference;
      po["serials"] = "";
      angular.forEach(data.data, function(sku){
        var name = sku[0].sku_details[0].pk;
        po[name] = {};
        po[name]["wms_code"] = sku[0].wms_code;
        po[name]["accepted"] = "";
        po[name]["rejected"] = "";
      })
      console.log(po);
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId).push(po).then(function(data){

        fb.poData = po;
        fb.poData['id'] = data.path.o[2];
        fb.delete_accept_serial(fb.poData);
        fb.added_reject_serial(fb.poData);
        fb.added_accept_serial(fb.poData);
        fb.qc_confirm_event();
        fb.change_po_data(fb.poData);
      })
    }

    fb["push_po"] = function(data) {
      angular.forEach(data.data, function(record){

        record[0]["accepted_quantity"] = 0;
        record[0]["rejected_quantity"] = 0;
        record[0]["accept_imei"] = [];
        record[0]["reject_imei"] = [];
      });
      fb.exists(data).then(function(po){

        console.log(po);
        if(!po.status) {
          fb.push(data);
        } else {
          fb.poData = po.data;
          fb.delete_accept_serial(fb.poData);
          fb.added_reject_serial(fb.poData);
          fb.added_accept_serial(fb.poData);
          fb.qc_confirm_event();
          fb.change_po_data(fb.poData);
        }
      })
    }

    fb["add_new"] = false;
    fb["change_po_data"] = function(data) {

      vm.fb.poData['serials'] = Object.values(vm.fb.poData['serials']);
      vm.imei_list = vm.fb.poData['serials'];
      angular.forEach(vm.model_data.data, function(data){
        var name= data[0].sku_details[0].pk;
        if(vm.fb.poData[name]) {
          if(!vm.fb.poData[name]['accepted']){vm.fb.poData[name]['accepted'] = {}}
          if(!vm.fb.poData[name]['rejected']){vm.fb.poData[name]['rejected'] = {}}
          data[0].accepted_quantity = Object.keys(vm.fb.poData[name]['accepted']).length;
          data[0].rejected_quantity = Object.keys(vm.fb.poData[name]['rejected']).length;
          data[0].accept_imei =  Object.values(vm.fb.poData[name]['accepted']);
          data[0].reject_imei =  Object.values(vm.fb.poData[name]['rejected']);
          data[0].value = data[0].accepted_quantity + data[0].rejected_quantity;
          $timeout(function() {$scope.$apply();}, 500);
        }
      })
      fb.add_new = true;

    }

    fb["recent_accept"] = "";
    fb["accept_serial"] = function(data, serial) {

      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ data.sku_details[0].pk +"/accepted/").push(serial).then(function(snapshot){

        fb["recent_accept"] = snapshot.path.o[5];
      });
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/serials/").push(serial);
    }

    fb["reject_serial"] = function(data, serial) {

      var name= data.sku_details[0].pk;
      if(fb.recent_accept) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/accepted/"+fb.recent_accept).once("value", function(snapshot) {
          snapshot.ref.remove();
        })
      }
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/rejected/").push(serial);
      //firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/serials/").push(serial);
    }

    fb["remove_add_serial"] = function(data, serial1, serial2, remove_from, add_to) {

      var name= data.sku_details[0].pk;
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+remove_from+"/").once("value", function(snapshot) {
        if(snapshot.val()) {
          var status = true;
          angular.forEach(snapshot.val(), function(value,key) {
            if(serial1 == value && status) {
              status = false;
              firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+remove_from+"/"+key).once("value", function(snapshot) {
                snapshot.ref.remove();
              })
            }
          })
        }
      })
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+add_to+"/").push(serial2);
    }

    fb["delete_accept_serial"] = function() {

      angular.forEach(vm.fb.poData, function(value, key) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+key + "/accepted/").on("child_removed", function(snapshot) {
          if(snapshot.V.path.o[4] == "accepted") {

            if(vm.model_data['data']) {
              var sku_data = snapshot.V.path.o[3];
              for(var i=0; i < vm.model_data.data.length; i++) {

                var sku = vm.model_data.data[i][0];
                if(sku.wms_code == sku_data) {

                  var imei = snapshot.val();
                  var index = sku.accept_imei.indexOf(imei);
                  if(index != -1) {
                    vm.model_data.data[i][0].accept_imei.splice(index, 1);
                    vm.model_data.data[i][0].accepted_quantity -= 1;
                    vm.model_data.data[i][0].value = vm.model_data.data[i][0].accepted_quantity + vm.model_data.data[i][0].rejected_quantity;
                    $timeout(function() {$scope.$apply();}, 500);
                  };
                  break;
                }
              }
            }
          }
        })
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+key + "/rejected/").on("child_removed", function(snapshot) {
          if(snapshot.V.path.o[4] == "rejected") {

            if(vm.model_data['data']) {
              var sku_data = snapshot.V.path.o[3];
              for(var i=0; i < vm.model_data.data.length; i++) {

                var sku = vm.model_data.data[i][0];
                if(sku.wms_code == sku_data) {

                  var imei = snapshot.val();
                  var index = sku.reject_imei.indexOf(imei);
                  if(index != -1) {
                    vm.model_data.data[i][0].reject_imei.splice(index, 1);
                    vm.model_data.data[i][0].rejected_quantity -= 1;
                    vm.model_data.data[i][0].value = vm.model_data.data[i][0].accepted_quantity + vm.model_data.data[i][0].rejected_quantity;
                    $timeout(function() {$scope.$apply();}, 500);
                  };
                  break;
                }
              }
            }
          }
        })
      })
    }

    fb["added_reject_serial"] = function() {

      angular.forEach(vm.fb.poData, function(value, key) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ key + "/rejected/" ).on("child_added", function(snapshot) {
          if(snapshot.V.path.o[4] == "rejected" && fb.add_new) {

            var sku_data = snapshot.V.path.o[3];
            for(var i=0; i < vm.model_data.data.length; i++) {

              var sku = vm.model_data.data[i][0];
              if(sku.wms_code == sku_data) {

                var imei = snapshot.val();
                var index = sku.reject_imei.indexOf(imei);
                if(index == -1) {
                  vm.model_data.data[i][0].reject_imei.push(imei);
                  vm.model_data.data[i][0].rejected_quantity += 1;
                  vm.model_data.data[i][0].value = vm.model_data.data[i][0].accepted_quantity + vm.model_data.data[i][0].rejected_quantity;
                  if (vm.imei_list.indexOf(imei) == -1) {
                    vm.imei_list.push(imei);
                    vm.fb.poData.serials.push(imei);
                  }
                  $timeout(function() {$scope.$apply();}, 500);
                }
                break;
              }
            }
           }
        })
      })
    }

    fb["added_accept_serial"] = function() {

      angular.forEach(vm.fb.poData, function(value, key) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ key + "/accepted/" ).on("child_added", function(snapshot) {
          if(snapshot.V.path.o[4] == "accepted" && fb.add_new) {

            var sku_data = snapshot.V.path.o[3];
            for(var i=0; i < vm.model_data.data.length; i++) {

              var sku = vm.model_data.data[i][0];
              if(sku.wms_code == sku_data) {

                var imei = snapshot.val();
                var index = sku.accept_imei.indexOf(imei);
                if(index == -1) {
                  vm.model_data.data[i][0].accept_imei.push(imei);
                  vm.model_data.data[i][0].accepted_quantity += 1;
                  vm.model_data.data[i][0].value = vm.model_data.data[i][0].accepted_quantity + vm.model_data.data[i][0].rejected_quantity;
                  if (vm.imei_list.indexOf(imei) == -1) {
                    vm.imei_list.push(imei);
                    vm.fb.poData.serials.push(imei);
                  }
                  $timeout(function() {$scope.$apply();}, 500);
                }
                break;
              }
            }
          }
        })
      })
    }

    fb["qc_confirm_event"] = function() {

      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/").on("child_removed", function(po) {

        var delete_po = po.val();
        if(fb.poData.po == delete_po["po"] && vm.model_data.po_reference == delete_po["po"]) {
          fb.poData = {};
          if (!(fb.generate)) {

             fb.stop_listening(delete_po["po"]);
             SweetAlert.swal({
               title: '',
               text: 'Receiv+QC confirmed Successfully',
               type: 'success',
               showCancelButton: false,
               confirmButtonColor: '#33cc66',
               confirmButtonText: 'Ok',
               closeOnConfirm: true,
             },
             function (status) {
               vm.close();
               }
             );
            //vm.close();
          }
        }
        console.log(po);
      })
    }

    fb["remove_po"] = function(po) {

      if(po) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+po).once("value", function(data){
          data.ref.remove()
            .then(function() {
              console.log("Remove succeeded.")
            })
            .catch(function(error) {
              console.log("Remove failed: " + error.message)
            });
          console.log(data.ref.remove())
        })
      }
    }

    fb["stop_listening"] = function(po) {

      var data = po;
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+data.id).off();
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/").off();

      angular.forEach(data, function(value, key) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+data.id+"/"+key + "/").off();
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+data.id+"/"+ key + "/rejected/" ).off();
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+data.id+"/"+ key + "/accepted/" ).off();
      })
    }

    fb["stop_fb"] = function() {

      fb.stop_listening(fb.poData);
      fb["poData"] = {serials: []};
      fb["generate"] = false;
      fb["add_new"] = false;
    }

    fb["check_imei"] = function(imei) {
      var d = $q.defer();
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/").once("value", function(snapshot){
        if(snapshot.val()) {
          var found = false;
          var po_data = snapshot.val();
          angular.forEach(po_data, function(po) {
            if (typeof(po.serials) != "string") {
              angular.forEach(po.serials, function(serial) {
                if (imei == serial) {
                  found = true;
                  d.resolve({status: true, data: po});
                }
              })
            }
          })
          d.resolve({status: found});
        } else {
          d.resolve({status: false});
        }
      });
      return d.promise;
    }
  }

  if(vm.po_qc) {
    po_qc_fb_functions();
  } else {
    po_fb_functions();
  }

  vm.accept_qc = function(data, field) {

      vm.enable_button = false;
      var sku = vm.model_data.data[vm.current_index][0];
      sku.accepted_quantity = Number(sku.accepted_quantity) + 1;
      // sku.value = Number(sku.value) + 1;
      sku.value = Number(sku.accepted_quantity) + Number(sku.rejected_quantity);

      sku["accept_imei"].push(field);
      vm.model_data.data[vm.current_index][0] = sku

      fb.accept_serial(sku, field);
      vm.serial_scan = "";
    }

    vm.selected = "";
    vm.reject_qc = function(imei) {

      focus('focusSKU');
      vm.reason_show = false;
      var sku = vm.model_data.data[vm.current_index][0];
      var field = "";
      if(!imei) {

        sku.accepted_quantity = Number(sku.accepted_quantity) - 1;
        var index = sku["accept_imei"].length-1;
        var field = sku["accept_imei"][index].split("<<>>")[0];
        sku["accept_imei"].splice(index,1);
      } else {
        field = imei.toUpperCase();
      }
      sku.rejected_quantity = Number(sku.rejected_quantity) + 1;

      if(!(sku["reject_imei"])) {
        sku["reject_imei"] = [];
      }
      var imei = field+"<<>>"+vm.selected;
      sku["reject_imei"].push(imei);

      if(vm.permissions.use_imei) {
        fb.reject_serial(sku, imei);
      }

      vm.selected="";
    }

    vm.status_imei = "";
    vm.status_scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field.length > 0) {
        field = field.toUpperCase();
        vm.enable_button = true;
        vm.reason_show = false;
        vm.current_sku = "";
        var data = {imei: field, order_id: vm.model_data.order_id};
        if(vm.imei_list.indexOf(field) != -1) {
          vm.status_move_imei(field);
        } else {
          vm.service.apiCall('check_imei_qc/', 'GET', data).then(function(data){
            if(data.data.status == "") {

              vm.service.showNoty("Yet to scan IMEI")
            } else {

              vm.service.showNoty(data.data.status);
            }
          })
        }
        vm.status_imei = "";
      }
    }

    vm.status_move_imei = function(field) {
      field = field.toUpperCase();
      for(var i = 0; i < vm.model_data.data.length; i++) {

        var data = vm.model_data.data[i][0];
        var reject = vm.status_ac_rj(field, data.reject_imei);
        var accept = vm.status_ac_rj(field, data.accept_imei);
        if(reject != -1) {

          vm.status_imei_here(i, reject, "reject_imei", field);
          vm.current_index = i;
          vm.model_data1["sku_data"] = data.sku_details[0].fields;
          break;
        } else if(accept != -1) {

          vm.current_index = i;
          vm.model_data1["sku_data"] = data.sku_details[0].fields;
          vm.status_imei_here(i, accept, "accept_imei", field);
          break;
        }
      }
    }

    vm.status_imei_here = function(index1, index2, from_data, field) {

      var msg = "Accepted. Move to Reject State?"
      if(from_data == "reject_imei") {
        msg = "Rejected. Move to Accept State?"


        $timeout(function() {
          swal2({
            title: '',
            text: 'Rejected. Move to Accept State?',
            showCancelButton: true,
          }).then(function (result) {
            var serial1 = vm.model_data.data[index1][0][from_data][index2];
            vm.model_data.data[index1][0][from_data].splice(index2, 1);
            var from = "rejected";
            var to = "accepted";
            vm.model_data.data[index1][0].rejected_quantity -= 1;
            var serial2 = serial1.split("<<>>");
            serial2 = serial2[0]
            fb.remove_add_serial(vm.model_data.data[index1][0], serial1, serial2, from, to)
           });
         }, 100);

      } else {
        vm.model_data.reasons = {};
        angular.forEach(vm.model_data.options, function(reason){
          vm.model_data.reasons[reason] = reason;
        })
        $timeout(function() {
          swal2({
            title: '',
            text: 'Accepted. Move to Reject State?',
            input: 'select',
            inputOptions: vm.model_data.reasons,
            inputPlaceholder: 'Select Reason',
            showCancelButton: true,
          }).then(function (result) {
            var serial1 = vm.model_data.data[index1][0][from_data][index2];
            vm.model_data.data[index1][0][from_data].splice(index2, 1);
            var to = "rejected";
            var from = "accepted";
            vm.model_data.data[index1][0].accepted_quantity -= 1;
            var serial2 = serial1.split("<<>>");
            serial2 = serial2[0]+"<<>>"+result;
            fb.remove_add_serial(vm.model_data.data[index1][0], serial1, serial2, from, to)
          })
        },100);
      }
    }

    vm.status_ac_rj = function(field, data){

      var index = -1;
      for(var i = 0; i < data.length; i++) {

        if(field == data[i].split("<<>>")[0]) {

          index = i;
          break;
        }
      }
      return index;
    }

  //GRN Pop Data
  vm.grn_details = {po_reference: 'PO Reference', supplier_id: 'Supplier ID', supplier_name: 'Supplier Name',
                    order_date: 'Order Date'}
  vm.grn_details_keys = Object.keys(vm.grn_details);

  vm.change_datatable = function() {
      Data.receive_po.style_view = vm.g_data.style_view;
      $state.go($state.current, {}, {reload: true});
  }

  vm.preview = function(order_detail_id, flag=false) {
    if (flag) {
      var data = {order_id: vm.order_id};
    } else {
      var data = {order_id: order_detail_id};
    }
    vm.service.apiCall("get_view_order_details/", "GET", data).then(function(data){

      var all_order_details = data.data.data_dict[0].ord_data;
      vm.ord_status = data.data.data_dict[0].status;
      var modalInstance = $modal.open({
        templateUrl: 'views/outbound/toggle/customOrderDetailsTwo.html',
        controller: 'customOrderDetails',
        controllerAs: 'pop',
        size: 'lg',
        backdrop: 'static',
        keyboard: false,
        resolve: {
          items: function () {
            return all_order_details;
          }
        }
      });
    });
  }
  vm.invoice_readonly_option = false;
  vm.invoice_readonly = function(event, data, key_name, is_number){
      console.log(vm);
      if(vm.permissions.receive_po_invoice_check)
      {
        if(!vm.model_data.invoice_value || vm.model_data.invoice_value == "0")
        {
          Service.showNoty('Please fill the invoice value');
          if(is_number) {
            data[key_name] = 0;
          }
          else {
            data[key_name] = '';
          }
        }
        else
        {
          vm.invoice_readonly_option = true;
        }
      }
  }
  vm.skus_total_amount = 0;
  vm.calc_total_amt = function(event, data, index, parent_index) {
      var sku_row_data = {};
      angular.copy(data.data[parent_index][index], sku_row_data);
      if(sku_row_data.buy_price == ''){
        sku_row_data.buy_price = 0;
      }
      if(sku_row_data.value == ''){
        sku_row_data.value = 0;
      }
      if(sku_row_data.tax_percent == ''){
        sku_row_data.tax_percent = 0;
      }
      if(sku_row_data.cess_percent == ''){
        sku_row_data.cess_percent = 0;
      }
      if(sku_row_data.apmc_percent == ''){
        sku_row_data.apmc_percent = 0;
      }
      if(sku_row_data.discount_percentage == ''){
        sku_row_data.discount_percentage = 0;
      }

      if (Number(sku_row_data.tax_percent)) {

        sku_row_data.tax_percent = Number(sku_row_data.tax_percent).toFixed(1)
      }

      if (Number(sku_row_data.cess_percent)) {

        sku_row_data.cess_percent = Number(sku_row_data.cess_percent).toFixed(1)
      }

      vm.singleDecimalVal(sku_row_data.tax_percent, 'tax_percent', index, parent_index);
      vm.singleDecimalVal(sku_row_data.cess_percent, 'cess_percent', index, parent_index);
      vm.singleDecimalVal(sku_row_data.apmc_percent, 'apmc_percent', index, parent_index);

      if (vm.industry_type == 'FMCG') {
        var total_amt = Number(sku_row_data.value)*Number(sku_row_data.buy_price);
      } else {
        var total_amt = Number(sku_row_data.value)*Number(sku_row_data.price);
      }

      var total_amt_dis = Number(total_amt) * Number(sku_row_data.discount_percentage) / 100;
      var tot_tax = Number(sku_row_data.tax_percent) + Number(sku_row_data.cess_percent) +
                    Number(sku_row_data.apmc_percent);
      var wo_tax_amt = Number(total_amt)-Number(total_amt_dis);
      data.data[parent_index][index].total_amt = wo_tax_amt + (wo_tax_amt * (tot_tax/100));

      var totals = 0;
      for(var index in data.data) {
        var rows = data.data[index];
        for (var d in rows) {
            if(!isNaN(rows[d]['total_amt'])) {
                totals += rows[d]['total_amt'];
            }
        }
      }
      var overall_discount = 0;
      if(vm.model_data.overall_discount) {
        overall_discount = vm.model_data.overall_discount;
      }
      vm.skus_total_amount = totals;
      //$('.totals').text('Totals: ' + totals);
      vm.model_data.round_off_total = (Math.round(totals * 100) / 100) - overall_discount;
    }

    vm.pull_cls = "pull-right";
    vm.margin_cls = {marginRight: '50px'};
    vm.round_off_effects = function(key){

      vm.pull_cls = key ? 'pull-left' : 'pull-right';
      vm.margin_cls = key ? {marginRight: '0px'} : {marginRight: '50px'};
    }

    vm.singleDecimalVal = function(value, field, inIndex, outIndex){

      if (Number(value)) {

        vm.model_data.data[outIndex][inIndex][field] = Number(value).toFixed(1);
      }
    }

  vm.check_mrp_buy_price = function(event, data, index, parent_index) {
    var sku_row_data = {};
    angular.copy(data.data[parent_index][index], sku_row_data);
    if(sku_row_data.buy_price == ''){
      sku_row_data.buy_price = 0;
    }
    if(sku_row_data.mrp == ''){
      sku_row_data.mrp = 0;
    }
    if(Number(sku_row_data.buy_price) > Number(sku_row_data.mrp)){
      pop_msg("Buy Price should be less than or equal to MRP");
      data.data[parent_index][index]['buy_price'] = sku_row_data.mrp;
    }
  }

    vm.send_for_approval_check = function(event, data) {
    if(vm.milkbasket_users.indexOf(vm.parent_username) < 0){
      return
    }
    if(vm.permissions.change_purchaseorder) {
      return
    }
    vm.display_approval_button = false;
    var total_po_data = [];
    angular.copy(data.data, total_po_data);
    angular.forEach(total_po_data, function(sku_row_data) {
      var tot_qty = 0;
      for(var i=0;i<sku_row_data.length;i++) {
        if(sku_row_data[i].value == '') {
          sku_row_data[i].value = 0;
        }
        tot_qty += Number(sku_row_data[i].value);
        if(!sku_row_data[i].buy_price || sku_row_data[i].buy_price == '') {
          sku_row_data[i].buy_price = 0;
        }
        var price_tolerence = 0;
        var buy_price = Number(sku_row_data[i].buy_price);
        var price = Number(sku_row_data[i].price);
        if(price && (buy_price > price))  {
          price_tolerence = ((buy_price-price)/price)*100;
          if(price_tolerence > 2){
            vm.display_approval_button = true;
            break;
          }
        }
//        if(sku_row_data[i].price != sku_row_data[i].buy_price){
//          vm.display_approval_button = true;
//          break;
//        }
        if(sku_row_data[i].tax_percent == '') {
          sku_row_data[i].tax_percent = 0;
        }
        if(sku_row_data[i].tax_percent != sku_row_data[i].tax_percent_copy){
          vm.display_approval_button = true;
          break;
        }
      }
      var po_quantity = 0;
      if(sku_row_data[0].po_quantity != '') {
        po_quantity = sku_row_data[0].po_quantity;
      }
      if(po_quantity && po_quantity < tot_qty) {
        var abs_qty_value = vm.absOfQtyTolerence(po_quantity, tot_qty);
        console.log(abs_qty_value);
        if(tot_qty > abs_qty_value) {
          vm.display_approval_button = true;
        }
      }
    })
  }

  vm.file_size_check = function(event, file_obj) {
    var file_size = ($(".grn-form").find('[name="files"]')[0].files[0].size/1024)/1024;
    if(file_size > 10) {
      return true;
    }
    else {
      return false;
    }
  }

}

stockone.directive('dtPoData', function() {
  return {
    restrict: 'E',
    scope: {
      po_data: '=data',
      preview: '=preview'
    },
    templateUrl: 'views/inbound/toggle/po_data_html.html',
    link: function(scope, element, attributes, $http){
      console.log(scope);
    }
  };
});

})();

angular.module('urbanApp').controller('addNewSkuCtrl', function ($modalInstance, $modal, items, Service, Data, Session) {
  var $ctrl = this;
  $ctrl.model_data = {};
  angular.copy(items, $ctrl.model_data);
  $ctrl.service = Service;
  $ctrl.processing = false;
  $("#map_sku_code").focus();
  $ctrl.service.popup_dyn_style = 155;

  $ctrl.ok = function (form) {

    if($ctrl.model_data.map_sku_code) {

      $ctrl.processing = true;
      var data = {ean_number: $ctrl.model_data.scanned_val, map_sku_code: $ctrl.model_data.map_sku_code};

      Service.apiCall("map_ean_sku_code/", "GET", data).then(function(data) {

        if(data.message) {

          // console.log(data.data.data);
          Service.showNoty('Your scanned sku mapped');
          $ctrl.close();
        }
        $ctrl.processing = false;
      });
    } else {

      $ctrl.service.showNoty("Please Select SKU")
    }
  };

  $ctrl.close = function () {

    $modalInstance.dismiss('cancel');
  };
});
