'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockTransferOrders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'StockTransferOrders'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('order', [1, 'desc'])
       .withOption('drawCallback', function(settings) {
          vm.service.make_selected(settings, vm.selected);
        })
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
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
                vm.selected[meta.row] = vm.selectAll;
                return vm.service.frontHtml + meta.row + vm.service.endHtml;
            }).notSortable(),
        DTColumnBuilder.newColumn('Warehouse Name').withTitle('Warehouse Name'),
        DTColumnBuilder.newColumn('Stock Transfer ID').withTitle('Stock Transfer ID'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
            });
        });
        return nRow;
    } 

    vm.close = close;
    function close() {
      $state.go('app.outbound.ViewOrders');
    }

    vm.model_data = {};
    vm.generate_data = [];
    vm.generate_picklist = generate_picklist;
    function generate_picklist() {
      for(var key in vm.selected){
        console.log(vm.selected[key]);
        if(vm.selected[key]) {
          vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[key]._aData);
        }
      }
      if(vm.generate_data.length > 0) {
        console.log(vm.generate_data);
        var data = {};
        for(var i=0;i<vm.generate_data.length;i++) {
          data[vm.generate_data[i]['Stock Transfer ID']+":"+vm.generate_data[i]['SKU Code']]= vm.generate_data[i].DT_RowAttr.id;
        }
        vm.service.apiCall('st_generate_picklist/', 'POST', data).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
            for(var i=0; i<vm.model_data.data.length; i++){
                    vm.model_data.data[i]['sub_data'] = [];
                    var value = (vm.permissions.use_imei)? 0: vm.model_data.data[i].picked_quantity;
                    vm.model_data.data[i]['sub_data'].push({zone: vm.model_data.data[i].zone,
                                                         location: vm.model_data.data[i].location,
                                                         picked_quantity: value});
                  }
            $state.go('app.outbound.ViewOrders.Picklist');
            reloadData();
          }
        });
        vm.generate_data = [];
      }
    }

    vm.serial_scan = function(event, scan, data, record) {
      if ( event.keyCode == 13) {
        var id = data.id;
        var total = 0;
        for(var i=0; i < data.sub_data.length; i++) {
          total = total + parseInt(data.sub_data[i].picked_quantity);
        }
        var scan_data = scan.split("\n");
        var length = scan_data.length;
        var elem = {};
        elem[id]= scan_data[length-1]
        if(total < data.reserved_quantity) {
          vm.service.apiCall('check_imei/', 'GET', elem).then(function(data){
            if(data.message) {
              if(data.data == "") {
                record.picked_quantity = parseInt(record.picked_quantity) + 1;
              } else {
                pop_msg(data.data);
                scan_data.splice(length-1,1);
                record.scan = scan_data.join('\n');
                record.scan = record.scan+"\n";
              }
            }
          });
        } else {
          scan_data.splice(length-1,1);
          record.scan = scan_data.join('\n');
          record.scan = record.scan+"\n";
          pop_msg("picked already equal to reserved quantity");
        }
      }
    }

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.print_excel = print_excel;
  function print_excel(id)  {
    vm.service.apiCall('print_picklist_excel/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        window.location = Session.host+data.data.slice(3);
      }
    })
  }

  vm.print_pdf = print_pdf;
  function print_pdf(id) {
    vm.service.apiCall('print_picklist/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        vm.service.print_data(data.data);
      }
    })
  }

  vm.update_data = update_data;
  function update_data(index, data, last) {
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
  function cal_quantity(record, data, check) {
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

    vm.picklist_confirmation = picklist_confirmation;
    function picklist_confirmation() {
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      vm.service.apiCall('picklist_confirmation/', 'POST', elem).then(function(data){
        if(data.message) {
          if(data.data == "Picklist Confirmed") {
            $state.go('app.outbound.ViewOrders');
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
      reloadData();
    }

  vm.add_stock_transfer = function() {
    $state.go("app.outbound.ViewOrders.CreateTransfer");
  }

  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      vm.service.apiCall('create_stock_transfer/', 'POST', elem).then(function(data){
        if(data.message) {
          if("Confirmed Successfully" == data.data) {
            vm.reloadData();
            vm.close();
          }
          pop_msg(data.data);
        }
      })
    } else {
      pop_msg("Fill Required Fields");
    }
  }

  }

