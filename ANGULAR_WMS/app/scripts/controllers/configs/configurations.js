'use strict';

angular.module('urbanApp', ['angularjs-dropdown-multiselect'])
  .controller('ConfigCtrl',['$scope', '$http', '$state', '$compile', 'Session' , 'Auth', '$timeout', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, Auth, $timeout, Service) {
  var vm = this;
  vm.service = Service;
  vm.model_data = {
                    'send_message': false, 'batch_switch': false, 'fifo_switch': false, 'show_image': false,'sku_sync': false,
                    'back_order': false, 'use_imei': false, 'pallet_switch': false, 'production_switch': false,'stock_sync': false,
                    'pos_switch': false, 'auto_po_switch': false, 'no_stock_switch': false, 'online_percentage': 0,
                    'mail_alerts': 0, 'prefix': '', 'all_groups': '', 'mail_options': [{'id': 1,'name': 'Default'}],
                    'mail_inputs':[], 'report_freq':'0', 'float_switch': false, 'automate_invoice': false, 'all_stages': '',
                    'show_mrp': false, 'decimal_limit': 1,'picklist_sort_by': false, 'auto_generate_picklist': false,
                    'detailed_invoice': false, 'picklist_options': {}, 'scan_picklist_option':''
                  };
  vm.all_mails = '';
  vm.switch_names = {1:'send_message', 2:'batch_switch', 3:'fifo_switch', 4: 'show_image', 5: 'back_order',
                     6: 'use_imei', 7: 'pallet_switch', 8: 'production_switch', 9: 'pos_switch',
                     10: 'auto_po_switch', 11: 'no_stock_switch', 12:'online_percentage', 13: 'mail_alerts',
                     14: 'invoice_prefix', 15: 'float_switch', 16: 'automate_invoice', 17: 'show_mrp', 18: 'decimal_limit',
                     19: 'picklist_sort_by', 20: 'stock_sync', 21: 'sku_sync', 22: 'auto_generate_picklist',
                     23: 'detailed_invoice', 24: 'scan_picklist_option'}
  vm.empty = {};
  vm.message = "";

  vm.switches = switches;
  function switches(value, switch_num) {
    vm.service.apiCall("switches/?"+vm.switch_names[switch_num]+"="+String(value)).then(function(data){
      if(data.message) {
        Service.showNoty(data.data);
      }
    });
    Session.roles.permissions[vm.switch_names[switch_num]] = value;
    Session.changeUserData();
  }

  vm.alertPopup = function(){
      sweetAlert("Syncing b/n Users will take some time");
  }

  vm.example1model = [{'id': 1,'name': 'Default'}];
  vm.example1data = [];
  vm.show_mail_reports = false;

  vm.toggle_reports = function() {
    if (vm.show_mail_reports) {
      vm.show_mail_reports = false;
    } else {
      vm.show_mail_reports = true;
      $timeout(function () {
        $('#my-select').multiSelect();
        $("html, body").animate({ scrollTop: $(document).height() }, 1000);
      }, 500);
    }
  }

  vm.service.apiCall("configurations/").then(function(data){
    if(data.message) {
      angular.copy(data.data, vm.model_data);
      angular.forEach(vm.model_data, function(value, key) {
        if (value == "true") {
          vm.model_data[key] = Boolean(true);
        } else if (value == "false") {
          vm.model_data[key] = Boolean(false);
        }
      });
      vm.model_data["mail_alerts"] = parseInt(vm.model_data["mail_alerts"]);
      vm.model_data["online_percentage"] = parseInt(vm.model_data["online_percentage"]);
      vm.model_data["order_header_inputs"] = Session.roles.permissions["order_headers"].split(",")
      $timeout(function () {
        $('.selectpicker').selectpicker();
        $(".mail_notifications .bootstrap-select").change(function(){
          var data = $(".mail_notifications .selectpicker").val();
          var send = "";
          if (data) {
            for(var i = 0; i < data.length; i++) {
              send += data[i].slice(1)+",";
            }
          }
          vm.service.apiCall("enable_mail_reports/?data="+send.slice(0,-1)).then(function(data){
            if(data.message) {
              Auth.update();
            }
          });
          var build_data = send.split(",");
          var temp = [];
          angular.forEach(build_data, function(item){
            if(item) {
              temp.push(vm.model_data.mail_options[item]);
            }
          })
          vm.model_data.mail_inputs = temp;
        })

        $(".create_orders .bootstrap-select").change(function(){
          var data = $(".create_orders .selectpicker").val();
          var send = "";
          if (data) {
            for(var i = 0; i < data.length; i++) {
              send += data[i].slice(1)+",";
            }
          }
          vm.service.apiCall("switches/?order_headers="+send.slice(0,-1)).then(function(data){
            if(data.message) {
              Auth.update();
            }
          });
        })
      }, 500);
      $(".sku_groups").importTags(vm.model_data.all_groups);
      $(".stages").importTags(vm.model_data.all_stages);
      $('#my-select').multiSelect();
    }
  })

  vm.mail_alerts_change = function(url, selector, item) {
    var data = $(selector).val();
    var send = "";
    for(var i = 0; i < data.length; i++) {
      send += data[i].slice(1)+",";
    }
    vm.service.apiCall(url+"/?"+ item +"="+send.slice(0,-1)).then(function(data){
      if(data.message) {
        Auth.status();
      }
    });
  }

  vm.check_selected = function(opt, name) {
    if(!vm.model_data[name]) {
      return false;
    } else {
      return (vm.model_data[name].indexOf(opt) > -1) ? true: false;
    }
  }

  vm.check_mail = function(opt) {
    return (vm.model_data.reports_data.indexOf(opt) > -1) ? true: false;
  }

  vm.update_sku_groups = function() {
    var data = $("#tags").val();
    vm.service.apiCall("save_groups?sku_groups="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.update_stages = function() {
    var data = $(".stages").val();
    vm.service.apiCall("save_stages/?stage_names="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.update_internal_mails = function() {
    var data = $(".internal_mails").val();
    vm.service.apiCall("get_internal_mails/?internal_mails="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.save_mail_config = function() {
    var report_selected = [];
     var report_removed = [];
     var data = {};

     var date_val = $($('#datepicker11')[0]).val();
     var selected = $('#configurations').find('#ms-my-select').find('.ms-elem-selection.ms-selected').find('span')
     var removed = $('#configurations').find('#ms-my-select').find('.ms-selectable').find('li').not($('.ms-selected')).find('span');
     for(i=0; i<selected.length; i++) {
       report_selected.push($(selected[i]).text());
     }
     for(i=0; i<removed.length; i++) {
       report_removed.push($(removed[i]).text());
     }
     console.log(vm.model_data.email);
     data['selected'] = report_selected;
     data['removed'] = report_removed;
     var mail_to = ""
     angular.forEach($(".mail-to .tagsinput .tag span"),function(data){
       mail_to = mail_to + $(data).text().slice(0,-2)+",";
     })
     if(mail_to) {
       mail_to = mail_to.slice(0,-1)
     }
     data['email'] = mail_to;
     data['frequency'] = $('#days_range').val();
     data['date_val'] = date_val;
     data['range'] = $('.time_data option:selected').val();
     $.ajax({url: Session.url+'update_mail_configuration/',
             method: 'POST',
             data: data,
             xhrFields: {
               withCredentials: true
             },
             'success': function(response) {
               msg = response;
               $scope.showNoty();
               Auth.status();
     }});
  }

  vm.mail_now = function() {
    var mail_to = ""
    angular.forEach($(".mail-to .tagsinput .tag span"),function(data){
      mail_to = mail_to + $(data).text().slice(0,-2)+",";
    })
    if(mail_to) {
       mail_to = mail_to.slice(0,-1)
    }
    vm.service.apiCall("send_mail_reports/?mails="+mail_to).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  var msg = "message",
      type = "success"
  var $layout = 'topRight';
  $scope.showNoty = function () {

    if (!msg) {
      msg = $scope.getMessage();
    }

    if (!type) {
      type = 'error';
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

  vm.order_manage = function (data) {
    vm.service.showLoader();
    var order_management;
    $.ajax({
	url: Session.url+'order_management_toggle?order_manage='+data,
        method: 'GET',
        xhrFields: {
          withCredentials: true
        },
        'success': function(response) {
	  if (data){
	      $('#channel_component').removeClass('ng-hide').css('display', 'block');
	      order_management = "Order Management Enabled"
	      localStorage.setItem("order_management", String(data));
	  } else {
	      $('#channel_component').addClass('ng-hide').css('display', 'none');
	      order_management = "Order Management Disabled"
	      localStorage.setItem("order_management", String(data));
	  }
	  vm.service.showNoty(order_management, 'success', 'topRight');
	  vm.service.hideLoader();
        },
	'error': function(response) {
	  console.log(response);
	  vm.service.hideLoader();
        }
    });
  };

}
