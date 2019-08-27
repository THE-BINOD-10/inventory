'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierWisePOsCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.tb_data = {}
    vm.total_data = {positions:[7], keys:{7: 'total_charge'}}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_supplier_details/',
              type: 'GET',
              data: vm.model_data,
              xhrFields: {
                withCredentials: true
              },
              // complete: function(jqXHR, textStatus) {
              //   $scope.$apply(function(){
              //     angular.copy(JSON.parse(jqXHR.responseText), vm.tb_data)
              //   })
              // }
           })
       .withDataProp('data')
       .withOption('order', [0, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         var html = vm.service.add_totals(settings.aoColumns.length, vm.total_data)
         $(".dataTable > thead").prepend(html)
         $compile(angular.element(".totals_row").contents())($scope);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Order Date').withTitle('Order Date'),
        DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'),
        DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('Ordered Quantity').withTitle('Ordered Quantity'),
        DTColumnBuilder.newColumn('Received Quantity').withTitle('Received Quantity'),
        DTColumnBuilder.newColumn('Amount').withTitle('Amount'),
        DTColumnBuilder.newColumn('Status').withTitle('Status'),
    ];

   vm.dtInstance = {};

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Purchase Order";

                $http.get(Session.url+'print_purchase_order_form/?po_id='+aData['order_id'], {withCredential: true})
                .success(function(data, status, headers, config) {
//                  vm.html = $(data)[0];
//                  $(html).find(".modal-dialog").removeClass('modal-lg');
//                  $(html).find(".modal-dialog").addClass('modal-lgi');
//                  $(html).find(".modal-dialog").addClass('modal-size');
//                  var html = $(vm.html).closest("form").clone();
//                  vm.print_page = $(html).clone();
//                  $(".modal-body").html($(html).find(".modal-body > .form-group"));
                  //vm.extra_width = {'width': '990px'};
                  //vm.html = $(data.data);
                  //angular.element(".modal-body").html($(data.data));
                  $(".modal-body").html($(data).html());
                  vm.print_page = $($(data).html()).clone();
                  vm.print_enable = true;
                });
                $state.go("app.reports.SupplierWisePOs.POs");
            });
        });
        return nRow;
    }

   vm.empty_data = {
                    'supplier': '',
                    'status' : '',
                    'from_date': '',
                    'to_date': '',
                    'sku_code': ''
                    };

   vm.model_data = {};

   angular.copy(vm.empty_data, vm.model_data);

   vm.suppliers = {};
   vm.service.apiCall('get_supplier_list/').then(function(data){
      if(data.message) {
        vm.suppliers = data.data.suppliers;
      }
   })

    vm.close = function() {

      angular.copy(vm.empty_data, vm.model_data);
      $state.go('app.reports.SupplierWisePOs');
    }

    vm.print = print;
    vm.print = function() {
      console.log(vm.print_page);
      vm.service.print_data(vm.print_page, "Purchase Order");
    }

  }
