'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CustomerInvoiceCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;

    vm.selected = {};
    vm.checked_items = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.display = false;
    vm.extra_width = {'width': '1100px'};

    if (vm.user_type == 'distributor') {
      vm.service.apiCall("customer_invoice_data/").then(function(data) {
        if(data.message) {
          vm.filters = {'datatable': 'CustomerInvoices', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
            .withOption('drawCallback', function(settings) {
              vm.service.make_selected(settings, vm.selected);
            })
            .withOption('processing', true)
            .withOption('serverSide', true)
            .withOption('order', [5, 'desc'])
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
            .withOption('initComplete', function( settings ) {
              //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
            });

          var columns = data.data.headers;
          var not_sort = ['Order Quantity', 'Picked Quantity']
          vm.dtColumns = vm.service.build_colums(columns, not_sort);
          var row_click_bind = 'td';
          vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle('').notSortable().withOption('width', '20px')
                 .renderWith(function(data, type, full, meta) {
                   // if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                   //   vm.selected = {};
                   // }
                   // vm.selected[meta.row] = vm.selectAll;
                   return "<i style='cursor: pointer' ng-click='showCase.addRowData($event, "+JSON.stringify(full)+")' class='fa fa-plus-square'></i>";
                 }))
          row_click_bind = 'td:not(td:first)';
          vm.dtInstance = {};

          $scope.$on('change_filters_data', function(){
            if($("#"+vm.dtInstance.id+":visible").length != 0) {
              vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
              vm.service.refresh(vm.dtInstance);
            }
          });
          vm.display = true;
        }
      });
    } else {
      var send = {'tabType': 'ProcessedOrders'};
      vm.service.apiCall("customer_invoice_data/", "GET", send).then(function(data) {
        if(data.message) {
          vm.filters = {'datatable': 'ProcessedOrders', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
            .withOption('drawCallback', function(settings) {
              vm.service.make_selected(settings, vm.selected);
            })
            .withOption('processing', true)
            .withOption('serverSide', true)
            .withOption('order', [5, 'desc'])
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
            .withOption('initComplete', function( settings ) {
              //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
            });

          var columns = data.data.headers;
          var not_sort = ['Order Quantity', 'Picked Quantity']
          vm.dtColumns = vm.service.build_colums(columns, not_sort);
          vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle('').notSortable().withOption('width', '20px')
                 .renderWith(function(data, type, full, meta) {
                   if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                     vm.selected = {};
                   }
                   vm.selected[meta.row] = vm.selectAll;
                   return vm.service.frontHtml + meta.row + vm.service.endHtml;
                 }))

          vm.dtInstance = {};

          $scope.$on('change_filters_data', function(){
            if($("#"+vm.dtInstance.id+":visible").length != 0) {
              vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
              vm.service.refresh(vm.dtInstance);
            }
          });
          vm.display = true;
        }
      });
    }

    vm.checked_ids = [];
    vm.checkedItem = function(data, index){
      
      if (vm.checked_items[index]) {
        
        delete vm.checked_items[index];
      } else {
        
        vm.checked_items[index] = data;
        vm.checked_ids.push(vm.checked_items[index].id);
      }
      // vm.checked_items[index] = data;
      console.log(data)      
    }

    vm.generateInvoice = function(){
      console.log("Checked Items::", vm.checked_items);
      var data = [];
      angular.forEach(vm.checked_items, function(row){
        data.push(row['id']);
      });
      var ids = data.join(",");
      var send = {seller_summary_id: ids};
      vm.service.apiCall("generate_customer_invoice/", "GET", send).then(function(data){

        if (data.message) {
          console.log(data);
          if(data.message) {
          vm.pdf_data = data.data;
          if(typeof(vm.pdf_data) == "string" && vm.pdf_data.search("print-invoice") != -1) {
            $state.go("app.outbound.CustomerInvoices.InvoiceE");
            $timeout(function () {
              $(".modal-body:visible").html(vm.pdf_data)
            }, 3000);
          } else if(Session.user_profile.user_type == "marketplace_user") {
            $state.go("app.outbound.CustomerInvoices.InvoiceM");
          } else if(vm.permissions.detailed_invoice) {
            $state.go("app.outbound.CustomerInvoices.InvoiceD");
          } else {
            $state.go("app.outbound.CustomerInvoices.InvoiceN");
          }
          }
          vm.service.showNoty("Invoice generated");
        }
      });
    }

    vm.addRowData = function(event, data) {
      vm.checked_items = {};
      console.log(data);
      var elem = event.target;
      if (!$(elem).hasClass('fa')) {
        return false;
      }
      var data_tr = angular.element(elem).parent().parent();
      var all_tr = angular.element(elem).parent().parent().siblings();
      
      for (var i = 0; i < all_tr.length; i++) {

        if (all_tr[i].cells[0].children[0].className == 'fa fa-minus-square') {
        
          all_tr[i].cells[0].children[0].className = 'fa fa-plus-square'
          all_tr[i].nextSibling.remove();
        }
      }

      if ($(elem).hasClass('fa-plus-square')) {
        $(elem).removeClass('fa-plus-square');
        $(elem).removeClass();
        $(elem).addClass('glyphicon glyphicon-refresh glyphicon-refresh-animate');
        Service.apiCall('get_invoice_details/?gen_id='+data['Gen Order Id']+'&customer_id='+data['Customer ID']).then(function(resp){
          if (resp.message){

            if(resp.data.status) {
              // var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='11'><dt-po-data data='"+JSON.stringify(resp.data.data_dict)+"'></dt-po-data></td></tr>")($scope);
              var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='11'><generic-customer-invoice-data data='"+JSON.stringify(resp.data.data_dict)+"'></generic-customer-invoice-data></td></tr>")($scope);
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

    vm.close = function() {

      $state.go("app.outbound.CustomerInvoices")
    }

    vm.edit_invoice = function() {

      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
          data.push(temp['id']);
        }
      });
      var ids = data.join(",");
      var send = {seller_summary_id: ids, data: true};
      vm.service.apiCall("generate_customer_invoice/", "GET", send).then(function(data){

        if (data.message) {
        var mod_data = data.data;
        var modalInstance = $modal.open({
          templateUrl: 'views/outbound/toggle/edit_invoice.html',
          controller: 'EditInvoice',
          controllerAs: 'pop',
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
          var data = selectedItem;
        })
        }
      })
    }

    vm.delivery_challan = false;

    vm.pdf_data = {};

    vm.move_to = function (click_type) {
      var po_number = '';
      var status = false;
      var field_name = "";
      var data = [];
      var selected_customers = [];
      if (vm.user_type == 'distributor') {
        data = vm.checked_ids;
      } else {
        angular.forEach(vm.selected, function(value, key) {
          if(value) {
            var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
            if(selected_customers.indexOf(temp['Customer Name']) == -1) {
              selected_customers.push(temp['Customer Name']);
            }
            if(!(po_number)) {
              po_number = temp[temp['check_field']];
            } else if (po_number != temp[temp['check_field']]) {
              //status = true;
              console.log("true");
            }
            field_name = temp['check_field'];
            data.push(temp['id']);
          }
        });
      }

      if(selected_customers.length > 1){
        vm.service.showNoty("Please select one customer orders only");
        return
      }
      if(status) {
        vm.service.showNoty("Please select same "+field_name+"'s");
      } else {

        var ids = data.join("<<>>");
        var url = click_type === 'move_to_dc' ? 'move_to_dc/' : 'move_to_inv/';
        var send = {seller_summary_id: ids};
        vm.bt_disable = true;
        vm.service.apiCall(url, "GET", send).then(function(data){
          if(data.message) {
            console.log(data.message);
            vm.reloadData();
          } else {
            vm.service.showNoty("Something went wrong while moving to DC !!!");
          }
        })
      }
    };

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };

    vm.generate_invoice = function(click_type, DC=false){

      var po_number = '';
      var status = false;
      var field_name = "";
      var data = [];
      if (vm.user_type == 'distributor') {
        data = vm.checked_ids;
      } else {
        angular.forEach(vm.selected, function(value, key) {
          if(value) {
            var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
            if(!(po_number)) {
              po_number = temp[temp['check_field']];
            } else if (po_number != temp[temp['check_field']]) {
              status = true;
            }
            field_name = temp['check_field'];
            data.push(temp['id']);
          }
        });
      }

      if(status) {
        vm.service.showNoty("Please select same "+field_name+"'s");
      } else {

        var ids = data.join(",");
        var send = {seller_summary_id: ids};
        if(po_number && field_name == 'SOR ID') {
          send['sor_id'] = po_number;
        }
        if(click_type == 'edit'){
          send['data'] = true;
          send['edit_invoice'] = true;
        }
        send['delivery_challan'] = DC;
        vm.delivery_challan = DC;
        vm.bt_disable = true;
        vm.service.apiCall("generate_customer_invoice/", "GET", send).then(function(data){

          if(data.message) {
            if(click_type == 'generate') {
              vm.pdf_data = data.data;
              if(typeof(vm.pdf_data) == "string" && vm.pdf_data.search("print-invoice") != -1) {
                $state.go("app.outbound.CustomerInvoices.InvoiceE");
                $timeout(function () {
                  $(".modal-body:visible").html(vm.pdf_data)
                }, 3000);
              } else if(Session.user_profile.user_type == "marketplace_user") {
                $state.go("app.outbound.CustomerInvoices.InvoiceM");
              } else if(vm.permissions.detailed_invoice) {
                $state.go("app.outbound.CustomerInvoices.InvoiceD");
              } else {
                $state.go("app.outbound.CustomerInvoices.InvoiceN");
              }
            } else {
              var mod_data = data.data;
              var modalInstance = $modal.open({
              templateUrl: 'views/outbound/toggle/edit_invoice.html',
              controller: 'EditInvoice',
              controllerAs: 'pop',
              size: 'lg',
              backdrop: 'static',
              keyboard: false,
              resolve: {
                items: function () {
                  return mod_data;
                }
              }
              });

              modalInstance.result.then(function (selectedItem) {
                var data = selectedItem;
              })
            }
          }
          vm.bt_disable = false;
        });
      }
    }

    vm.inv_height = 1358; //total invoice height
    vm.inv_details = 292; //invoice details height
    vm.inv_footer = 95;   //invoice footer height
    vm.inv_totals = 127;  //invoice totals height
    vm.inv_header = 47;   //invoice tables headers height
    vm.inv_product = 47;  //invoice products cell height
    vm.inv_summary = 47;  //invoice summary headers height
    vm.inv_total = 27;    //total display height

    vm.render_data = []
    vm.invoiceAdjust = function(data){
      vm.render_data = []
      var render_space = 0;
      var hsn_summary_length= (Object.keys(data.hsn_summary).length)*vm.inv_total;
      if(vm.permissions.hsn_summary) {
        render_space = vm.inv_height-(vm.inv_details+vm.inv_footer+vm.inv_totals+vm.inv_header+vm.inv_summary+vm.inv_total+hsn_summary_length);
      } else {
        render_space = vm.inv_height-(vm.inv_details+vm.inv_footer+vm.inv_totals+vm.inv_header+vm.inv_total)
      }
      var no_of_skus = parseInt(render_space/vm.inv_product);
      var data_length = data.data.length;
      vm.pdf_data.empty_data = [];
      if(data_length > no_of_skus) {

        var needed_space = vm.inv_footer + vm.inv_footer + vm.inv_total;
        if(vm.permissions.hsn_summary) {
          needed_space = needed_space+ vm.inv_summary+hsn_summary_length;
        }

        var temp_render_space = 0;
        temp_render_space = vm.inv_height-(vm.inv_details+vm.inv_header);
        var temp_no_of_skus = parseInt(temp_render_space/vm.inv_product);

        if(data_length > temp_no_of_skus) {
          for(var i=0; i<Math.ceil(data_length/temp_no_of_skus); i++) {
            var temp_page = {data: []}
            temp_page.data = data.data.slice(i*temp_no_of_skus,((i+1)*temp_no_of_skus));
            temp_page["empty_data"] = [];
            vm.render_data.push(temp_page);
          }
        }
        console.log(data_length);

        var last = vm.render_data.length - 1;
        data_length = vm.render_data[last].data.length;
        if(no_of_skus < data_length) {
          vm.render_data.push({empty_data: [], data: [vm.render_data[last].data[data_length-1]]});
          vm.render_data[last].data.splice(data_length-1,1);
        }

        last = vm.render_data.length - 1;
        data_length = vm.render_data[last].data.length;
        var empty_data = [];
        for(var i = 0; i < (no_of_skus - data_length); i++) {
          empty_data.push(i);
        }
        vm.render_data[last].empty_data = empty_data;

        vm.pdf_data.data = vm.render_data;
      } else if(data_length < no_of_skus) {

        var temp = vm.pdf_data.data;
        vm.pdf_data.data = [];
        var empty_data = [];
        for(var i = 0; i < (no_of_skus - data_length); i++) {
          empty_data.push(i);
        }
        vm.pdf_data.data[0] = {data: temp, empty_data: empty_data}
      }
      vm.pdf_data.titles = [""];
      if (vm.permissions.invoice_titles) {
        vm.pdf_data.titles = vm.permissions.invoice_titles.split(",");
      }
    }
  }

function EditInvoice($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.priceband_sync = Session.roles.permissions.priceband_sync;

  vm.model_data = items;
  vm.model_data.temp_sequence_number = vm.model_data.sequence_number;

  vm.model_data.default_charge = function(){

    if (vm.model_data.order_charges.length == 1) {

      vm.model_data.flag = true;
    }
  }

  vm.delete_charge = function(id){

    if (id) {

      vm.service.apiCall("delete_order_charges?id="+id, "GET").then(function(data){

        if(data.message){

          Service.showNoty(data.data.message);
        }
      });
    }
  }

  $timeout(function() {

    $('[name="invoice_date"]').datepicker("setDate", new Date(vm.model_data.inv_date) );
  },1000);
  vm.ok = function () {

    $modalInstance.close("close");
  };

  vm.process = false;
  vm.save = function(form) {

    if (vm.permissions.increment_invoice && vm.model_data.sequence_number && form.invoice_number.$invalid) {

      Service.showNoty("Please Fill Invoice Number");
      return false;
    } else if (!form.$valid) {

      Service.showNoty("Please Fill the Mandatory Fields");
      return false;
    }
    vm.process = true;
    var data = $("form:visible").serializeArray()
    Service.apiCall("update_invoice/", "POST", data).then(function(data) {

      if(data.message) {

        if(data.data.msg == 'success') {

          Service.showNoty("Updated Successfully");
          $modalInstance.close("saved");
        } else {

          Service.showNoty(data.data.msg);
        }
      } else {

        Service.showNoty("Update fail");
      }
      vm.process = false;
    })
  }

  vm.changeUnitPrice = function(data) {

    data.base_price = data.quantity * Number(data.unit_price);
    data.discount = (data.base_price/100)*Number(data.discount_percentage);
    data.amt = data.base_price - data.discount;
    var taxes = {cgst_amt: 'cgst_tax', sgst_amt: 'sgst_tax', igst_amt: 'igst_tax', utgst_amt: 'utgst_tax'};
    data.total_tax_amount = 0;

    angular.forEach(taxes, function(tax_name, tax_amount){

      if (data.taxes[tax_name] > 0){

        data.taxes[tax_amount] = (data.amt/100)*data.taxes[tax_name];
      } else {

        data.taxes[tax_amount] = 0;
      }
       data.total_tax_amount += data.taxes[tax_amount];
    })
    data.invoice_amount = (data.amt + data.total_tax_amount);
  }
}
stockone = angular.module('urbanApp');

stockone.controller('EditInvoice', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', EditInvoice]);

stockone.directive('genericCustomerInvoiceData', function() {
  return {
    restrict: 'E',
    scope: {
      invoice_data: '=data',
    },
    templateUrl: 'views/outbound/toggle/invoice_data_html.html',
    link: function(scope, element, attributes, $http, Service){
      console.log(scope);
    }
  };
});
