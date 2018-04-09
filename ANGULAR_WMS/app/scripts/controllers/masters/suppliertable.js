;(function(){

'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;

  vm.filters = {'datatable': 'SupplierMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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

  vm.dtColumns = [
    DTColumnBuilder.newColumn('id').withTitle('Supplier ID'),
    DTColumnBuilder.newColumn('name').withTitle('Name'),
    DTColumnBuilder.newColumn('address').withTitle('Address'),
    DTColumnBuilder.newColumn('phone_number').withTitle('Phone Number').withOption('width', '100px'),
    DTColumnBuilder.newColumn('email_id').withTitle('Email'),
    DTColumnBuilder.newColumn('Status').withTitle('Status').renderWith(function(data, type, full, meta) {
      return vm.service.status(full.status);
    }).withOption('width', '80px')
  ];

  vm.dtInstance = {};

  $scope.$on('change_filters_data', function(){
    vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
    vm.service.refresh(vm.dtInstance);
  });

  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    $('td', nRow).unbind('click');
    $('td', nRow).bind('click', function() {
      $scope.$apply(function() {
        vm.model_data = {};
        angular.extend(vm.model_data, aData);
        vm.update = true;
        vm.message = "";
        vm.title = "Update Supplier";
        vm.model_data.status = vm.status_data[vm.status_data.indexOf(aData["status"])]
        $state.go('app.masters.SupplierMaster.supplier');
      });
    });
    return nRow;
  }

  vm.filter_enable = true;

  var empty_data = {id: "", name: "", email_id: "", address: "", phone_number: "", status: "Active",
                    create_login: false, login_created: false};
  vm.status_data = ["Inactive", "Active"];
  vm.title = "Add Supplier";
  vm.update = false;
  vm.message = "";
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.SupplierMaster');
  }

  vm.add = function() {

    vm.title = "Add Supplier";
    vm.update = false;
    vm.message = "";
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.SupplierMaster.supplier');
  }

  vm.supplier = function(url) {

    //var data = $.param(vm.model_data);
	var elem = angular.element($('form'));
	elem = elem[0];
	elem = $(elem).serializeArray();
	var send = vm.uploadFile(elem);
    //var send = $("form").serializeArray();
    vm.service.apiCall(url, 'POST', send, true, true).then(function(data){

      if(data.message) {

        if (data.data == 'New Supplier Added' || data.data == 'Updated Successfully')  {

          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {

          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = function(data) {

    if (data.$valid) {

      if ("Add Supplier" == vm.title) {

        vm.supplier('insert_supplier/');
      } else {

        vm.supplier('update_supplier_values/');
      }
    } else {

      vm.service.pop_msg('Please fill required fields');
    }
  }
  //read files
    function readFile(input) {
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

	//upload file
	vm.uploadFile = function(elem) {

		var formData = new FormData();
		var el = $("#file-upload");
		var files = el[0].files;
		$.each(elem, function(i, val) {
			formData.append(val.name, val.value);
		});

		if(files.length == 0){
			return formData;
		}
		$.each(files, function(i, file) {
			formData.append('master_file', file);
		});
		return formData;
  	}

    $scope.$on("fileSelected", function (event, args) {
	  console.log(args.file.name);
	});
}

    app.directive('fileUploadd', function () { 
    return {
        scope: true,
        link: function (scope, el, attrs) {
            el.bind('change', function (event) {
                var files = event.target.files;
                var url = $(this).attr('data');
                for (var i = 0;i<files.length;i++) {
                    scope.$emit("fileSelected", { file: files[i], url: url});
                }
            });  
        }
    };   
    });

})();
