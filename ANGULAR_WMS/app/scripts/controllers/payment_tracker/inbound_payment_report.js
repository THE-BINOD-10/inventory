FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('InboundPaymentReportCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.self_life_ratio = Number(vm.permissions.shelf_life_ratio) || 0;
    vm.industry_type = Session.user_profile.industry_type;
    vm.expect_date = false;
    vm.extra_width = {width: '1050px'};

    function getOS() {
      var userAgent = window.navigator.userAgent,
          platform = window.navigator.platform,
          macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
          windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
          iosPlatforms = ['iPhone', 'iPad', 'iPod'],
          os = null;

      if (macosPlatforms.indexOf(platform) !== -1) {
        os = 'Mac OS';
      } else if (iosPlatforms.indexOf(platform) !== -1) {
        os = 'iOS';
      } else if (windowsPlatforms.indexOf(platform) !== -1) {
        os = 'Windows';
      } else if (/Android/.test(userAgent)) {
        os = 'Android';
      } else if (!os && /Linux/.test(platform)) {
        os = 'Linux';
      }

      return os;
    }

    vm.date_format_convert = function(utc_date){

      var os_type = getOS();

      var date = utc_date.toLocaleDateString();
      var datearray = date.split("/");

      if (os_type == 'Windows') {

        if (datearray[1] < 10 && datearray[1].length == 1) {
          datearray[1] = '0'+datearray[1];
        }

        if (datearray[0] < 10 && datearray[0].length == 1) {
          datearray[0] = '0'+datearray[0];
        }

        vm.date = datearray[0] + '/' + datearray[1] + '/' + datearray[2];
      } else {
        
        vm.date = datearray[1] + '/' + datearray[0] + '/' + datearray[2];
      }
    }

    vm.date_format_convert(new Date());

    //process type;
    vm.po_qc = true;
    vm.po_qc = (vm.permissions.receive_process == "receipt-qc")? true: false;
    vm.g_data = Data.payment_based_invoice;

    var sort_no = 1;
    vm.filters = {'datatable': 'InboundPaymentReport', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
    				'search4': '', 'search5': '', 'search6': '', 'search7': ''/*, 'search8': ''*/};

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
       .withOption('bFilter', false)
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
       // .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('payment_id').withTitle('Payment ID'),
        DTColumnBuilder.newColumn('payment_date').withTitle('Payment Date'),
        DTColumnBuilder.newColumn('invoicee_number').withTitle('Invoice Number'),
        // DTColumnBuilder.newColumn('customer_name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('invoice_amount').withTitle('Invoice Amount'),
        DTColumnBuilder.newColumn('payment_received').withTitle('Payment Received'),
        // DTColumnBuilder.newColumn('invoice_date').withTitle('Invoice Date'),
        DTColumnBuilder.newColumn('mode_of_pay').withTitle('Mode Of Payment'),
        DTColumnBuilder.newColumn('remarks').withTitle('Remarks'),
    ];

    // var row_click_bind = 'td';
    
    // if(vm.g_data.style_view) {
    //   var toggle = DTColumnBuilder.newColumn('Update').withTitle('').notSortable()

    //              .withOption('width', '25px').renderWith(function(data, type, full, meta) {
    //                return "<span style='color: #2ECC71;text-decoration: underline;cursor: pointer;' class='invoice_data_show' ng-click='showCase.addRowData($event, "+JSON.stringify(full)+"); $event.stopPropagation()'>Update</span>";
    //              })
    // }

    // vm.dtColumns.push(toggle);
    vm.dtInstance = {};
    vm.poDataNotFound = function() {
      $(elem).removeClass();
      $(elem).addClass('fa fa-plus-square');
      Service.showNoty('Something went wrong')
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    vm.checkDateValidation = function(){

      var from_date = new Date(vm.model_data.filters.from_date);
      var to_date = new Date(vm.model_data.filters.to_date);
      if (from_date > to_date) {

        colFilters.showNoty('Pease select proper date combination');
        vm.model_data.filters.to_date = '';
      }
    }
    vm.loadjs = function () {
      vm.InboundPaymentReportCtrl_enable = true;
    }

    vm.model_data = {};

  vm.resetFilters = function(filters){

    filters.from_date = '';
    filters.to_date = '';
    filters.supplier_name = '';
    filters.invoice_number = '';
  }

    // vm.close = close;
    // function close() {
    //   vm.model_data = {};
    //   $state.go('app.PaymentTrackerInvBased');
    //   vm.reloadData();
    // }

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };
}

})();
