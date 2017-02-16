'use strict';

function updateCA(obj) {
  event.stopPropagation();
  var scope = angular.element(document.getElementById("channel_table")).scope();
  scope.$apply(function () {
    scope.showCase.showName(obj);
  });
}

function pullOrders(obj, channelName) {
  event.stopPropagation();
  var scope = angular.element(document.getElementById("channel_table")).scope();
  scope.$apply(function () {
    channelName = channelName.toLowerCase();
    scope.showCase.pull_market(obj, channelName);
  });
}

var app = angular.module('urbanApp', ['datatables'])

app.controller('OneChannel',['$scope', '$http', '$state', '$timeout',  'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', ServerSideProcessingCtrl ]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, Service) {

  var vm = this;
  vm.showName = showName;
  vm.service = Service;
  vm.logo = false;

  //Marketplace Logo 
  $.ajax({
      type: "GET",
      url: Session.url+"get_marketplace_logo/",
      crossDomain:true,
      success: function(data) {
	data = JSON.parse(data)
	$scope.marketplace_logos = data.objects;
        $scope.path_name = vm.service.channels_logo_base_path();
	$scope.$apply(function () {
    	  $scope.showCase.logo = true;
  	});
      },
      error: function(data) {
        vm.service.showNoty(data.statusText, 'error', 'topRight');
      }
  })

  //Modal Popup
  vm.add_channels = function(channel_name) {
    if (channel_name == "flipkart"){
      vm.title = "Add Flipkart Channel";
      vm.update = false;
      vm.model_data = {};
      vm.formType = "add";
      var empty_data = {};
      angular.extend(vm.model_data, empty_data);
      $state.go('app.channels.add_flipkart');
    } else if (channel_name == "amazon"){
      vm.title = "Add Amazon Channel";
      vm.update = false;
      vm.model_data = {};
      vm.formType = "add";
      var empty_data = {};
      angular.extend(vm.model_data, empty_data);
      $state.go('app.channels.add_amazon');
    }
  }

  //Close Modal Popup
  vm.close = function() {
      vm.model_data = {};
      var empty_data = {}
      angular.extend(vm.model_data, empty_data);
      $state.go('app.channels');
  }

  //Msg Notify for Add and Update successfully
  function pop_msg(msg) {

    if(msg.marketplace == 'flipkart' && msg.auth_url != ""){
      vm.service.showNoty(msg.message, "success", "topRight")
      window.location = msg.auth_url
    }
    else if (msg.marketplace == 'flipkart' && msg.auth_url == ""){
      vm.service.showNoty(msg.message, "error", "topRight")
    }
    else if (msg.auth_url == ""){
      vm.service.showNoty(msg.message, "success", "topRight")
    }
    if ((msg.message).toLowerCase().indexOf("duplicate") >= 0) {
      vm.service.showNoty(msg.message, "error", "topRight")
    }
    reloadData();
    vm.close();
  }

  //Add and Update marketplace
  vm.add_marketplace_auth = function() {
    vm.service.showLoader();
    var json_data = $.param(vm.model_data)
    $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
    $http({ 
	    method: 'POST',
            url: Session.url+"add_market_credentials/",
            data: json_data
	  }).success(function(data, status, headers, config) {
            pop_msg(data);
	    vm.service.hideLoader();
          }).error(function(data) {
            vm.service.showNoty(data.statusText, 'error', 'topRight');
	    vm.service.hideLoader();
          });
  }

  //Add Update Market
  vm.submit = submit;
  function submit(data) {
    if ( data.$valid )
    {
        vm.add_marketplace_auth();
    }
  }

  vm.permissions = Session.roles.permissions;

  vm.dtInstance = {};
   vm.reloadData = reloadData;
   function reloadData () {
         vm.dtInstance.reloadData();
   };

  vm.dtOptions = DTOptionsBuilder.newOptions()
	.withOption('ajax', {
		url:  Session.url+'get_marketplace_data/',
		type: 'POST',
		data: {'datatable' : 'channels_list'},
		xhrFields: {
                	    withCredentials: true
                }
                })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', false)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

  // Datatable Code
  vm.dtColumns = [ 
		  DTColumnBuilder.newColumn('channel__image_name').withTitle('MARKETPLACE').renderWith(function(data, type, full, meta)
                        {
			var image_path = vm.service.channels_logo_base_path() + full.channel__image_name;
		        return '<center><img style="width: 100px;height: 30px;display: inline-block;margin-right: 10px;" src=' + image_path + '></center>';
                        }),
        	  DTColumnBuilder.newColumn('name').withTitle('CHANNEL NAME').renderWith(function(data, type, full, meta) {
      			return "<center><b>"+full.name+"</b></center>";
    			}),
        	  DTColumnBuilder.newColumn('is_active').withTitle('STATUS').renderWith(function(data, type, full, meta) {
			var status_name = full.is_active;
      			if (status_name == true) {
		        return '<center><span class="label label-success">ACTIVE</span></center>';
		        } else {
       			return '<center><span class="label label-danger">INACTIVE</span></center>';
      			}
    			}),
        	  DTColumnBuilder.newColumn('action').withTitle('ACTION').renderWith(function(data, type, full, meta) {
		    	var status = 'ACTIVE';
    			var color = '#70cf32';
			var button_class = 'danger';
			var button_name = 'Deactivate';
			var icon_name = 'remove';
			if (full.is_active != true) {
			  status = 'INACTIVE';
			  color = '#d96557';
			  button_class = 'success';
			  button_name = 'Activate';
			  icon_name = 'check';
			  }
			  var dict = [];
			  var data_ids = full.id;
			  return '<center><a class="btn btn-sm btn-icon btn-' + button_class + '" onClick="updateCA([' +data_ids + ',\'' + status + '\']);" ><i class="fa fa-'+icon_name+' mr10"></i><span style="font-weight: bolder;">' + button_name + '</span></a></center>';
		  }),
        	  DTColumnBuilder.newColumn('pull').withTitle('PULL').renderWith(function(data, type, full, meta) {
		    var status_name = full.is_active;
		    if (status_name == false) {
		        return '<center><a href="javascript:;" class="btn btn-sm btn-info btn-outline" disabled="true" '+'tooltip-placement="right" tooltip="Channel Activation is Mandatory" ><span>Pull Now</span></a></center>';
      		    }
		    return '<center><a href="javascript:;" class="btn btn-sm btn-primary btn-icon" onClick="pullOrders(\'' +full.id + '\'\, \'' + full.channel_name + '\')"><i class="fa fa-refresh mr10"></i><span style="font-weight: bolder;">Pull Now</span></a></center>';
		  }),
        	  DTColumnBuilder.newColumn('last_pull').withTitle('LAST SYNCED').renderWith(function(data, type, full, meta) {
      			var date_string = full.last_pull;
		        if (date_string == null || date_string == "" ) {
		        return "<center><b>"+"Not Yet Synced"+"</b></center>";
			}
		        return "<center><b>"+ new Date(date_string).toLocaleDateString(); +"</b></center>"
		    })
                 ];

  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    vm.service.showLoader();
    $('td', nRow).unbind('click');
    $('.btn-success').unbind('click');
    $('td', nRow).bind('click', function() {
      $scope.$apply(function() {
        vm.model_data = {};
        vm.model_data.name = aData.name;
        vm.model_data.username = aData.username;
        vm.model_data.password = aData.password;
        vm.model_data.id = aData.id;
        var extra_info = JSON.parse(aData.extra_info);
        if(extra_info) {
          vm.model_data.auth_token = extra_info.auth_token;
          vm.model_data.merchant_id = extra_info.merchant_id;
	  vm.model_data.secret_key = extra_info.secret_key;
        }
        vm.title = "Modify Marketplace Details";
        vm.formType = "update";
        vm.model_data.channel_name = aData.channel_name.toLowerCase();
        if (vm.model_data.channel_name == "flipkart") {
          $state.go('app.channels.update_flipkart');
        } else if (vm.model_data.channel_name == "amazon") {
          $state.go('app.channels.update_amazon');
        }
      });
    });
    vm.service.hideLoader();
    return nRow;
  }

  //Activate and Deactivate
  function showName(obj) {
    vm.service.showLoader();
    var channel_str = "Channel Activated";
    var resp_color = "success";
    var put_params = [];
    var obj_status = obj[1];
    var obj_bin = true;

    if (obj_status == "ACTIVE") {
      obj_bin = false;
      channel_str = "Channel Deactivated";
      resp_color = "error";
    }
    var data = {};
    data['data_id'] = obj[0];
    data['status'] = obj_bin;
    var button_status = $.param(data);

    $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
    $http({  method: 'POST',
             url : Session.url+"update_market_status/",
             data: button_status
           }).success(function(data, status, headers, config) {
      reloadData()
      vm.service.showNoty(channel_str, resp_color, "topRight");
      vm.service.hideLoader();
    }).error(function(data) {
      vm.service.showNoty(data.statusText, 'error', 'topRight');
      vm.service.hideLoader();
    });
  }

  /* PULL MARKET */
  vm.pull_market = pull_market;
  function pull_market(id, market){
      vm.service.showLoader();
      var data = {}

      data['account_id'] = id
      data['marketplace'] = market
      var dict = $.param(data)
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http({
             method: 'POST',
             url : Session.url+"pull_market_data/",
             data: dict
           }).success(function(data, status, headers, config) {
      reloadData();
      if (data['status'] == "Pull Now Failed"){
      	vm.service.showNoty(data['status'], "error", "topRight");
      }
      else {
	vm.service.showNoty(data['status'], "success", "topRight");
      }
      vm.service.hideLoader();
    }).error(function(data) {
      vm.service.showNoty("Error Occured", 'error', 'topRight');
      vm.service.hideLoader();
    });
  }

}
