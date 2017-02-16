'use strict';

var app = angular.module('urbanApp')
app.service('Service',['$rootScope', '$compile','$q', '$http', '$state', '$timeout', 'Session', 'colFilters', 'SweetAlert', 'COLORS', 'DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', '$window', Service]); 

function Service($rootScope, $compile, $q, $http, $state, $timeout, Session, colFilters, SweetAlert, COLORS, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, $window) {

    var vm = this;
    vm.colFilters = colFilters

    vm.stock_transfer = "";

    vm.dyn_data = {
                    style_detail: {
                                    head: {common:["SKU Code", "SKU Description"], sagar_fab: ["Size"]},
                                    keys: {common:["wms_code", "sku_desc"], sagar_fab: ["sku_size"]},
                                    check_stock: {'common':false, 'sagar_fab':true}
                                  }
                  }

    vm.reports = {};

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

    vm.units = ["KGS", "UNITS", "METERS", "INCHES", "CMS", "REAMS", "GRAMS"];

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
              type: 'GET',
              data: send.empty_data,
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers');

      send.dtColumns = vm.build_colums(data.dt_headers);
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
      value = value.replace(/[^0-9\.]/g, '')
      var findsDot = new RegExp(/\./g)
      var containsDot = value.match(findsDot)
      if(containsDot != null) {
        var data = value.split(".")
        var limit = (Session.roles.permissions["decimal_limit"])?Number(Session.roles.permissions["decimal_limit"]):1;
        if(data[1].length >= limit) {
          value = data[0]+"."+data[1].slice(0,limit);
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

    vm.print_excel = function(data, instance, headers, name, stat) {

      var send = {};
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
        send['serialize_data'] = $.param(data);
        send = $.param(send)
      }
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http.post(Session.url+"excel_reports/", send, {withCredential: true}).success(function(data){
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
      $http({  
               method: 'POST',
               url: Session.url+"results_data/",
               data: data}).success(function(data, status, headers, config) {
           window.location = Session.url+data;
           vm.print_enable = false;
      });
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
        var results = response.data;
        if (results.length > 7) {
          results = results.slice(0,7);
        }
        return results.map(function(item){
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

    vm.apiCall = function(url, method, data) {

      var d = $q.defer();
      var response = {message: 0, data:{}}
      if (url) {
        method = (method == "POST") ? method : "GET";
        data = (data) ? data: {};
        var send =  "";
        send = $.param(data);
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        $(".preloader").removeClass("ng-hide").addClass("ng-show");
        if (method == "POST") {  
          $http({
            method: method,
            url:Session.url+url,
            withCredential: true,
            data: send}).success(function(data, status, headers, config) {
              response.data = data;
              response.message = 1;
              $(".preloader").removeClass("ng-show").addClass("ng-hide");
              d.resolve(response);
            }).error(function(){
              response.message = 0;
              $(".preloader").removeClass("ng-show").addClass("ng-hide");
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
              d.resolve(response);
            }).error(function(){
              response.message = 0;
              $(".preloader").removeClass("ng-show").addClass("ng-hide");
              d.resolve(response);
            });
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
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="styles/custom/urban.css" />');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="styles/custom/page.css" media="print"/>');
    mywindow.document.write('<script type="text/javascript" src="vendor/jquery/dist/jquery.min.js"></script>');
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

  vm.build_colums = function(data)  {

    var columns = [];
    angular.forEach(data, function(item) {

      columns.push(DTColumnBuilder.newColumn(item).withTitle(item))
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
