'use strict';

var app = angular.module('urbanApp')

app.service('Service',['$rootScope', '$compile','$q', '$http', '$state', '$timeout', 'Session', 'colFilters', 'SweetAlert', 'COLORS', 'DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'DTDefaultOptions', '$window', Service]);

function Service($rootScope, $compile, $q, $http, $state, $timeout, Session, colFilters, SweetAlert, COLORS, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, DTDefaultOptions, $window) {

    var vm = this;
    vm.colFilters = colFilters
    vm.searched_wms_code = "";
    vm.searched_sup_code = '';
    vm.is_came_from_raise_po = false;
    vm.totals_tb_data = {};

    DTDefaultOptions.setLanguage({
    // ...
      sProcessing: '<div class="spinner"><div></div><div></div><div></div><div></div></div>'//'<img src="images/loader.gif" style="width:50px;">'
    });

    vm.stock_transfer = "";

    vm.dyn_data = {
                    style_detail: {
                                    head: {common:["SKU Code", "SKU Description"], sagar_fab: ["Size"]},
                                    keys: {common:["wms_code", "sku_desc"], sagar_fab: ["sku_size"]},
                                    check_stock: {'common':false, 'sagar_fab':true}
                                  }
                  }

    vm.reports = {};
    vm.search_res = [];
    vm.search_key = '';

    vm.price_format = function(a){

      var price = String(a);
      if(price.length == 2) {

        return "DN-80"+price;
      } else {
        return "DN-8"+price;
      }
    }

    vm.check_quantity = function(data, a, b) {

      var status = false;
      for(var j=0; j<data.length; j++) {
        var temp = false;
        for(var i=0; i<data[j][a].length; i++) {
          if(data[j][a][i][b]) {
            temp = true;
            break;
          }
        }
        if (temp) {
          status = true;
        }
      }
      return status;
    }

    vm.add_totals = function(length, total_data) {

      var html = "<tr class='totals_row'>"
      for(var i=0; i < length; i++) {
        if(i == 0) {
          html += "<th>Total's</th>";
        } else if (total_data.positions.indexOf(i) != -1) {
          html += "<th>{{showCase.tb_data['"+total_data.keys[i]+"']}}</th>";
        } else {
          html += "<th></th>";
        }

      }
      html += "</tr>";
      return html;
    }

    vm.pull_order_now = function() {

      vm.apiCall("pull_orders_now/").then(function(data){
        if(data.message) {

          if(data.data == "Success") {
            $state.go($state.current, {}, {reload: true});
          }
        }
      })
    }

    vm.get_view_url = function(type, dir) {

      if(type) {
        return 'views/common/' + dir + '/' + type + '.html';
      } else {
        return  '';
      }
    }

    vm.units = ["KGS", "UNITS", "METERS", "INCHES", "CMS", "REAMS", "GRAMS", "GROSS", "ML", "LITRE","FEET"];

    vm.get_report_data = function(name){
      var send = {};
      var d = $q.defer();
      if(vm.reports[name]) {
        d.resolve(vm.reports[name]);
      } else {
        vm.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data){

          if(data.message) {
            vm.reports[name] = data.data.data;
            d.resolve(vm.reports[name]);
          }
        })
      }
      return d.promise;
    }

    vm.get_report_dt = function(filters, data) {

      var d = $q.defer();
      var send = {dtOptions: '', dtColumns: '', empty_data: {}};

      angular.forEach(data.filters, function(data){

        send.empty_data[data.name] = ""
      });

      send.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url + data.dt_url + '/',
              type: 'POST',
              data: send.empty_data,
              xhrFields: {
                withCredentials: true
              },
              complete: function(jqXHR, textStatus) {
                vm.totals_tb_data = {};
                $rootScope.$apply(function(){
                  vm.tb_data = JSON.parse(jqXHR.responseText);
                  vm.totals_tb_data = vm.tb_data.totals;
                })
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

      function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
          console.log(aData);
          if(data["row_call"]) {
            data.row_call(aData);
          }
        });
        return nRow;
      }

      if(Session.user_profile.user_type == "marketplace_user") {

        if(data["mk_dt_headers"]) {

          data.dt_headers = data.mk_dt_headers;
        }
      }

      if(data.dt_unsort) {
        send.dtColumns = vm.build_colums(data.dt_headers, data.dt_unsort);
      }
      else {
        send.dtColumns = vm.build_colums(data.dt_headers);
      }

      if(data["row_call"]) {

        data["row_click"] = true;
      } else {

        data["row_click"] = false;
      }

      d.resolve(send);
      return d.promise;
    }

    vm.scan = function(event, field, url) {

      var d = $q.defer();
      if ( event.keyCode == 13 && field.length > 0) {

        if(url) {
          vm.service.apiCall(url, 'GET', {code: field}).then(function(data){
            if(data.message) {
              if (data.data) {
                d.resolve(true);
              } else {
                d.resolve(false);
              }
            }
          });
        } else {
          d.resolve(true);
        }
      } else {
        d.resolve(false);
      }
      return d.promise;
    }

    // Dictionary size
    vm.dict_length = function(dict) {

      if(Object.keys(dict).length > 0) {
        return true;
      } else {
        return false;
      }
    }

    vm.multi = function(a, b) {

      return Number(a)*Number(b);
    }

    $("body").on("keypress",".notallowspace",function (e) {
        if (e.which === 32) {
          return false;
        }
    });

    $("body").on("keypress",".number",function (e) {
    if (e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57)) {
       return false;
       }
    });

    $("body").on("keyup",".decimal",function(e){
      if(e.which == 37 || e.which == 39) {
        return true;
      } else if (e.which == 190 || this.value.indexOf(".")) {
        this.value = this.value.replace(/[^\d\.]/g, "").replace(/\./, "x").replace(/\./g, "").replace(/x/, ".");
        var data = this.value.split(".")
        if(data[1]) {
          var limit = (Session.roles.permissions["decimal_limit"])?Number(Session.roles.permissions["decimal_limit"]):1;
          console.log(limit);
          if(data[1].length > limit) {
           this.value = data[0]+"."+data[1].slice(0,limit);
          }
        }
        return true;
      } else if(e.which < 48 || e.which > 57) {
        return true
      } else {
        return false
      }
    });

    //common variables
    vm.titleHtml = '<input type="checkbox" class="data-select" ng-model="showCase.selectAll" ng-change="showCase.bt_disable = showCase.service.toggleAll(showCase.selectAll, showCase.selected, showCase.bt_disable); $event.stopPropagation();">';
    vm.frontHtml = '<input class="data-select" type="checkbox" ng-model="showCase.selected[';
    vm.endHtml = ']" ng-change="showCase.bt_disable = showCase.service.toggleOne(showCase.selectAll, showCase.selected, showCase.bt_disable);$event.stopPropagation();showCase.selectAll = showCase.servce.select_all(showCase.selectAll, showCase.selected)">';

    vm.status = function(data) {

      var status = 'Active';
      var color = '#70cf32';
      if (data != status) {
        status = 'Inactive';
        color = '#d96557';
      }
      return '<span style="padding: 1px 6px 3px;border-radius: 10px;background: #f4f4f5;">'+'<i class="fa fa-circle" style="color:'+color+';display: inline-block;"></i>'+'<p style="display: inline-block;margin: 0px;padding-left: 5px;">'+status+'</p>'+'</span>'
    }

    vm.isLast = function(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

    vm.get_decimal_perm = function() {

      return (Boolean(Session.roles.permissions["float_switch"])) ? "decimal" : "number";
    }

    vm.decimal = function(a, b) {

      var value = Number(a)*Number(b);
      value = String(value);
      if(value.indexOf("e") != -1) {
        return "0";
      }
      value = value.replace(/[^0-9\.]/g, '')
      var findsDot = new RegExp(/\./g)
      var containsDot = value.match(findsDot)
      if(containsDot != null) {
        var data = value.split(".")
        var limit = (Session.roles.permissions["decimal_limit"])?Number(Session.roles.permissions["decimal_limit"]):1;
        if(data[1].length >= limit) {
          value = data[0]+"."+data[1].slice(0,limit);
          value = Number(value)
        }
      }
      return value;
    }

    vm.message = "";
    vm.pop_msg =  function(msg) {
      vm.message = msg;
      $timeout(function () {
        vm.message = "";
      }, 3000);

      $(".insert-status > h4").text(msg);
      $timeout(function () {
        $(".insert-status > h4").text("");
      }, 3000);
    }

    vm.refresh = function(instance) {

        instance.reloadData();
    };

    vm.check_image_url = function(url)  {
      if(!(url)) {
        if(Session.user_profile.company_name == "Sagar Fab International") {
          return "images/wms/sagar_default.jpg";
        } else {
          return "images/wms/dflt.jpg";
        }
      } else if((url.indexOf("static")) > -1 && (url != "/static/img/default-image.jpg")) {
        return Session.host+url.slice(1);
      } else if(url == "/static/img/default-image.jpg") {
        if(Session.user_profile.company_name == "Sagar Fab International") {
          return "images/wms/sagar_default.jpg";
        } else {
          return "images/wms/dflt.jpg";
        }
      } else {
        return url;
      }
    }
	vm.get_host_url = function(url) {
		return Session.host + url;
	}

    vm.print_enable = false;
    vm.print_report = function(data, url, stat){

      var d = $q.defer();
      vm.print_enable = true;
      if(stat) {
        var data1 = ""
        angular.forEach(data,function(v,n){
          data1 = data1 + n + "=" + v + "&";
        })
        data = data1.slice(0,-1);
      } else {
        data = $.param(data)
      }
      $http.get(Session.url+url+data, {withCredential: true}).success(function(data){
        colFilters.print_data(data);
        vm.print_enable = false;
        d.resolve('resolved');
      })
      return d.promise;
    }

    vm.print_excel = function(data, instance, headers, name, stat, url) {

      var send = {};
      var excel_url = "excel_reports/";
      excel_url = (url)? url: excel_url;
      var d = $q.defer();
      vm.print_enable = true;
      data['excel_name'] = name;
      send['serialize_data'] = ""
      var index = 0
      angular.forEach(headers, function(value, key) {
        if(value.mData) {
          send['columns['+index+'][data]'] = value.sTitle;
          index++;
        }
      })
      if(stat) {
        var data1 = ""
        angular.forEach(data,function(v,n){
          data1 = data1 + n + "=" + v + "<>";
        })
        send = $.param(send)+"&"+"serialize_data="+data1.slice(0,-2);
      } else {
        send['serialize_data'] = $.param(data).replace(/[+]/g, ' ');
        send = $.param(send)
      }
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http.post(Session.url+excel_url, send, {withCredential: true}).success(function(data){
        window.location = Session.host+data.slice(3);
        vm.print_enable = false;
        d.resolve('resolved');
      })
      return d.promise;
    }

    vm.generate_report = function(instance, data)  {

      var temp = {};
      angular.copy(data, temp);
      instance.DataTable.context[0].ajax.data = temp;
      instance.DataTable.draw();
    }

    vm.reset_data = function(from, to) {

      angular.copy(from, to);
    }

    /*** Excel Download ***/

    vm.excel_downloading = {};

    vm.download_excel = function download_excel(headers, search) {

      vm.print_enable = true;
      var data = {};
      data['excel'] = true;
      angular.forEach(headers, function(value, key) {
        if(value.mData) {
          data[value.mData] = value.sTitle;
        }
      })
      angular.extend(data, search);
      data['search[value]'] = $(".dataTables_filter").find("input").val();
      data = $.param(data);
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      vm.showNoty("Download Excel started");
      vm.excel_downloading[search['datatable']] = true;
      $http({
        method: 'POST',
        url: Session.url+"results_data/",
        data: data})
        .then(function(data) {
          window.location = Session.url+data.data;
          vm.print_enable = false;
          vm.showNoty("Downloaded Excel Successfully")
          vm.excel_downloading[search['datatable']] = false;
        }, function(response) {
          vm.print_enable = false;
          vm.showNoty("Downloading Fail");
          vm.excel_downloading[search['datatable']] = false;
        }
      );
    }

    vm.show_tab = function(data) {
      if(Boolean(Session.roles.permissions.is_staff) && Boolean(Session.roles.permissions.is_superuser)) {
        return true;
      } else if (!(Session.roles.permissions[data])) {
        return false;
      } else {
        return true;
      }
    }

    vm.showNoty = function (msg,type,$layout) {

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

    vm.showNotyNotHide = function (msg,type,$layout) {
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
        layout: $layout,
        closeWith: ['button', 'click'],
        animation: {
          open: 'in',
          close: 'out',
          easing: 'swing'
        },
      });
    };

    /* State Refresh */
    vm.state_refresh = function() {
      $state.go($state.current, {}, {reload: true});
    }

    /* Switches */
    vm.switches = function(value, name) {
      vm.apiCall("switches/?"+name+"="+String(value)).then(function(data){
        if(data.message) {
          vm.showNoty(data.data);
        }
      });
      Session.roles.permissions[name] = value;
      Session.changeUserData();
      $state.go($state.current, {}, {reload: true});
    }

    /* negative number stop */
    $.validator.addMethod('number',
      function (value) {
        return Number(value) >= 0;
      }, 'Enter a positive number.');

    vm.alert_msg = function (title) {
      var d = $q.defer();
      $timeout(function() {
      SweetAlert.swal({
        title: title,
        text: 'Do you Want to Continue',
        type: 'warning',
        showCancelButton: true,
        confirmButtonColor: COLORS.danger,
        confirmButtonText: 'continue',
        closeOnConfirm: true,
      },
      function (status) {
        //swal('Added!', 'Return Tracking ID added to index!', 'success');
        if (status) {
          d.resolve("true");
        } else {
          d.resolve("false");
        }
      });
      }, 500);
      return d.promise;
    };

    vm.alert_info = function(title, info) {

      SweetAlert.swal(title, info);
    }

    //search input
    vm.getSearchValues = function(val,url,extra) {
      vm.search_key = val;
      var type = "";
      if (extra) {
        type = extra;
      }
      return $http.get(Session.url+url, {
        params: {
          q: val,
          type: type
        }
      }).then(function(response){
        vm.search_res = [];
        var results = response.data;
        if (results.length > 7) {
          results = results.slice(0,7);
        }
        vm.popup_dyn_style = {height: (175 + (25 * results.length))}; // It is for scaning sku alert popup height
        return results.map(function(item){
          vm.search_res.push(item);
          return item;
        });
      });
    };

    vm.checkSearchValue = function(val,url, event, extra, msg) {
      var type = "";
      if (val.search(":") > -1) {

        val = val.split(":")[0];
      }
      if (extra) {
        type = extra;
      }
      var data = val
      return $http.get(Session.url+url, {
        params: {
          q: val,
          type: type
        }
      }).then(function(response){
        var results = response.data;
        if ($(event.target).val() == val) {
          if (results.length > 0) {
            if (results[0] == data) {
              $(event.target).val(val);
            } else if(results[0].search(val) > -1) {
              $(event.target).val(val);
            } else {
              $(event.target).val("");
              $(event.target).focus();
              vm.pop_msg("Enter Correct value "+msg);
            }
          } else {
            $(event.target).val("");
            $(event.target).focus();
            vm.pop_msg("Enter Correct "+msg);
          }
        }
      });
    };

    vm.checkSearchValue2 = function(record,url, event, extra, msg) {
      var val = record.sku_code;
      var type = "";
      if (!(val)) {
        return;
      }
      if (val.search(":") > -1) {

        val = val.split(":")[0];
      }
      if (extra) {
        type = extra;
      }
      var data = val
      return $http.get(Session.url+url, {
        params: {
          q: val,
          type: type
        }
      }).then(function(response){
        var results = response.data;
        if ($(event.target).val() == val) {
          if (results.length > 0) {
            if (results[0] == data) {
              $(event.target).val(val);
            } else if(results[0].search(val) > -1) {
              $(event.target).val(val);
            } else {
              record.sku_code = "";
              $(event.target).focus();
              vm.pop_msg("Enter Correct value "+msg);
            }
          } else {
            record.sku_code = "";
            $(event.target).focus();
            vm.pop_msg("Enter Correct "+msg);
          }
        }
      });
    };

    vm.change_search_value = function(data) {
      if(data.indexOf(":")> -1) {
        return data.split(":")[0];
      } else {
        return data;
      }
    }

    //Checkbox Toggle;
    vm.toggleAll = function(selectAll, selectedItems, bt_disable, event) {
      for (var id in selectedItems) {
        if (selectedItems.hasOwnProperty(id)) {
          selectedItems[id] = selectAll;
        }
      }
      var enable = true
      for (var id in selectedItems) {
        if(selectedItems[id]) {
          bt_disable = false;
          enable = false;
          break;
        }
      }
      if (enable) {
        bt_disable = true;
        return true;
      } else {
        return false;
      }
    }

    vm.toggleOne = function(selectAll, selectedItems, bt_disable) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                if(!selectedItems[id]) {
                    selectAll = false;
                    break;
                }
            }
        }
        //selectAll = true;
        var enable = true
        for (var id in selectedItems) {
          if(selectedItems[id]) {
            bt_disable = false;
            enable = false;
            break;
          }
        }
        if (enable) {
          bt_disable = true;
          return true;
        } else {
          return false;
        }
    }

    vm.select_all = function(selectAll, selectedItems) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                if(!selectedItems[id]) {
                    selectAll = false;
                    break;
                }
            }
        }
        return selectAll;
    }

    vm.make_selected = function(settings, selected) {

      angular.forEach($("#"+settings.sInstance).find("tbody > tr"), function(tr, index) {
        if(selected[index]) {
          $(tr).find("td:first > input").attr("checked", true);
        }
      })
    }

    vm.datatable = {
                     titleHtml: vm.titleHtml,
                     frontHtml: vm.frontHtml,
                     endHtml: vm.endHtml,
                     toggleAll: vm.toggleAll,
                     toggleOne: vm.toggleOne,
                     select_all: vm.select_all,
                   }

    //Api Calls

    //Api Calls

    vm.change_process = function(status, make) {

      if (status) {
        $rootScope.process = make;
      }
    }
    vm.apiCall = function(url, method, data, disable, with_file) {

      var d = $q.defer();
      var response = {message: 0, data:{}}
      if (url) {
        method = (method == "POST") ? method : "GET";
        data = (data) ? data: {};
        var send =  "";
        $(".preloader").removeClass("ng-hide").addClass("ng-show");
        vm.change_process(disable, true);
        if (with_file) {
			send = data;
			if (method == "POST") {
				$.ajax({url: Session.url+url,
						data: send,
						method: 'POST',
						processData : false,
						contentType : false,
						xhrFields: {
							withCredentials: true
						},
						'success': function(data) {
							  response.data = data;
							  response.message = 1;
							  $(".preloader").removeClass("ng-show").addClass("ng-hide");
							  vm.change_process(disable, false);
							  d.resolve(response);
							},
						'error': function(data){
							  response.message = 0;
							  $(".preloader").removeClass("ng-show").addClass("ng-hide");
							  vm.change_process(disable, false);
							  d.resolve(response);
						}
				});
			}
        }
        else {
			send = $.param(data);
			$http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
            if (method == "POST") {
              $http({
                method: method,
                url:Session.url+url,
                withCredential: true,
                data: send}).success(function(data, status, headers, config) {
                  response.data = data;
                  response.message = 1;
                  $(".preloader").removeClass("ng-show").addClass("ng-hide");
                  vm.change_process(disable, false);
                  d.resolve(response);
                }).error(function(){
                  response.message = 0;
                  $(".preloader").removeClass("ng-show").addClass("ng-hide");
                  vm.change_process(disable, false);
                  d.resolve(response);
                });
            } else {
              var temp_url = (send)? Session.url+url+"?"+send: Session.url+url;
              $http({
                method: method,
                url:temp_url,
                withCredential: true,
                }).success(function(data, status, headers, config) {
                  response.data = data;
                  response.message = 1;
                  $(".preloader").removeClass("ng-show").addClass("ng-hide");
                  vm.change_process(disable, false);
                  d.resolve(response);
                }).error(function(){
                  response.message = 0;
                  $(".preloader").removeClass("ng-show").addClass("ng-hide");
                  vm.change_process(disable, false);
                  d.resolve(response);
                });
            }
      }
      } else {

        d.resolve(response);
      }
      return d.promise;
    }

  vm.get_style = function(type) {

    if(Session.userName = "adam_clothing") {

      if( type == "font") {
        return {"font-size": "10px"}
      } else if(type == "td") {
        return {"font-size": "10px", "border-top": "1px solid #fff", "border-bottom": "1px solid #fff", "padding": "5px 10px"}
      } else if(type == "tr") {
        return {"border-top": "1px solid rgba(128, 128, 128, 0.14)"}
      }
    }
  }

  //printing
  vm.print_data = function(data, title) {
    if(!(data)) {
      data = $('.print:visible').clone();
    } else {
      data = $(data).clone();
    }
    var print_div= "<div class='print'></div>";
    print_div= $(print_div).html(data);
    print_div = $(print_div).clone();

    $(print_div).find(".modal-body").css('max-height', 'none');
    $(print_div).find(".modal-footer").remove();
    print_div = $(print_div).html();

    var mywindow = window.open('', title, 'height=400,width=600');
    mywindow.document.write('<html><head><title>'+title+'</title>');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="vendor/bootstrap/dist/css/bootstrap.min.css" />');
    //mywindow.document.write('<link rel="stylesheet" type="text/css" href="styles/custom/urban.css" />');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="styles/custom/page.css" media="print"/>');
    //mywindow.document.write('<script type="text/javascript" src="vendor/jquery/dist/jquery.min.js"></script>');
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

  vm.print_invoice = function(data, title) {
    if(!(data)) {
      data = $('.print:visible').clone();
    } else {
      data = $(data).clone();
    }
    var print_div= "<div class='print'></div>";
    print_div= $(print_div).html(data);
    print_div = $(print_div).clone();

    $(print_div).find(".modal-body").css('max-height', 'none');
    $(print_div).find(".modal-footer").remove();
    print_div = $(print_div).html();

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

  vm.generate_pdf_file2 = function(data){
    var send = {};
    send = $(".modal-body:visible").html()
   vm.print_invoice_data(send, "");
 }
  vm.print_invoice_data = function(data, title) {
   if(!(data)) {
     data = $('.print:visible').clone();
   } else {
     data = $(data).clone();
   }
   var print_div= "<div class='print'></div>";
   print_div= $(print_div).html(data);
   print_div = $(print_div).clone();
    $(print_div).find(".modal-body").css('max-height', 'none');
   $(print_div).find(".modal-footer").remove();
   print_div = $(print_div).html();
    var mywindow = window.open(Session.url + '/dispatch_invoice.pdf', '_blank', title, 'height=400,width=600');
   mywindow.document.write('<html><head><title>'+title+'</title>');
   mywindow.document.write('<link rel="stylesheet" type="text/css" href="vendor/bootstrap/dist/css/bootstrap.min.css" />');
   mywindow.document.write('<link rel="stylesheet" type="text/css" href="styles/custom/page.css" media="print"/>');
   mywindow.document.write('<link rel="stylesheet" type="text/css" href="styles/custom/page1.css" media="print"/>');
   mywindow.document.write('</head><body>');
   mywindow.document.write(print_div);
   mywindow.document.write('</body></html>');
    mywindow.document.close();
   mywindow.focus();
    $timeout(function(){
     mywindow.print();
     mywindow.close();
   }, 20);
    return true;
  }

  vm.generate_pdf_file = function(data){
      var send = {};
      //send['data'] = JSON.stringify(data);
      send['data'] = $(".print-invoice:visible").html()
      send['css'] = 'page';
      vm.apiCall("generate_pdf_file/", "POST", send).then(function(data){
         if(data.message) {
           window.open(Session.url + data.data, '_blank');
         }
      })
  }

  vm.build_colums = function(data, not_sort)  {

    if (!not_sort) {
      not_sort = [];
    }
    var columns = [];
    angular.forEach(data, function(item) {

      if(not_sort.indexOf(item) > -1) {
        columns.push(DTColumnBuilder.newColumn(item).withTitle(item).notSortable());
      } else {
        columns.push(DTColumnBuilder.newColumn(item).withTitle(item));
      }
    })
    return columns;
  }

  vm.build_colums2 = function(data, not_sort)  {

    if (!not_sort) {
      not_sort = [];
    }
    var columns = [];
    angular.forEach(data, function(key, value) {

      if(not_sort.indexOf(value) > -1) {
        columns.push(DTColumnBuilder.newColumn(value).withTitle(key).notSortable());
      } else {
        columns.push(DTColumnBuilder.newColumn(value).withTitle(key));
      }
    })
    return columns;
  }

  vm.channels_logo_base_path = function(data) {
    return "images/marketplaces/";
  }

  vm.showLoader = function(){
    $("#overlay").removeClass("ng-hide").addClass("ng-show");
  };

  vm.hideLoader = function(){
    $("#overlay").removeClass("ng-show").addClass("ng-hide");
  };

  vm.generate_barcodes = function(data) {

    if (data.$valid) {

      var elem = angular.element($('form:visible'));

      elem = elem[0];

      elem = $(elem).serializeArray();

      elem.push({name: 'format', value: 'sku_master'})

      vm.apiCall('generate_barcodes/', 'POST', elem, true).then(function(data){

        if(data.message && data.data !== '"Failed"') {

            var href_url = Session.host.concat(data.data.slice(1, -1));
            console.log(href_url);
            var downloadpdf = $('<a id="downloadpdf" target="_blank" href='+href_url+' >');

            $('body').append(downloadpdf);

            document.getElementById("downloadpdf").click();

            $("#downloadpdf").remove();
        }else{
           vm.showNoty("Failed", 'warning');
        }
      });
    }
  }


}

  app.directive('scrolly', function () {
    return {
        restrict: 'A',
        link: function (scope, element, attrs) {
            var raw = element[0];
            console.log('loading directive');
            element.bind('scroll', function () {
                console.log(raw.scrollTop + raw.offsetHeight);
                console.log(raw.scrollHeight);
                if (raw.scrollTop + raw.offsetHeight+10 > raw.scrollHeight) {
                    scope.$apply(attrs.scrolly);
                }
            });
        }
    };
  });

  //http interceptor
    app.factory('loaderManage', [function() {
    var timestampMarker = {
        request: function(config) {
            $(".preloader").removeClass("ng-hide").addClass("ng-show");
            return config;
        },
        response: function(response) {
            var data = {status: 1, data: response.data};
            response.data = data;
            $(".preloader").removeClass("ng-show").addClass("ng-hide");
            return response;
        },
        requestError: function(response) {
            var data = {status: 0, data: response.data};
            response.data = data;
            console.log("backend fail");
            $(".preloader").removeClass("ng-show").addClass("ng-hide");
            return response;
        },
        responseError: function(response) {
            var data = {status: 0, data: response.data};
            response.data = data;
            console.log("backend fail");
            $(".preloader").removeClass("ng-show").addClass("ng-hide");
            return response;
        }
      };
      return timestampMarker;
    }]);
   // app.config(['$httpProvider', function($httpProvider) {
   //   $httpProvider.interceptors.push('loaderManage');
   // }]);

    //percentage
    app.directive('percentageNumber', function() {
    return function(scope, element, attrs) {
        var value = element.val();
        element.on('keydown', function(e) {
            if (element.val() == "") {
               element.val(element.val());
            } else if(parseInt(element.val()) < 0) {
               value = element.val("0");
            } else if(parseInt(element.val()) > 100) {
               value = element.val("100");
            }
        });
    }
    });

    //Postibe Number Service
    app.directive('positiveNumber', function() {
    return function(scope, element, attrs) {
        var value = element.val();
        element.on('keyup, change', function(e) {
            if (element.val() == "") {
               element.val(element.val());
            } else if(parseInt(element.val()) < 0) {
                value = element.val("0");
            }
        });
    }
    });

    // greater than zero number
    app.directive('integerNumber', function() {
    return function(scope, element, attrs) {
        var value = element.val();
        element.on('keyup, change', function(e) {
            if (element.val() == "") {
               element.val(element.val());
            } else if(parseInt(element.val()) <= 0) {
                value = element.val(1);
            }
        });
    }
    });

    app.directive('wholeNumber', function () {
      return {
        require: 'ngModel',
        link: function (scope, element, attr, ngModelCtrl) {
            function fromUser(text) {
                if (text) {
                    var transformedInput = text.replace(/[^0-9]/g, '');

                    if (transformedInput !== text) {
                        ngModelCtrl.$setViewValue(transformedInput);
                        ngModelCtrl.$render();
                    }
                    return transformedInput;
                }
                return undefined;
            }
            ngModelCtrl.$parsers.push(fromUser);
        }
      };
    });

    app.directive('naturalNumber', function () {
      return {
        require: 'ngModel',
        link: function (scope, element, attr, ngModelCtrl) {
            var element = element;
            function fromUser(text) {
                if (text) {
                    var transformedInput = "";
                    if (parseInt(text) != 0) {
                      transformedInput = text.replace(/[^0-9]/g, '');
                    }

                    if (transformedInput !== text) {
                        ngModelCtrl.$setViewValue(transformedInput);
                        ngModelCtrl.$render();
                    }
                    return transformedInput;
                }
                return undefined;
            }
            ngModelCtrl.$parsers.push(fromUser);
        }
      };
    });

    app.directive('quantityNumber', function () {
      return {
        require: 'ngModel',
        link: function (scope, element, attr, ngModelCtrl) {
            function fromUser(text, element) {
                if (text) {
                    var transformedInput = "";
                    transformedInput = text.replace(/[^0-9\.]/g, '');

                    if (transformedInput !== text) {
                        ngModelCtrl.$setViewValue(transformedInput);
                        ngModelCtrl.$render();
                    }
                    return transformedInput;
                }
                return undefined;
            }
            ngModelCtrl.$parsers.push(fromUser);
        }
      };
    });

    app.directive('decimalNumber', function () {
      return {
        restrict: 'A',
        link: function (scope, elm, attrs, ctrl) {
            elm.on('keydown', function (event) {
                var $input = $(this);
                var value = $input.val();
                value = value.replace(/[^0-9\.]/g, '')
                var findsDot = new RegExp(/\./g)
                var containsDot = value.match(findsDot)
                if (containsDot != null && ([46, 110, 190].indexOf(event.which) > -1)) {
                    event.preventDefault();
                    return false;
                }
                if(containsDot != null) {
                  var data = value.split(".")
                  if(data[1].length == 3 && (!([8,39,37].indexOf(event.which) > -1))) {
                    event.preventDefault();
                    return false;
                  }
                }
                $input.val(value);
                if (event.which == 64 || event.which == 16) {
                    // numbers
                    return false;
                } if ([8, 13, 27, 37, 38, 39, 40, 110].indexOf(event.which) > -1) {
                    // backspace, enter, escape, arrows
                    return true;
                } else if (event.which >= 48 && event.which <= 57) {
                    // numbers
                    return true;
                } else if (event.which >= 96 && event.which <= 105) {
                    // numpad number
                    return true;
                } else if ([46, 110, 190].indexOf(event.which) > -1) {
                    // dot and numpad dot
                    return true;
                } else if(event.keyCode == 9) {
                    // press tab
                    return true;
                } else {
                    event.preventDefault();
                    return false;
                }
            });
        }
      }
    });

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

    app.directive('imageUpload', function () {
    return {
        scope: true,
        link: function (scope, el, attrs) {
            el.bind('change', function (event) {
                var fname = $(this).val();
                var re = /(\.jpg|\.jpeg|\.bmp|\.gif|\.png)$/i;
                if(!re.exec(fname)) {
                  alert("File extension not supported!");
                  $(this).val('');
                } else {
                  var files = event.target.files;
                  var url = $(this).attr('data');
                  for (var i = 0;i<files.length;i++) {
                      scope.$emit("fileSelected", { file: files[i], url: url});
                  }
                }
            });
        }
    };
    });

    app.directive('multiImageUpload', function () {
    return {
        scope: true,
        link: function (scope, el, attrs) {
            el.bind('change', function (event) {
                var fname = $(this).val();
                var re = /(\.jpg|\.jpeg|\.bmp|\.gif|\.png)$/i;
                if(!re.exec(fname)) {
                  scope.$emit("fileSelected", { file: [], msg:"File extension not supported!"});
                  $(this).val('');
                } else {
                  var files = event.target.files;
                  scope.$emit("fileSelected", { file: files, msg: "success"});
                }
            });
        }
    };
    });

app.directive('percentageField', [ '$filter', function( $filter ) {
    return {
        restrict: 'A',
        require: 'ngModel',
        scope: {
            // currencyIncludeDecimals: '&',
        },
        link: function(scope, element, attr, ngModel) {
            attr[ 'percentageMaxValue' ] = attr[ 'percentageMaxValue' ] || 100;
            attr[ 'percentageMaxDecimals' ] = attr[ 'percentageMaxDecimals' ] || 2;
            $( element ).css( {'text-align': 'left'} );
            // function called when parsing the inputted url
            // this validation may not be rfc compliant, but is more
            // designed to catch common url input issues.
            function into(input) {
                var valid;
                if( input == '' || !(input))
                {
                    ngModel.$setValidity( 'valid', true );
                    return '';
                }
                // if the user enters something that's not even remotely a number, reject it
                if( ! input.match( /^\d+(\.\d+){0,1}%{0,1}$/gi ) )
                {
                    ngModel.$setValidity( 'valid', false );
                    return '';
                }
                // strip everything but numbers from the input
                input = input.replace( /[^0-9\.]/gi, '' );
                input = parseFloat( input );
                var power = Math.pow( 10, attr[ 'percentageMaxDecimals' ] );
                input = Math.round( input * power ) / power;
                if( input > attr[ 'percentageMaxValue' ] ) input = attr[ 'percentageMaxValue' ];
                // valid!
                ngModel.$setValidity( 'valid', true );
                return input;
            }
            ngModel.$parsers.push(into);
            function out( input )
            {
                if( ngModel.$valid && input !== undefined && input > '' )
                {
                    return input;
                }
                return '';
            }
            ngModel.$formatters.push( out );
            $( element ).bind( 'click', function(){
                //$( element ).val( ngModel.$modelValue );
                $( element ).select();
            });
            $( element ).bind( 'blur', function(){
                $( element ).val( out( ngModel.$modelValue ) );
            });
        }
    };
}]);

//focus me
app.directive('focusOn', function() {
   return function(scope, elem, attr) {
      scope.$on('focusOn', function(e, name) {
        if(name === attr.focusOn) {
          elem[0].focus();
        }
      });
   };
});

app.factory('focus', function ($rootScope, $timeout) {
  return function(name) {
    $timeout(function (){
      $rootScope.$broadcast('focusOn', name);
    });
  }
});

// auto focus

app.directive('autoFocus', function($timeout) {
    return {
        restrict: 'AC',
        link: function(_scope, _element) {
            $timeout(function(){
                _element[0].focus();
            }, 0);
        }
    };
});

app.directive('ngDebounce', function($timeout) {
    return {
        restrict: 'A',
        require: 'ngModel',
        priority: 99,
        link: function(scope, elm, attr, ngModelCtrl) {
            if (attr.type === 'radio' || attr.type === 'checkbox') return;

            elm.unbind('input');

            var debounce;
            elm.bind('input', function() {
                $timeout.cancel(debounce);
                debounce = $timeout( function() {
                    scope.$apply(function() {
                        ngModelCtrl.$setViewValue(elm.val());
                    });
                }, attr.ngDebounce || 1000);
            });
            elm.bind('blur', function() {
                scope.$apply(function() {
                    ngModelCtrl.$setViewValue(elm.val());
                });
            });
        }

    }
});

app.directive('discountNumber', function () {
      return {
        restrict: 'A',
        link: function (scope, elm, attrs, ctrl) {
            elm.on('keyup', function (event) {
                var $input = $(this);
                var value = $input.val();
                value = value.replace(/[^0-9\.]/g, '');
                var findsDot = new RegExp(/\./g)
                var containsDot = value.match(findsDot)
                if (containsDot != null && ([46, 110, 190].indexOf(event.which) > -1)) {
                    event.preventDefault();
                    return false;
                }
                if(containsDot != null) {
                  var data = value.split(".")
                  if(data[1].length == 2 && (!([8,39,37].indexOf(event.which) > -1))) {
                    event.preventDefault();
                    return false;
                  }
                }

                $input.val(value);
                console.log(value);

                if (99.99 > parseFloat(value)) {
                  return true;
                } else if (value == "") {
                  return true;
                } else {
                  $input.val(99.99);
                  return false;
                }
            });
        }
      }
    });


  app.config(['$httpProvider', function($httpProvider) {

    $httpProvider.responseInterceptors.push(function($q, $rootScope) {
      return function(promise) {
          // same as above
          promise.then(function(data){
            if(data.status == 200) {
              if (data.data.message == "invalid user") {
                $rootScope.$broadcast('invalidUser');
              }
            }
          })
          return promise;
      }
    });
  }])
