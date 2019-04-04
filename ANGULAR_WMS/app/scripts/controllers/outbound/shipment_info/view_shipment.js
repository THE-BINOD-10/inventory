'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ViewShipmentCtrl',['$scope', '$http', '$state','$timeout', '$compile', '$rootScope', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', '$modal', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout,$compile, $rootScope, Session, DTOptionsBuilder, DTColumnBuilder, Service, $modal, Data) {
    var vm = this;
    vm.service = Service
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;
    vm.host = Session.host;
    vm.upload_enable = true;
    vm.permissions = Session.roles.permissions;
    vm.awb_ship_type = (vm.permissions.create_shipment_type == true) ? true: false;
    var titleHtml = '<input type="checkbox" class="data-select" ng-model="vm.selectAll" ng-change="vm.toggleAll(vm.selectAll, vm.selected); $event.stopPropagation();">';

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'ShipmentInfo', 'ship_id':1, 'gateout':0},
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
       .withOption('RecordsTotal', function( settings ) {
         console.log("complete")
       });
    vm.dtColumns = [];
    if(vm.permissions.central_order_reassigning) {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Serial Number').withTitle('Serial Number')),
      vm.dtColumns.push(DTColumnBuilder.newColumn('Manifest Number').withTitle('Manifest Number')),
      vm.dtColumns.push(DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity'))
    } else {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Shipment Number').withTitle('Shipment Number')),
      vm.dtColumns.push(DTColumnBuilder.newColumn('Customer ID').withTitle('Customer ID')),
      vm.dtColumns.push(DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name')),
      vm.dtColumns.push(DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity'))
    }
    if(vm.permissions.dispatch_qc_check) {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Signed Invoice').withTitle('Signed Invoice Upload').notSortable())
    } else {
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Signed Invoice').withTitle('Signed Invoice Upload').notSortable())
    }
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $compile(angular.element('td', nRow))($scope);
        /*$('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {*/
        $('td:not(td:last)', nRow).unbind('click');
        $('td:not(td:last)', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                var data = { gateout : 0 ,customer_id: aData['Customer ID'], shipment_number:aData['Shipment Number']}
                Data.shipment_number = aData['Shipment Number'];
                vm.service.apiCall("shipment_info_data/","GET", data).then(function(data){
                  if(data.message) {
                    angular.copy(data.data, vm.model_data);
                    vm.model_data['sel_cartons'] = {};

                    for (var i = 0; i < vm.model_data.data.length; i++) {
                      if (vm.model_data.data[i].pack_reference && !vm.model_data.sel_cartons[vm.model_data.data[i].pack_reference]) {
                        vm.model_data.sel_cartons[vm.model_data.data[i].pack_reference] = vm.model_data.data[i].ship_quantity;
                      }
                    }
                    $state.go('app.outbound.ShipmentInfo.ConfirmShipment');
                  }
                });
            });
        });
        return nRow;
    }

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadAllData () {
      $('.custom-table').DataTable().draw();
    };

    function reloadData () {
        vm.selectAll = false;
        vm.dtInstance.reloadData();
    };

    function toggleAll (selectAll, selectedItems, event) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                selectedItems[id] = selectAll;
            }
        }
        vm.button_fun();
    }

    function toggleOne (selectedItems) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                if(!selectedItems[id]) {
                    vm.selectAll = false;
                    vm.button_fun();
                    return;
                }
            }
        }
        vm.selectAll = true;
        vm.button_fun();
    }

    vm.bt_disable = true;
    vm.button_fun = function() {

      var enable = true
      for (var id in vm.selected) {
        if(vm.selected[id]) {
          vm.bt_disable = false;
          enable = false;
          break;
        }
      }
      if (enable) {
        vm.bt_disable = true;
      }
    }

    vm.close = close;
    vm.close = function() {
      $state.go('app.outbound.ShipmentInfo');
    }

    vm.confirm_shipment = confirm_shipment;
    function confirm_shipment() {
      var data = $("input[name=shipment_number]").val();
      data = [];
      angular.forEach(vm.selected, function(key,value){
        if(key) {
          data.push({name: "ship_id", value: vm.dtInstance.DataTable.context[0].aoData[parseInt(value)]._aData['Shipment Number']})
        }
      });
      vm.service.apiCall("print_shipment/", "GET", data).then(function(data){
        if(data.message) {
          vm.service.print_data(data.data, 'Confirm Shipment');
        }
      })
    }

    vm.empty_data = {"shipment_number":"", "shipment_date":"","truck_number":"","shipment_reference":"","customer_id":"", "marketplace":"",
                     "market_list":[], "courier_name" : []};
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

    vm.under_taken_form = function(data){
      let elem = $("form:visible");
      elem = $(elem).serializeArray();
      elem.push({name:'serial_number', value:vm.model_data.data[0].serial_number})
      vm.service.apiCall("get_under_taking_form/", "POST", elem).then(function(data) {
        if(data.message) {
          if(data.data.search("<div") != -1) {
            if(!(data)) {
              data = $('.print:visible').clone();
            } else {
              data = $(data.data).clone();
            }
            var print_div= "<div class='print'></div>";
            print_div= $(print_div).html(data);
            print_div = $(print_div).clone();
            $(print_div).find(".modal-body").css('max-height', 'none');
            $(print_div).find(".modal-footer").remove();
            print_div = $(print_div).html();
            var title = "Order Shipment Print"
            var mywindow = window.open('', title, 'height=400,width=600');
            mywindow.document.write('<html><head><title>'+title+'</title>');
            mywindow.document.write('<link rel="stylesheet" type="text/css" href="vendor/bootstrap/dist/css/bootstrap.min.css" />');
            mywindow.document.write('<link rel="stylesheet" type="text/css" href="styles/custom/page.css" media="print"/>');
            mywindow.document.write('</head><body>');
            mywindow.document.write(print_div);
            mywindow.document.write('</body></html>');
            mywindow.document.close();
            mywindow.focus();
            $timeout(function(){
              mywindow.print();
              mywindow.close();
            }, 3000);
            return true;
          }
        }
      });
    }
    vm.uploaded_file_data = function(data, flag){
      vm.uploadedpdf_order_id = ''
      if(flag == 'view') {
        var send = $("form:visible");
        send = $(send).serializeArray();
        for (var i = 0; i < send.length; i++) {
          if(send[i].name == 'id'){
            vm.uploadedpdf_order_id = send[i].value
          }
        }
        vm.view_signed_copy(vm.uploadedpdf_order_id)
      }else if(flag == 'table') {
        vm.uploadedpdf_order_id = data
      }
    }
    vm.upload_file_name = "";
    $scope.$on("fileSelected", function (event, args) {
      $scope.$apply(function () {
        vm.upload_file_name = args.file.name;
        if(vm.upload_enable){
          vm.uploaded_pdf_send(vm.uploadedpdf_order_id, args.file)
        }
      });
    });

    vm.uploaded_pdf_send = function(id, pdf_file) {
      vm.upload_enable = false;
      var formData = new FormData();
      var el = $("#file-upload");
      var files = pdf_file;

      if(files.length == 0){
        return false;
      }
      formData.append('pdf_file', files);
      formData.append('id', id);
      $.ajax({url: Session.url+'upload_signed_under_taking_form/',
        data: formData,
        method: 'POST',
        processData : false,
        contentType : false,
        xhrFields: {
          withCredentials: true
        },
        'success': function(response) {
          if(response == 'Uploaded Successfully') {
            vm.dtInstance.reloadData();
            Service.showNoty(response);
            vm.upload_enable = true;
          } else {
            Service.showNoty(response, 'warning');
            vm.upload_enable = true;
          }
        },
        'error': function(response) {
          Service.showNoty('Something Went Wrong', 'warning');
          vm.upload_enable = true;
        }
      });
    }
    vm.view_signed_copy = function(id) {
      let elem = []
      let host = vm.host
      elem.push({name:'shipment_id', value:id})
      vm.service.apiCall("get_signed_oneassist_form/", "POST", elem).then(function(data) {
        if(data.message) {
          if (data.data == 'Please Upload Signed Invoice Copy'){
            Service.showNoty(data.data, 'warning');
          } else {
            let srcpdf = host+data.data.data_dict[0]
            var mywindow = window.open(srcpdf, 'height=400,width=600');
            mywindow.focus();
            $timeout(function(){
              mywindow.print();
              mywindow.close();
            }, 3000);
            return true;
          }
        }
      });
    }
    vm.submit = function(data) {
      var send = $("form:visible");
      send = $(send).serializeArray();
      vm.service.apiCall("update_shipment_status/", "GET", send).then(function(data) {
        if(data.message) {
          if(data.data["status"]) {
              vm.service.showNoty(data.data.message);
          } else {
              vm.service.showNoty(data.data.message, 'error', 'topRight');
          }
          vm.close();
          reloadData();
        }
      });
    }

    $scope.awb_marketplace_filter_data = function() {
      vm.service.apiCall("get_awb_marketplaces/?status=2").then(function(data) {
        vm.market_place = '';
        vm.courier_name = '';
        vm.model_data.market_list = [];
        vm.model_data.courier_name = [];
        if(data.data.status) {
          vm.model_data.market_list = data.data.marketplaces;
          vm.empty_data.market_list = data.data.marketplaces;
          vm.model_data.courier_name = data.data.courier_name;
          vm.empty_data.courier_name = data.data.courier_name;
          vm.market_place = '';
          vm.courier_name = '';
        }
      })
    }

    $scope.awb_marketplace_filter_data()

    vm.scanAwb = function(event, sku) {
      if (event.keyCode == 13 && sku.length > 0) {
        vm.bt_disable = true;
        vm.awb_no = sku;
        var apiUrl = "get_awb_view_shipment_info/";
        if (vm.awb_no.length) {
          var data=[];
          data.push({ name: 'awb_no', value: vm.awb_no });
          data.push({ name: 'market_place', value: vm.market_place });
          data.push({ name: 'courier_name', value: vm.courier_name });
        } else {
          vm.bt_disable = false;
          vm.service.showNoty("Fill Mandatory Fields", 'error', 'topRight');
          return;
        }
        vm.service.apiCall( apiUrl, "GET", data).then(function(data) {
          if(data.message) {
            if(data.data["status"]) {
                vm.service.showNoty(data.data.message);
                reloadAllData();
                $scope.awb_marketplace_filter_data();
              } else {
                vm.service.showNoty(data.data.message, 'error', 'topRight');
              }
            }
          vm.awb_no = '';
          vm.bt_disable = true;
        });
      }
    }
    vm.print_pdf_shipment_info = function(){
      vm.service.apiCall("print_pdf_shipment_info/", "POST", {"data":JSON.stringify(vm.model_data)}).then(function(data){
        if(data.message){
          vm.service.print_data(data.data, vm.model_data.manifest_number);
        }
      })
    }
    vm.invoice_print = function(){
      vm.service.apiCall("invoice_print_manifest/", "POST", {"shipment_id":vm.model_data.shipment_number}).then(function(data){
        if(data.message){
            $state.go("app.outbound.ShipmentInfo.InvoiceE");
            vm.pdf_data = data.data;
            $timeout(function () {
              $(".modal-body:visible").html(vm.pdf_data)
              }, 3000);

        }
      })

    }

    $rootScope.$on("CallParentMethod", function(){
      $scope.awb_marketplace_filter_data();
    });

    vm.get_courier_for_marketplace = function() {
      vm.service.apiCall("get_courier_name_for_marketplaces/?status=2&marketplace="+vm.market_place).then(function(data) {
        vm.model_data.courier_name = [];
        if(data.data.status) {
          vm.model_data.courier_name = data.data.courier_name;
          vm.empty_data.courier_name = data.data.courier_name;
          vm.courier_name = '';
        }
      })
    }


    vm.cartonPrintData = {html: vm.html};
    vm.print_pdf = function(form){
      if (vm.model_data.sel_cartons) {
        var sel_cartons = JSON.stringify(vm.model_data.sel_cartons);
        var elem = [];
        elem.push({'name':'sel_carton', 'value':vm.carton});
        elem.push({'name':'customer_id', 'value':vm.model_data.customer_id});
        elem.push({'name':'shipment_number', 'value':Data.shipment_number});

        vm.service.apiCall("print_cartons_data_view/", "GET", elem).then(function(data) {
          if(data.message) {

            if(data.data.search("<div") != -1) {
              vm.service.print_data(data.data, 'Packaging Slip');
            } else {
              vm.service.pop_msg(data.data);
            }
          }

        });
      } else {
        vm.service.showNoty("No cartons codes are entered");
      }
    }

    vm.get_carton_info = function(carton){
      vm.carton = carton;
    }

  }
