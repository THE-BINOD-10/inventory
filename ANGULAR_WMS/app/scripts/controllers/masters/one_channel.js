'use strict';

var app = angular.module('urbanApp', ['datatables'])

app.controller('OneChannel',['$scope', '$http', '$state', 'Session', '$log', 'DTOptionsBuilder', 'DTColumnBuilder', '$compile', '$timeout', '$window', '$location', ServerSideProcessingCtrl ]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, $log, DTOptionsBuilder, DTColumnBuilder, $compile, $timeout, $window, $location) {

  var vm = this;
  vm.showName = showName;

  //Notify Message Code
  function showNoty(msg,type,$layout) {

    if (!type) {
      type = 'success';
    }
    if (!msg) {
      msg = 'Success';
    }
    if (!$layout) {
      $layout = 'topRight';
    }
    noty({
      theme: 'urban-noty',
      text: msg,
      type: type,
      timeout: 3000,
      layout: $layout,
      closeWith: ['button', 'click'],
      animation: {
        open: 'in',
        close: 'out',
        easing: 'swing'
      },
    });
  };

  //To Check Parameters Present in Channels page
  var queryDict = {}
  function getUrlVars() {
    var vars = {}
    var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) {
        vars[key] = value;
    });
    return vars;
  }

  queryDict = getUrlVars()

  if (queryDict != undefined && $.isEmptyObject(queryDict) != true)
  {
   if (queryDict.auth_status){
      showNoty(queryDict.market_place + " Added Successfully", "success", "topLeft")
   }
   else{
      showNoty("Error occured", "danger", "topLeft")
   }
  }
   

  //Modal Popup of Flipkart
  vm.add_flipkart_channels = function() {
    vm.title = "Add Flipkart Channel";
    vm.update = false;
    vm.model_data = {}
    var empty_data = {}
    angular.extend(vm.model_data, empty_data);
    $state.go('app.channels.update');
  }

  //Modal Popup of Amazon
  vm.add_amazon_channels = function() {
    vm.title = "Add Amazon Channel";
    vm.update = false;
    vm.model_data = {}
    var empty_data = {}
    angular.extend(vm.model_data, empty_data);
    $state.go('app.channels.add_amazon_auth');
  }

  //Close Modal Popup
  vm.close = function() {
      vm.model_data = {};
      var empty_data = {}
      angular.extend(vm.model_data, empty_data);
      $state.go('app.channels');
  }

  //Msg of Add successfully
  function pop_msg(msg) {
    vm.message = msg;
    $timeout(function () {
        vm.message = "";
    }, 2000);
    if (msg.message == 'Redirecting to flipkart')  {
      showNoty(msg.message, "success", "topRight")
      window.location = msg.auth_url
    }
  }

  //insert marketplace
  vm.add_marketplace_auth = function() {
    var json_data = $.param(vm.model_data)
    $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
    $http({ 
	    method: 'POST',
            url: Session.url+"add_market_credentials/",
            data: json_data
	  }).success(function(data, status, headers, config) {
               pop_msg(data);
               console.log("success");
          });
  }

  //func redirect
  vm.submit = submit;
  function submit(data) {
    if ( data.$valid )
    {
        vm.add_marketplace_auth();
    }
  }

  vm.permissions = Session.roles.permissions;

  //vm.dtOptions = DTOptionsBuilder.fromSource(Session.url+'get_marketplace_data/',{withCredentials: true}).withPaginationType('full_numbers');

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
       .withOption('createdRow', createdRow);
 
  /* Excel 
  vm.excel = excel;
  function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }
  End Excel */


  // Datatable Code
  vm.dtColumns = [ 
		  DTColumnBuilder.newColumn('image_url').withTitle('CHANNEL').renderWith(function(data, type, full, meta)
                        {
                        full.image_url = (full.image_url)? full.image_url : 'images/wms/dflt.jpg'
                        full.image_url = (full.image_url == '/static/img/default-image.jpg') ? 'images/wms/dflt.jpg' : full.image_url;
                        return '<img style="width: 100px;height: 40px;display: inline-block;margin-right: 10px;" src='+full.image_url+'>';
                        }),
        	  DTColumnBuilder.newColumn('name').withTitle('CHANNEL NAME'),
        	  DTColumnBuilder.newColumn('is_active').withTitle('STATUS'),
        	  DTColumnBuilder.newColumn('action').withTitle('ACTION').renderWith(function(data, type, full, meta) {

			  var status = 'ACTIVE';
                          var color = '#70cf32';
			  var button_class = 'danger';
			  var button_name = 'Deactivate';

                          if (full.status != status) {
                            var status = 'INACTIVE';
                            var color = '#d96557';
			    var button_class = 'success';
			    var button_name = 'Activate';
                          }
			  var dict = []
			  var data_ids = ""

			  data_ids = full.id

			  return '<center><a class="btn btn-'+button_class+' btn-outline" ng-click = "showCase.showName(['+data_ids+',\'' + status + '\'])" >'+button_name+'</a></center>'
		  }),
        	  DTColumnBuilder.newColumn('pull').withTitle('PULL').renderWith(function(data, type, full, meta) {

			var status_name = full.status
			if (status_name == "Inactive"){
			   return '<center><a href="javascript:;" class="btn btn-info btn-outline" disabled="true" tooltip-placement="right" tooltip="Channel Activation is Mandatory" >Pull Now</a></center>'
			}
			else
			{
			return '<center><a href="javascript:;" class="btn btn-info btn-outline" ng-click = "showCase.pull_market(\'' + full.id + '\')">Pull Now</a></center>'
			}

		  }),
        	  DTColumnBuilder.newColumn('last_pull').withTitle('LAST SYNCED')
                 ];

  /* Update Market */
  function showName(obj) {
      var obj_status = obj[1]

      var obj_bin = ""
      if (obj_status == "ACTIVE" )
      {
        obj_bin = 0
      }
      else
      { 
        obj_bin = 1
      }

      var data = {}
      data['data_id'] = obj[0]
      data['status'] = obj_bin
      var dict = $.param(data)
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http({
             method: 'POST',
             url : Session.url+"update_market_status/",
             data: dict
           }).success(function(data, status, headers, config) {
      reloadData()
      
      console.log("success");
    });
  }

  /* PULL MARKET */
  vm.pull_market = pull_market;
  function pull_market(name){

      var data = {}
      data['marketplace'] = name
      var dict = $.param(data)
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http({
             method: 'POST',
             url : Session.url+"pull_market_data/",
             data: dict
           }).success(function(data, status, headers, config) {
      reloadData()
      console.log("success");
    });
  }

  function createdRow(row, data, dataIndex) {
        // Recompiling so we can bind Angular directive to the DT
        $compile(angular.element(row).contents())($scope);
    }
}
