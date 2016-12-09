'use strict';

var app = angular.module('urbanApp', ['datatables', 'rzModule'])
app.controller('SKUMasterTable',['$scope', '$http', '$state', 'Session','DTOptionsBuilder', 'DTColumnBuilder', '$log', 'colFilters', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, $log, colFilters) {

    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url:  Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'SKUMaster'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)

    function fnCallback(data) {
      console.log(data);
    }

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Sellerworx SKU Code').withTitle('SKU Code').renderWith(function(data, type, full, meta) {
                        full.image_url = ((full.image_url.indexOf("static")) > -1 && (full.image_url != '/static/img/default-image.jpg')) ? Session.host+full.image_url.slice(1):full.image_url;
                        full.image_url = (full.image_url == '/static/img/default-image.jpg') ? 'images/wms/dflt.jpg' : full.image_url;
                        return '<img style="width: 35px;height: 40px;display: inline-block;margin-right: 10px;" src='+full.image_url+'>'+'<p style=";display: inline-block;">'+ full['WMS SKU Code'] +'</p>';
                        }),
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
        DTColumnBuilder.newColumn('SKU Type').withTitle('SKU Type'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('Status').withTitle('Status').renderWith(function(data, type, full, meta) {
                          var status = 'Active';
                          var color = '#70cf32';
                          if (data != status) {
                            status = 'Inactive';
                            color = '#d96557';
                          }
                          return '<span style="padding: 1px 6px 3px;border-radius: 10px;background: #f4f4f5;">'+'<i class="fa fa-circle" style="color:'+color+';display: inline-block;"></i>'+'<p style="display: inline-block;margin: 0px;padding-left: 5px;">'+status+'</p>'+'</span>'
                        }).withOption('width', '80px')
    ];

    var empty_data = {
                      sku_data:{
                        sku_code:"",
                        wms_code:"",
                        sku_group:"",
                        sku_desc:"",
                        sku_type:"",
                        zone:"",
                        sku_class:"",
                        sku_category:"",
                        threshold_quantity:"",
                        online_percentage:"",
                        status:0,
                        qc_check:0,
                        image_url:"",
                      },
                      "zones":[],
                      "market_data": [{
                        "market_id":"",
                        "market_sku_type":"",
                        "marketplace_code":"",
                        "description":""
                        }
                      ],
                      "market_list":["Flipkart","Snapdeal","Paytm","Amazon","Shopclues","HomeShop18","Jabong","Indiatimes"]
                    }
    vm.model_data = {};
    angular.extend(vm.model_data, empty_data);

    vm.title = "Add SKU";
    vm.update = true;
    vm.update_data = {};
    vm.zone_id = "red";
    vm.status_data = ['Inactive','Active'];
    vm.status = vm.status_data[0];
    vm.qc_data = ['Disable','Enable'];
    vm.qc = vm.qc_data[0]
    vm.market_list = [];
    vm.market;
    vm.market_data = [];
    vm.files = [];
    $scope.$on("fileSelected", function (event, args) {
        $scope.$apply(function () {            
            vm.files.push(args.file);
        });
    });
    vm.isEmptyMarket = false 
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                vm.model_data = {};
                angular.extend(vm.model_data, empty_data);
                $http.get(Session.url+'get_sku_data/?data_id='+aData.DT_RowAttr["data-id"], {withCredential: true}).success(function(data, status, headers, config) {

                  vm.update=true;
                  vm.model_data.sku_data = data.sku_data;
                  vm.model_data.market_data = data.market_data;
                  vm.model_data.zones = data.zones;
                  var index = vm.model_data.zones.indexOf(vm.model_data.sku_data.zone);
                  vm.model_data.sku_data.zone = vm.model_data.zones[index];
                  
                  for (var j=0; j<vm.model_data.market_data.length; j++) {
                    var index = vm.model_data.market_list.indexOf(vm.model_data.market_data[j].market_sku_type);
                    vm.model_data.market_data[j].market_sku_type = vm.model_data.market_list[index];
                  };
                
                  vm.model_data.sku_data.status = vm.status_data[vm.model_data.sku_data.status];
                  vm.model_data.sku_data.qc_check = vm.qc_data[vm.model_data.sku_data.qc_check];
 
                  vm.isEmptyMarket = (data.market_data.length > 0) ? false : true;
                  $state.go('app.masters.SKUMaster.update');
                });
                vm.title ="Update SKU";
            });
        });
        //vm.priceSlider.options.ceil = parseInt($('.paginate_button[data-dt-idx=7]').text());
        return nRow;
    }

    vm.close = close;
    function close() {

      vm.model_data = {};
      angular.extend(vm.model_data, empty_data);
      $state.go('app.masters.SKUMaster');
      reloadData();
    }
    vm.change_page = function() {
      console.log(this);
    }

  //*****************
  vm.market_send = {market_sku_type:[],marketplace_code:[],description:[],market_id:[]}
  vm.update_sku = update_sku;
  function update_sku() {

    var data = {
             "image": vm.files
           }
    var elem = angular.element($('form'));
    elem = elem[0];
    elem = $(elem).serializeArray();
    for (var i=0;i<elem.length;i++) {
      if(elem[i].name == "market_sku_type") {
        elem[i].value = vm.model_data.market_list[parseInt(elem[i].value)];
      } else if(elem[i].name == "status") {
        elem[i].value = vm.status_data[parseInt(elem[i].value)];
      } else if(elem[i].name == "qc_check") {
        elem[i].value = vm.qc_data[parseInt(elem[i].value)];
      } else if(elem[i].name == "zone_id") {
        elem[i].value = vm.model_data.zones[parseInt(elem[i].value)];
      }
    }

    var formData = new FormData()
    var files = $("#update_sku").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });

    $.each(elem, function(i, val) {
        formData.append(val.name, val.value);
    });

    //elem = $.param(elem);
    /*
    $http.defaults.headers.post["Content-Type"] = "multipart/form-data; boundary=----WebKitFormBoundary7sOFXzhvNWc7WTOL';
    $http({
               method: 'POST',
               url:Session.url+"update_sku/",
               withCredential: true,
               processData : false,
               transformRequest: function (data) {
                 var formData = new FormData();
                 for (var i = 0; i < data.model.length; i++) {
                    formData.append(data.model[i].name, data.model[i].value);
                 }
                 for (var i = 0; i < data.files.length; i++) {
                    formData.append("file" + i, data.files[i]);
                 }
                 return formData;
               },
               data: {model: elem, files: vm.files}
               }).success(function(data, status, headers, config) {
      console.log("success");
      reloadData();
    });*/

    $.ajax({url: Session.url+'update_sku/',
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              reloadData();
            }});
  }

  vm.create_sku = create_sku;
  function create_sku() {

    vm.market_send.market_sku_type = [];
    vm.market_send.marketplace_code = [];
    vm.market_send.description = [];
    for(var i=0; i< vm.model_data.market_data.length; i++){
      vm.market_send.market_sku_type.push(vm.model_data.market_data[i]["market_sku_type"]);
      vm.market_send.marketplace_code.push(vm.model_data.market_data[i]["marketplace_code"]);
      vm.market_send.description.push(vm.model_data.market_data[i]["description"]);
    }
    var data = {
             "image": vm.files
           }
    angular.extend(data,vm.model_data.sku_data);
    angular.extend(data,vm.market_send);
    data.status = vm.status;
    data.qc_check = vm.qc;
    var data = $.param(data); 
    $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
    $http({
               method: 'POST',
               url:"http://176.9.181.43:7878/rest_api/insert_sku/",
               data: data}).success(function(data, status, headers, config) {
      console.log("success");
      $state.go('app.masters.SKUMaster');
    });
  }

  vm.submit = submit;
  function submit(data) {
    if ( data.$valid ){
      if ("Add SKU" == vm.title) {
        vm.create_sku();
      } else {
        vm.update_sku();
      }
    }
  }

  vm.remove_market = remove_market;
  function remove_market(index, id) {

        vm.model_data.market_data.splice(index,1);
        if (id) {
        $http({
            method: 'GET',
            url:Session.url+"delete_market_mapping?data_id="+id,
          }).success(function(data, status, headers, config) {
            console.log("success");
        });
        };
  }
  vm.add_market = add_market;
  function add_market() {

    vm.model_data.market_data.push({description: "",market_id: "",market_sku_type: "",marketplace_code: ""})
    vm.isEmptyMarket = false;
  }

  vm.add_sku = add_sku;
  function add_sku() {

    vm.title = "Add SKU";
    vm.update = false;
    vm.model_data = {};
    angular.extend(vm.model_data, empty_data);
    $state.go('app.masters.SKUMaster.update');
  }

  $scope.validationOpt = {
    rules: {
      namefield: {
        required: true,
        minlength: 3
      },
      urlfield: {
        required: true,
        minlength: 3,
        url: true
      }
    }
  };
}

app.directive('fileUpload', function () {
    return {
        scope: true,        //create a new scope
        link: function (scope, el, attrs) {
            el.bind('change', function (event) {
                var files = event.target.files;
                //iterate files since 'multiple' may be specified on the element
                for (var i = 0;i<files.length;i++) {
                    //emit event upward
                    scope.$emit("fileSelected", { file: files[i] });
                }                                       
            });
        }
    };
});
