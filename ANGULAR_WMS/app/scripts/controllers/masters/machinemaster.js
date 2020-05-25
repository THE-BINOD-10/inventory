;(function(){

'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('MachineMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type
  vm.reloadData = reloadData;
  vm.filters = {'datatable': 'MachineMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
//    DTColumnBuilder.newColumn('id').withTitle('Machine ID'),
    DTColumnBuilder.newColumn('machine_code').withTitle('Machine Code'),
    DTColumnBuilder.newColumn('machine_name').withTitle('Machine Name'),
    DTColumnBuilder.newColumn('model_number').withTitle('Model Number'),
    DTColumnBuilder.newColumn('serial_number').withTitle('Serial Number').withOption('width', '100px'),
    DTColumnBuilder.newColumn('brand').withTitle('Brand'),
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
        if (vm.model_data.ep_supplier == 1) {
          vm.model_data.ep_supplier = 'yes'
        }else if (vm.model_data.ep_supplier == 0) {
          vm.model_data.ep_supplier = 'no'
        }else{
          vm.model_data.ep_supplier = ''
        }
        vm.update = true;
        vm.message = "";
        vm.title = "Update Machine";
        vm.model_data.status = vm.status_data[vm.status_data.indexOf(aData["status"])]
        for(var i in vm.model_data.uploads_list){
            vm.model_data.uploads_list[i][0] = vm.service.get_host_url(vm.model_data.uploads_list[i][0]);
        }
        $state.go('app.masters.MachineMaster.machine');
      });
    });
    return nRow;
  }

  vm.filter_enable = true;

  var empty_data = {id: "", machine_code: "", machine_name: "", model_number: "", serial_number: "", brand: "",status: "Active"};
  vm.status_data = ["Inactive", "Active"];
  vm.title = "Add Machine";
  vm.update = false;
  vm.message = "";
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);

  vm.close = function() {
      $state.go('app.masters.MachineMaster');
      vm.reloadData();
      }


  vm.add = function() {

    vm.title = "Add Machine";
    vm.update = false;
    vm.message = "";
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.MachineMaster.machine');
  }

  vm.machine = function(url) {

    //var data = $.param(vm.model_data);
	var elem = angular.element($('form'));
	elem = elem[0];
	elem = $(elem).serializeArray();
	var send = vm.uploadFile(elem);
    //var send = $("form").serializeArray();
    vm.service.apiCall(url, 'POST', send, true, true).then(function(data){

      if(data.message) {

        if (data.data == 'New Machine Added' || data.data == 'Updated Successfully')  {
          if (data.data == 'New Machine Added' && Service.is_came_from_raise_po) {
            vm.service.searched_sup_code = vm.model_data.id;
            $state.go('app.masters.MachineMaster');
          } else {
            vm.service.refresh(vm.dtInstance);
            vm.close();
          }
        } else {

          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = function(data) {
    if (data.$valid) {
      if ("Add Machine" == vm.title) {
        vm.machine('insert_machine/');
//         vm.service.refresh(vm.dtInstance);
          vm.reloadData();
          vm.close();
      } else {
        vm.machine('update_machine_values/');
        $state.go('app.masters.MachineMaster');
        vm.service.showNoty("Updated Successfully")
      }
    }
    // else {
    //   vm.service.pop_msg('Please fill required fields OR Check Percentage Value 0 - 100');
    // }
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
     function reloadData () {
        vm.dtInstance.reloadData();
    };
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
