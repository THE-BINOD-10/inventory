'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PRReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {}
  vm.model_data = {};

  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;
  vm.toggle_detail = false;
  vm.report_data = {};
  vm.reports = {}
  vm.title = "PR Report";

  vm.row_call = function(aData) {
    if (!vm.toggle_sku_wise) {
        vm.file_url = "";
        vm.consolated_file_url = "";
        // vm.FileDownload(aData);
        vm.model_data.pr_number = aData["PR Number"]
        // print_pending_po_form/?purchase_id=21902&is_actual_pr=true&warehouse=
        $http.get(Session.url+'print_pending_po_form/?purchase_id='+aData.pending_pr_id+'&is_actual_pr='+true+'&type=pr_report', {withCredential: true})
        .success(function(data, status, headers, config) {
              $(".modal-body").html($(data).html());
              vm.print_page = $($(data).html()).clone();
              vm.print_enable = true;
          });
          $state.go('app.reports.PRReport.PRs');
    }
  }
  vm.toggle_po = function() {
    var send = {};
    var name ='';
  	if (vm.toggle_detail) {
      name = 'pr_detail_report';
    } else {
      name = 'pr_report';
    }
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
    	if (data.message) {
    	  if ($.isEmptyObject(data.data.data)) {
    		  vm.datatable = false;
    		  vm.dtInstance = {};
    	  } else {
      	  vm.reports[name] = data.data.data;
      	  angular.copy(data.data.data, vm.report_data)
          vm.report_data["row_call"] = vm.row_call;
          vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(datam) {
             vm.empty_data = datam.empty_data;
             angular.copy(vm.empty_data, vm.model_data);
//            vm.empty_data = datam.empty_data;
//            angular.copy(vm.empty_data, vm.filters_dt_data)
            vm.dtOptions = datam.dtOptions;
            vm.dtOptions.order = [2, 'desc']
            vm.dtColumns = datam.dtColumns;
            vm.datatable = true;
            vm.dtInstance = {};
    		    vm.report_data['row_click'] = true;
        		if (name =="pr_detail_report")
        		{
                vm.report_data['excel_name'] = 'get_pr_detail_report'
            }
            else{
                vm.report_data['excel_name'] = 'get_pr_report'
            }
          })
        }
    	}
    	$state.go('app.reports.PRReport');
  	})

  }

  vm.toggle_po()

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                  'from_date': '',
                  'to_date': '',
                  'po_number': '',
                  'sister_warehouse': '',
                  'supplier_id': '',
                  };
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

//  vm.filters_dt_data = {};
//  angular.copy(vm.empty_data, vm.filters_dt_data);
  //vm.download_pr_files= download_pr_files;
  //function download_pr_files(){
  //	console.log("test", vm.model_data)
  //	vm.service.apiCall("download_pr_attachments/", "GET", {pr_number: vm.model_data.pr_number}).then(function(data) {
  //	     if (data.data.status){
  //	         var a = document.createElement('a');
  //	         a.href = data.data.data
  //	         a.download = "PR_files" + vm.model_data.pr_number+ ".zip";
  //	         document.body.appendChild(a);
  //	         a.click();
  //	    }
  //	    else{
  //		vm.service.showNoty("No Attachments", 'warning');
  //		console.log("No attachements")
//	    }
	    // const blob = new Blob([data], {
    	    //	type: 'application/zip'
            // });
  	    // const url = window.URL.createObjectURL(blob);
 	    // window.open(url);
	    //onsole.log("data", data)			
//	})
  //} 

  vm.close = close;
  function close() {
    vm.title = "PR Report";
    $state.go('app.reports.PRReport');
  }

  vm.print = print;
  function print() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "PR Report");
  }

  vm.download_pr_files = function() {
    window.open('rest_api/download_pr_req_files?pr_number=' + vm.model_data.pr_number);

  }



}
