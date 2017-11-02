'use strict';

angular.module('urbanApp', ['angularjs-dropdown-multiselect'])
  .controller('ConfigCtrl',['$scope', '$http', '$state', '$compile', 'Session' , 'Auth', '$timeout', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, Auth, $timeout, Service) {
  var vm = this;
  vm.service = Service;

  vm.marketplace_user = (Session.user_profile.user_type == "marketplace_user")? true: false;

  vm.model_data = {
                    'send_message': false, 'batch_switch': false, 'fifo_switch': false, 'show_image': false,'sku_sync': false,
                    'back_order': false, 'use_imei': false, 'pallet_switch': false, 'production_switch': false,'stock_sync': false,
                    'pos_switch': false, 'auto_po_switch': false, 'no_stock_switch': false, 'online_percentage': 0,
                    'mail_alerts': 0, 'prefix': '', 'all_groups': '', 'mail_options': [{'id': 1,'name': 'Default'}],
                    'mail_inputs':[], 'report_freq':'0', 'float_switch': false, 'automate_invoice': false, 'all_stages': '',
                    'show_mrp': false, 'decimal_limit': 1,'picklist_sort_by': false, 'auto_generate_picklist': false,
                    'detailed_invoice': false, 'picklist_options': {}, 'scan_picklist_option':'', 'seller_margin': '',
                    'tax_details':{}, 'hsn_summary': false, 'display_customer_sku': false, 'create_seller_order': false,
                    'invoice_remarks': 'invoice_remarks', 'show_disc_invoice': false, 'increment_invoice': false,
                  };
  vm.all_mails = '';
  vm.switch_names = {1:'send_message', 2:'batch_switch', 3:'fifo_switch', 4: 'show_image', 5: 'back_order',
                     6: 'use_imei', 7: 'pallet_switch', 8: 'production_switch', 9: 'pos_switch',
                     10: 'auto_po_switch', 11: 'no_stock_switch', 12:'online_percentage', 13: 'mail_alerts',
                     14: 'invoice_prefix', 15: 'float_switch', 16: 'automate_invoice', 17: 'show_mrp', 18: 'decimal_limit',
                     19: 'picklist_sort_by', 20: 'stock_sync', 21: 'sku_sync', 22: 'auto_generate_picklist',
                     23: 'detailed_invoice', 24: 'scan_picklist_option', 25: 'stock_display_warehouse', 26: 'view_order_status',
                     27: 'seller_margin', 28: 'style_headers', 29: 'receive_process', 30: 'tally_config', 31: 'tax_details',
                     32: 'hsn_summary', 33: 'display_customer_sku', 34: 'marketplace_model', 35: 'label_generation',
                     36: 'barcode_generate_opt', 37: 'grn_scan_option', 38: 'invoice_titles', 39: 'show_imei_invoice',
                     40: 'display_remarks_mail', 41: 'create_seller_order', 42: 'invoice_remarks', 43: 'show_disc_invoice',
                     44: 'increment_invoice'}

  vm.check_box_data = [
    {
      name: "Tally Enable/Disable",
      model_name: "tally_config",
      param_no: 30,
      class_name: "fa fa-th",
      display: true
    },
    {
      name: "Auto Generate Picklist",
      model_name: "auto_generate_picklist",
      param_no: 22,
      class_name: "fa fa-envelope-o",
      display: true
    },
    {
      name: "Batch Processing Required",
      model_name: "batch_switch",
      param_no: 2,
      class_name: "fa fa-th",
      display: true
    },
    {
      name: "First In First Out Required",
      model_name: "fifo_switch",
      param_no: 3,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Display HSN Summary In Invoice",
      model_name: "hsn_summary",
      param_no: 32,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    { 
      name: "Display Discount In Invoice",
      model_name: "show_disc_invoice",
      param_no: 43,
      class_name: "glyphicon glyphicon-sort",
      display: true
    }, 
    {
      name: "Display Customer SKU In Invoice",
      model_name: "display_customer_sku",
      param_no: 33,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Detail Invoice",
      model_name: "detailed_invoice",
      param_no: 23,
      class_name: "fa fa-rupee",
      display: true
    },
    {
      name: "Show MRP In Invoice",
      model_name: "show_mrp",
      param_no: 17,
      class_name: "fa fa-rupee",
      display: true
    },
    {
      name: "Show Images in Picklist",
      model_name: "show_image",
      param_no: 4,
      class_name: "fa fa-file-image-o",
      display: true
    },
    {
      name: "Enable/Disable Cross Stock",
      model_name: "back_order",
      param_no: 5,
      class_name: "fa fa-exchange",
      display: true
    },
    {
      name: "Use Serial Numbers for SKUs",
      model_name: "use_imei",
      param_no: 6,
      class_name: "fa fa-list-ol",
      display: true
    },
    {
      name: "Pallet Enable/Disable",
      model_name: "pallet_switch",
      param_no: 7,
      class_name: "fa fa-archive",
      display: true
    },
    {
      name: "Production Enable/Disable",
      model_name: "production_switch",
      param_no: 8,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "POS Enable/Disable",
      model_name: "pos_switch",
      param_no: 9,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Auto PO Enable/Disable",
      model_name: "auto_po_switch",
      param_no: 10,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Generate Picklist for out of stock orders",
      model_name: "no_stock_switch",
      param_no: 11,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Automatic Invoice Generation",
      model_name: "automate_invoice",
      param_no: 16,
      class_name: "fa fa-envelope",
      display: true
    },
    {
      name: "Picklist Sort By Order Sequence",
      model_name: "picklist_sort_by",
      param_no: 19,
      class_name: "fa fa-envelope",
      display: true
    },
    {
      name: "Sync WMS Stock Count",
      model_name: "stock_sync",
      param_no: 20,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Sync SKU b/n Users",
      model_name: "sku_sync",
      param_no: 21,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Label Generation",
      model_name: "label_generation",
      param_no: 35,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Support Marketplace Model",
      model_name: "marketplace_model",
      param_no: 34,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Display IMEI Numbers In Invoice",
      model_name: "show_imei_invoice",
      param_no: 39,
      class_name: "fa fa-refresh",
      display: vm.marketplace_user
    },
    {
      name: "Create Seller Order",
      model_name: "create_seller_order",
      param_no: 41,
      class_name: "fa fa-server",
      display: vm.marketplace_user
    }, 
    {
      name: "Display Remarks in Mail",
      model_name: "display_remarks_mail",
      param_no: 40,
      class_name: "fa fa-envelope",
      display: true
    },
    { 
      name: "Decimal Quantity",
      model_name: "float_switch",
      param_no: 15,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Invoice number generation",
      model_name: "increment_invoice",
      param_no: 44,
      class_name: "fa fa-server",
      display: true
    },
]

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
      vm.model_data["tax_details"] = {'CST': {}};
      vm.model_data['prefix_data'] = [];
      angular.forEach(data.data.prefix_data, function(data){
        vm.model_data.prefix_data.push({marketplace_name: data.marketplace, marketplace_prefix: data.prefix});
      })
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
      if (vm.model_data.invoice_titles) {
        $(".titles").importTags(vm.model_data.invoice_titles);
      }
      $('#my-select').multiSelect();
      vm.getRemarks(vm.model_data.invoice_remarks)
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

  vm.multi_select_switch = function(selector, number) {
    var data = $(selector).val();
    if(!data) {
      data = [];
    }
    var send = data.join(",");
    vm.switches(send, number);
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

  vm.update_invoice_titles = function() {
    var data = $(".titles").val();
    vm.switches(data, 38);
    Auth.status();
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


  vm.marketplace_add_show = false;

  vm.saveMarketplace = function(name, value) {

    if(!name) {

      Service.showNoty("Please Enter Name");
      return false;
    } else if(!value) {

      Service.showNoty("Please Enter Prefix");
      return false;
    } else {
      vm.updateMarketplace(name, value, 'save')
      //vm.switches("{'tax_"+name+"':'"+value+"'}", 31);
      var found = false;
      for(var i = 0; i < vm.model_data.prefix_data.length; i++) {

        if(vm.model_data.prefix_data[i].marketplace_name == vm.model_data.marketplace_name) {

          vm.model_data.prefix_data[i].marketplace_name = vm.model_data.marketplace_name;
          vm.model_data.prefix_data[i].marketplace_prefix = vm.model_data.marketplace_prefix;
          found = true;
          break;
        }
      }
      if(!found) {

        vm.model_data.prefix_data.push({marketplace_name: vm.model_data.marketplace_name, marketplace_prefix: vm.model_data.marketplace_prefix});
      }
      vm.marketplace_add_show = false;
      vm.marketplace_selected = "";
      vm.model_data.marketplace_name = "";
      vm.model_data.marketplace_prefix = "";
      vm.model_data.marketplace_new = true;
    }
  }

  vm.model_data.marketplace_new = true;
  vm.marketplaceSelected = function(name) {

    if (name) {

      for(var i = 0; i < vm.model_data.prefix_data.length; i++) {

        if(vm.model_data.prefix_data[i].marketplace_name == name) {

          vm.model_data.marketplace_name = vm.model_data.prefix_data[i].marketplace_name;
          vm.model_data.marketplace_prefix = vm.model_data.prefix_data[i].marketplace_prefix;
          vm.model_data["marketplace_new"] = false;
          vm.marketplace_add_show = true;
          break;
        }
      }
    } else {

      vm.model_data["marketplace_new"] = true;
      vm.marketplace_add_show = false;
      vm.model_data.marketplace_name = "";
      vm.model_data.marketplace_prefix = "";
    }
  }

  vm.updateMarketplace = function(name, value, type) {

      var send = {marketplace_name : name, marketplace_prefix: value}
      if (type != 'save') {
        send['delete'] = true;

        for(var i = 0; i < vm.model_data.prefix_data.length; i++) {

          if(vm.model_data.prefix_data[i].marketplace_name == vm.model_data.marketplace_name) {

            vm.model_data.prefix_data.splice(i, 1);
            break;
          }
        }
        vm.marketplace_add_show = false;
        vm.marketplace_selected = "";
        vm.model_data.marketplace_name = "";
        vm.model_data.marketplace_prefix = "";
        vm.model_data.marketplace_new = true;
      }
      vm.service.apiCall("update_invoice_sequence/", "GET", send).then(function(data) {

        console.log(data);
      })
  }

  vm.saved_marketplaces = [];
  vm.filterMarkeplaces = function() {
    vm.saved_marketplaces = [];
    angular.forEach(vm.model_data.prefix_data, function(data){
      vm.saved_marketplaces.push(data.marketplace_name);
    })
    for(var i=0; i < vm.model_data.marketplaces.length; i++) {
      if (vm.saved_marketplaces.indexOf(vm.model_data.marketplaces[i]) == -1) {
        vm.model_data.marketplace_name = vm.model_data.marketplaces[i];
        break;
      }
    }
  }

  vm.update_invoice_remarks = function(invoice_remarks) {

    var data = $("[name='invoice_remarks']").val().split("\n").join("<<>>");
    vm.switches(data, 42);
    Auth.status();
  }

  vm.getRemarks = function(remarks) {

    $timeout(function() {
    if(remarks.split("<<>>").length > 1) {
      $("[name='invoice_remarks']").val( remarks.split("<<>>").join("\n") )
    } else {
      $("[name='invoice_remarks']").val( remarks );
    }
    }, 1000);
  }
      var keynum = "";
      vm.limitLines = function(rows, e) {
        var lines = $(e.target).val().split('\n').length;
        //if(lines > rows && e.keyCode != 8) {
        //  e.preventDefault();
        //  return false;
        //}
        if(window.event) {
          keynum = e.keyCode;
        } else if(e.which) {
          keynum = e.which;
        }

        if(keynum == 13) {
          if(lines == rows) {
            e.preventDefault();
            return false;
          }else{
            lines++;
          }
        }
      } 
}
