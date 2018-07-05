'use strict';

angular.module('urbanApp', ['datatables'], ['angularjs-dropdown-multiselect'])
// angular.module('urbanApp', ['angularjs-dropdown-multiselect'])
  .controller('OutboundPaymentCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;
    vm.marketplace_user = (Session.user_profile.user_type == "marketplace_user")? true: false;

    vm.selected = {};
    vm.checked_items = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.display = false;
    vm.extra_width = {'width': '1100px'};
    vm.title = "Payments";
    vm.model_data = {'customers': {'customer-1': 'customer-1','customer-2': 'customer-2','customer-3': 'customer-3'}};

    var send = {'tabType': 'CustomerInvoices'};
    /*vm.service.apiCall("customer_invoice_data/", "GET", send).then(function(data) {
      if(data.message) {
        vm.filters = {'datatable': 'CustomerInvoicesTab', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
    });*/

    $timeout(function () {
        $('.selectpicker').selectpicker();
        // $(".mail_notifications .bootstrap-select").change(function(){
        //   var data = $(".mail_notifications .selectpicker").val();
        //   var send = "";
        //   if (data) {
        //     for(var i = 0; i < data.length; i++) {
        //       send += data[i].slice(1)+",";
        //     }
        //   }
        //   vm.service.apiCall("enable_mail_reports/?data="+send.slice(0,-1)).then(function(data){
        //     if(data.message) {
        //       Auth.update();
        //     }
        //   });
        //   var build_data = send.split(",");
        //   var temp = [];
        //   angular.forEach(build_data, function(item){
        //     if(item) {
        //       temp.push(vm.model_data.mail_options[item]);
        //     }
        //   })
        //   vm.model_data.mail_inputs = temp;
        // })

        // $(".create_orders .bootstrap-select").change(function(){
        //   var data = $(".create_orders .selectpicker").val();
        //   var send = "";
        //   if (data) {
        //     for(var i = 0; i < data.length; i++) {
        //       send += data[i].slice(1)+",";
        //     }
        //   }
        //   vm.service.apiCall("switches/?order_headers="+send.slice(0,-1)).then(function(data){
        //     if(data.message) {
        //       Auth.update();
        //     }
        //   });
        // })
      }, 500);
      // $(".sku_groups").importTags(vm.model_data.all_groups);
      // $(".stages").importTags(vm.model_data.all_stages);
      // $(".extra_view_order_status").importTags(vm.model_data.extra_view_order_status);
      // $(".invoice_types").importTags(vm.model_data.invoice_types);
      // $(".mode_of_transport").importTags(vm.model_data.mode_of_transport||'');
      // if (vm.model_data.invoice_titles) {
      //   $(".titles").importTags(vm.model_data.invoice_titles);
      // }
      // $('#my-select').multiSelect();

    vm.multi_select_switch = function(selector) {
      var data = $(selector).val();
      if(!data) {
        data = [];
      }
      var send = data.join(",");
      vm.switches(send);
    }

    vm.switches = switches;
    function switches(value) {
      console.log(value);

      vm.model_data.sel_customers = value.split(',');
    }

    vm.check_selected = function(opt, name) {
      if(!vm.model_data[name]) {
        return false;
      } else {
        return (vm.model_data[name].indexOf(opt) > -1) ? true: false;
      }
    }

    vm.move_to = function (click_type) {
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
              //status = true;
              console.log("true");
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
        var url = 'move_to_inv/';
        var send = {seller_summary_id: ids};
        if (click_type == 'cancel_inv') {
           send['cancel'] = true;
        }
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


    vm.close = function() {

      $state.go("app.outbound.CustomerInvoices")
    }
}
