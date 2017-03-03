'use strict';

function uploads($scope, Session, $http, $rootScope, Service) {

  $scope.url = Session.url;
  var vm = this;
  vm.service = Service;
  $scope.uploads = [{
                   title: "Orders Download/ Upload",
                   download: "Download Order Form",
                   upload: "Upload order Form",
                   durl: "order_form/",
                   uurl: "order_upload/",
                   dparam: "download-order-form",
                   value: ""
                 }, {
                   title: "SKU Download/ Upload",
                   download: "Download SKU Form",
                   upload: "Upload SKU Form",
                   durl: "sku_form/",
                   uurl: "sku_upload/",
                   dparam: "download-sku-file",
                   value: ""
                 }, {
                   title: "Inventory Download/ Upload",
                   download: "Download Inventory Form",
                   upload: "Upload Inventory Form",
                   durl: "inventory_form/",
                   uurl: "inventory_upload/",
                   dparam: "download-file",
                   value: ""
                 }, {
                   title: "Supplier Download/ Upload",
                   download: "Download 	Supplier Form",
                   upload: "Upload Supplier Form",
                   durl: "supplier_form/",
                   uurl: "supplier_upload/",
                   dparam: "download-supplier-file",
                   value: ""
                 }, {
                   title: "Supplier-SKU Download/ Upload",
                   download: "Download Supplier-SKU Form",
                   upload: "Upload Supplier-SKU Form",
                   durl: "supplier_sku_form/",
                   uurl: "supplier_sku_upload/",
                   dparam: "download-supplier-sku-file",
                   value: ""
                 }, {
                   title: "Location Download/ Upload",
                   download: "Download Location Form",
                   upload: "Upload Location Form",
                   durl: "location_form/",
                   uurl: "location_upload/",
                   dparam: "download-loc-file",
                   value: ""
                 }, {
                   title: "Purchase Orders Download/ Upload",
                   download: "Download Purchase Form",
                   upload: "Upload Purchase Form",
                   durl: "purchase_order_form/",
                   uurl: "purchase_order_upload/",
                   dparam: "download-purchase-order-form",
                   value: ""
                 }, {
                   title: "Move Inventory Download/ Upload",
                   download: "Download Move Inventory Form",
                   upload: "Upload Move Inventory Form",
                   durl: "move_inventory_form/",
                   uurl: "move_inventory_upload/",
                   dparam: "download-move-inventory-file",
                   value: ""
                 }, {
                   title: "Market Place - SKU Download/ Upload",
                   download: "Download Market SKU Form",
                   upload: "Upload Market SKU Form",
                   durl: "marketplace_sku_form/",
                   uurl: "marketplace_sku_upload/",
                   dparam: "download-marketplace-sku-file",
                   value: ""
                 }, {
                   title: "BOM - SKU Download/ Upload",
                   download: "Download BOM Form",
                   upload: "Upload BOM Form",
                   durl: "bom_form/",
                   uurl: "bom_upload/",
                   dparam: "download-bom-file",
                   value: ""
                 }, {
                   title: "Combo SKU Download/ Upload",
                   download: "Download Combo SKU Form",
                   upload: "Upload Combo SKU Form",
                   durl: "combo_sku_form/",
                   uurl: "combo_sku_upload/",
                   dparam: "download-combo-sku-file",
                   value: ""
                 }, {
                   title: "Inventory Adjustment Download/ Upload",
                   download: "Download Adjustment Form",
                   upload: "Upload Adjustment Form",
                   durl: "inventory_adjust_form/",
                   uurl: "inventory_adjust_upload/",
                   dparam: "download-inventory-adjust-file",
                   value: ""
                 }, {
                   title: "Vendor Download/ Upload",
                   download: "Download Vendor Form",
                   upload: "Upload Vendor Form",
                   durl: "vendor_form/",
                   uurl: "vendor_upload/",
                   dparam: "download-vendor-file",
                   value: ""
                 }, {
                   title: "Customer Download/ Upload",
                   download: "Download Customer Form",
                   upload: "Upload Customer Form",
                   durl: "customer_form/",
                   uurl: "customer_upload/",
                   dparam: "download-customer-file",
                   value: ""
                 }, {
                   title: "Sales Returns Download/ Upload",
                   download: "Download Sales Returns Form",
                   upload: "Upload Sales Returns Form",
                   durl: "sales_returns_form/",
                   uurl: "sales_returns_upload/",
                   dparam: "download-sales-returns",
                   value: ""
                 }, {
                   title: "Pricing Master Download/ Upload",
                   download: "Download Pricing Master Form",
                   upload: "Upload Pricing Master Form",
                   durl: "pricing_master_form/",
                   uurl: "pricing_master_upload/",
                   dparam: "download-pricing-master",
                   value: ""
                 }
                 ]

  $scope.download = function(data) {

    $http({
    url: Session.url+data.durl+"?"+data.dparam+"="+data.value,
    method: 'GET'
    })
    .success(function(data, status, headers, config){
      var anchor = angular.element('<a/>');
     anchor.attr({
         href: 'data:attachment/csv;charset=utf-8,' + encodeURI(data),
         target: '_blank',
         download: 'filename.xls'
     })[0].click();
    });
    saveAs(blob, 'File_Name_With_Some_Unique_Id_Time' + '.xlsx');
  }

  $scope.$on("excelSelected", function (event, args) {
        $scope.$apply(function () {
            $scope.files.push(args.file);
            $scope.uploadFile(args.url, args.index);
        });
    });

  $scope.disable = false;
  $scope.files = [];
  $scope.uploadFile = function(data, index){
    $scope.disable = true;
    vm.service.showNoty("Started Uploading");
    $(".preloader").removeClass("ng-hide").addClass("ng-show");
    var file = $scope.files[0];
               
    console.log('file is ' );
    console.dir(file);
    var uploadUrl = Session.url+data;

    var fd = new FormData();
    fd.append('files', file);

    $http.post(uploadUrl, fd, {
      transformRequest: angular.identity,
      headers: {'Content-Type': undefined}
    })
    .success(function(data){
      if (data == "Success" || (data.search("Invalid") > -1)) {
        vm.service.showNoty(data);
        $scope.disable = false;
        $(".preloader").removeClass("ng-show").addClass("ng-hide");
        $scope.files = [];
        $("input").val('')
      } else {
        upload_status(data, index);
      }
    })
    .error(function(){
      vm.service.showNoty("Upload Fail");
      $("input").val('');
      $scope.disable = false;
    }); 
  };

  function upload_status(msg, index) {

    if (msg != "Success" && msg != "Upload Fail") {

      $scope.uploads[parseInt(index)].download = "Download Error Form";
      $scope.uploads[parseInt(index)].value = msg;
      vm.service.showNoty("Please Download The Error Form");
    } else {
    vm.service.showNoty(msg);
    }
    $scope.disable = false;
    $(".preloader").removeClass("ng-show").addClass("ng-hide");
    $scope.files = [];
    $("input").val('')
  }

}

var app = angular.module('urbanApp')
  .controller('Uploads', ['$scope', 'Session', '$http', '$rootScope', 'Service', uploads]);

app.directive('excelUpload', function () {
    return {
        scope: true,
        link: function (scope, el, attrs) {
            el.bind('change', function (event) {
                var files = event.target.files;
                var url = $(this).attr('data');
                var index = $(this).attr('index');
                for (var i = 0;i<files.length;i++) {
                    scope.$emit("excelSelected", { file: files[i], url: url , index: index});
                }
            });
        }
    };
});
