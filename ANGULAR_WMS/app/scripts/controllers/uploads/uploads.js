'use strict';

function uploads($scope, Session, $http, $rootScope, Service, $modal) {

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
                   value: "",
                   show: true,
                   perm: "add_orderdetail"
                 }, {
                   title: "SKU Download/ Upload",
                   download: "Download SKU Form",
                   upload: "Upload SKU Form",
                   durl: "sku_form/",
                   uurl: "sku_upload/",
                   dparam: "download-sku-file",
                   value: "",
                   show: true,
                   perm: "add_skumaster"
                 }, {
                   title: "Inventory Download/ Upload",
                   download: "Download Inventory Form",
                   upload: "Upload Inventory Form",
                   durl: "inventory_form/",
                   uurl: "inventory_upload/",
                   dparam: "download-file",
                   value: "",
                   show: true,
                   perm: "add_stockdetail"
                 }, {
                   title: "Supplier Download/ Upload",
                   download: "Download 	Supplier Form",
                   upload: "Upload Supplier Form",
                   durl: "supplier_form/",
                   uurl: "supplier_upload/",
                   dparam: "download-supplier-file",
                   value: "",
                   show: true,
                   perm: "add_suppliermaster"
                 }, {
                   title: "Supplier-SKU Download/ Upload",
                   download: "Download Supplier-SKU Form",
                   upload: "Upload Supplier-SKU Form",
                   durl: "supplier_sku_form/",
                   uurl: "supplier_sku_upload/",
                   dparam: "download-supplier-sku-file",
                   value: "",
                   show: true,
                   perm: "add_skusupplier"
                 }, {
                   title: "Supplier-SKU Attributes Download/ Upload",
                   download: "Download Supplier-SKU Attributes Form",
                   upload: "Upload Supplier-SKU Attributes Form",
                   durl: "supplier_sku_attributes_form/",
                   uurl: "supplier_sku_attributes_upload/",
                   dparam: "download-supplier-sku-attributes-file",
                   value: "",
                   show: true,
                   perm: "add_skusupplier"
                 },{
                   title: "Location Download/ Upload",
                   download: "Download Location Form",
                   upload: "Upload Location Form",
                   durl: "location_form/",
                   uurl: "location_upload/",
                   dparam: "download-loc-file",
                   value: "",
                   show: true,
                   perm: "add_locationmaster"
                 }, {
                   title: "Purchase Orders Download/ Upload",
                   download: "Download Purchase Form",
                   upload: "Upload Purchase Form",
                   durl: "purchase_order_form/",
                   uurl: "purchase_order_upload/",
                   dparam: "download-purchase-order-form",
                   value: "",
                   show: true,
                   perm: "add_openpo"
                 }, {
                   title: "Move Inventory Download/ Upload",
                   download: "Download Move Inventory Form",
                   upload: "Upload Move Inventory Form",
                   durl: "move_inventory_form/",
                   uurl: "move_inventory_upload/",
                   dparam: "download-move-inventory-file",
                   value: "",
                   show: true,
                   perm: "change_inventoryadjustment"
                 }, {
                   title: "Market Place - SKU Download/ Upload",
                   download: "Download Market SKU Form",
                   upload: "Upload Market SKU Form",
                   durl: "marketplace_sku_form/",
                   uurl: "marketplace_sku_upload/",
                   dparam: "download-marketplace-sku-file",
                   value: "",
                   show: true,
                   perm: "add_skumaster"
                 }, {
                   title: "BOM - SKU Download/ Upload",
                   download: "Download BOM Form",
                   upload: "Upload BOM Form",
                   durl: "bom_form/",
                   uurl: "bom_upload/",
                   dparam: "download-bom-file",
                   value: "",
                   show: Session.roles.permissions.add_bommaster,
                   perm: "add_bommaster"
                 }, {
                   title: "Combo SKU Download/ Upload",
                   download: "Download Combo SKU Form",
                   upload: "Upload Combo SKU Form",
                   durl: "combo_sku_form/",
                   uurl: "combo_sku_upload/",
                   dparam: "download-combo-sku-file",
                   value: "",
                   show: true,
                   perm: "add_skumaster"
                 }, {
                   title: "Inventory Adjustment Download/ Upload",
                   download: "Download Adjustment Form",
                   upload: "Upload Adjustment Form",
                   durl: "inventory_adjust_form/",
                   uurl: "inventory_adjust_upload/",
                   dparam: "download-inventory-adjust-file",
                   value: "",
                   show: true,
                   perm: "add_inventoryadjustment"
                 }, {
                   title: "Vendor Download/ Upload",
                   download: "Download Vendor Form",
                   upload: "Upload Vendor Form",
                   durl: "vendor_form/",
                   uurl: "vendor_upload/",
                   dparam: "download-vendor-file",
                   value: "",
                   show: true,
                   perm: "add_vendormaster"
                 }, {
                   title: "Customer Download/ Upload",
                   download: "Download Customer Form",
                   upload: "Upload Customer Form",
                   durl: "customer_form/",
                   uurl: "customer_upload/",
                   dparam: "download-customer-file",
                   value: "",
                   show: true,
                   perm: "add_customermaster"
                 }, {
                   title: "Sales Returns Download/ Upload",
                   download: "Download Sales Returns Form",
                   upload: "Upload Sales Returns Form",
                   durl: "sales_returns_form/",
                   uurl: "sales_returns_upload/",
                   dparam: "download-sales-returns",
                   value: "",
                   show: true,
                   perm: "add_orderreturns"
                 }, {
                   title: "Pricing Master Download/ Upload",
                   download: "Download Pricing Master Form",
                   upload: "Upload Pricing Master Form",
                   durl: "pricing_master_form/",
                   uurl: "pricing_master_upload/",
                   dparam: "download-pricing-master",
                   value: "",
                   show: true,
                   perm: "add_pricemaster"
                 }, {
                   title: "Network Master Download/ Upload",
                   download: "Download Network Master Form",
                   upload: "Upload Network Master Form",
                   durl: "network_master_form/",
                   uurl: "network_master_upload/",
                   dparam: "download-network-master",
                   value: "",
                   show: true,
                   perm: "add_networkmaster"
                 }, {
                   title: "Order Label Mapping Download/ Upload",
                   download: "Download Order Label Mapping Form",
                   upload: "Upload Order Label Mapping Form",
                   durl: "order_label_mapping_form/",
                   uurl: "order_label_mapping_upload/",
                   dparam: "order-label-mapping-form",
                   value: "",
                   show: true,
                   perm: "add_orderlabels"
                 }, {
                   title: "Order Serial Mapping Download/ Upload",
                   download: "Download Order Serial Mapping Form",
                   upload: "Upload Order Serial Mapping Form",
                   durl: "order_serial_mapping_form/",
                   uurl: "order_serial_mapping_upload/",
                   dparam: "order-serial-mapping-form",
                   value: "",
                   show: true,
                   perm: "use_imei"
                 }, {
                   title: "PO Serial Mapping Download/ Upload",
                   download: "Download PO Serial Mapping Form",
                   upload: "Upload PO Serial Mapping Form",
                   durl: "po_serial_mapping_form/",
                   uurl: "po_serial_mapping_upload/",
                   dparam: "po-serial-mapping-form",
                   value: "",
                   perm: "use_imei"
                 }, {
                   title: "Job Order Download/ Upload",
                   download: "Download Job Order Form",
                   upload: "Upload Job Order Form",
                   durl: "job_order_form/",
                   uurl: "job_order_upload/",
                   dparam: "job-order-file",
                   value: "",
                   show: Session.roles.permissions.add_jomaterial,
                   perm: "add_jomaterial"
                 }, {
                   title: "Marketplace Order Serial Download/ Upload",
                   download: "Download Marketplace Serial Form",
                   upload: "Upload Marketplace Serial Form",
                   durl: "marketplace_serial_form/",
                   uurl: "marketplace_serial_upload/",
                   dparam: "marketplace-serial-file",
                   value: "",
                   perm: "use_imei"
                 }, {
                    title: "OrderId AWB Mapping Download/Upload",
                    download: "Download OrderId AWB Mapping Form",
                    upload: "Upload OrderId AWB Mapping Form",
                    durl: "orderid_awb_mapping_form/",
                    uurl: "orderid_awb_upload/",
                    dparam: "orderid-awb-map-file",
                    value: "",
                    show: true,
                    perm: "create_shipment_type"
                 }, {
                   title: "Seller-Seller Transfer form Download/ Upload",
                   download: "Download Seller-Seller Transfer Form",
                   upload: "Upload Seller-Seller Transfer Form",
                   durl: "seller_transfer_form/",
                   uurl: "seller_transfer_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "add_sellerstocktransfer"
                 }, {
                   title: "SKU Substitution form Download/ Upload",
                   download: "Download SKU Substitution Form",
                   upload: "Upload SKU Substitution Form",
                   durl: "sku_substitution_form/",
                   uurl: "sku_substitution_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "add_substitutionsummary"
                 },{
                   title: "Targets form Download/ Upload",
                   download: "Targets Download Form",
                   upload: "Targets Upload Form",
                   durl: "targets_form/",
                   uurl: "targets_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "add_targetmaster"
                 }, {
                   title: "Central Order Form Download/ Upload",
                   download: "Central Order Download Form",
                   upload: "Central Order Upload Form",
                   durl: "central_order_form/",
                   uurl: "central_order_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "add_intermediateorders"
                 },
                 {
                   title: "Create Stock Transfer Order Form Download/ Upload",
                   download: "Stock Transfer Order Download Form",
                   upload: "Stock Transfer Order Upload Form",
                   durl: "stock_transfer_order_form/",
                   uurl: "stock_transfer_order_upload/",
                   dparam: "download-stock-transfer-file",
                   value: ""
                 },{
                   title: "SKUPack Master Form Download/ Upload",
                   download: "SKUPack Master Download Form",
                   upload: "SKUPack Master Upload Form",
                   durl: "skupack_master_download/",
                   uurl: "skupack_master_upload/",
                   dparam: "download-file",
                   value: "",
                 },
                 {
                   title: "BlockStock Form Download/ Upload",
                   download: "BlockStock Download Form",
                   upload: "BlockStock Upload Form",
                   durl: "block_stock_download/",
                   uurl: "block_stock_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "add_enquirymaster",
                 },
                 {
                   title: "Custom Order Form Download/ Upload",
                   download: "Custom Order Download Form",
                   upload: "Custom Order Upload Form",
                   durl: "custom_order_download/",
                   uurl: "custom_order_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "add_enquirymaster",
                 },
                 {
                   title: "Cluster SKU Mapping Download/ Upload",
                   download: "Cluster SKU Mapping Download Form",
                   upload: "Cluster SKU Mapping Upload Form",
                   durl: "cluster_sku_form/",
                   uurl: "cluster_sku_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "add_clusterskumapping",
                 },
                 {
                   title: "Combo Allocate Stock Download/ Upload",
                   download: "Combo Allocate Stock Download Form",
                   upload: "Combo Allocate Stock Upload Form",
                   durl: "combo_allocate_form/",
                   uurl: "combo_allocate_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "change_substitutionsummary",
                 },
                 {
                   title: "Brand Level Pricing Download/ Upload",
                   download: "Brand Level Pricing Download Form",
                   upload: "Brand Level Pricing Upload Form",
                   durl: "brand_level_pricing_form/",
                   uurl: "brand_level_pricing_upload/",
                   dparam: "download-file",
                   value: "",
                   perm: "add_pricemaster",
                 },
                 {
                   title: "SKU Substitute Download/ Upload",
                   download: "Download SKU Form",
                   upload: "Upload SKU Form",
                   durl: "sku_substitutes_form/",
                   uurl: "sku_substitutes_upload/",
                   dparam: "download-file",
                   value: "",
                   show: true,
                   perm: "add_skumaster"
                 },
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
    $scope.files = [];
    var uploadUrl = Session.url+data;
    var fd = new FormData();
    fd.append('files', file);
    $http.post(uploadUrl, fd, {
      transformRequest: angular.identity,
      headers: {'Content-Type': undefined}
    })
    .success(function(data){
      if (Object.keys(data).includes('data_list')) {
        $scope.disable = false;
        vm.title = "View Preview";
        var mod_data = data;
        var modalInstance = $modal.open({
          templateUrl: 'views/uploads/purchase_preview_popup.html',
          controller: 'purchaseOrderPreview',
          controllerAs: 'pop',
          size: 'lg',
          backdrop: 'static',
          keyboard: false,
          resolve: {
            items: function () {
              return mod_data;
            }
          }
        });
        modalInstance.result.then(function (selectedItem) {
          if(selectedItem['input'] == 'confirm'){
            var uploadUrl = Session.url+'purchase_order_upload_preview/'
            var fd = new FormData();
            fd.append('data_list', JSON.stringify(selectedItem['datum']))
            $http.post(uploadUrl, fd, {
              transformRequest: angular.identity,
              headers: {'Content-Type': undefined}
            }).success(function(data){
              $(".preloader").removeClass("ng-show").addClass("ng-hide");
              $("input").val('');
              vm.service.showNoty('Success');
              selectedItem['datum'] = ''
            })
          } else {
            $(".preloader").removeClass("ng-show").addClass("ng-hide");
            $("input").val('');
            vm.service.showNoty('Upload Cancelled !');
            selectedItem['datum'] = ''
          }
        });
      } else {
        if ((data == "Success") || (data.search("Invalid") > -1) || (data.search("not") > -1) || (data.search("Fail") > -1)) {
          var type = "";
          type = (data == "Success")? "": "error";
          vm.service.showNotyNotHide(data, type);
          $scope.disable = false;
          $(".preloader").removeClass("ng-show").addClass("ng-hide");
          $scope.files = [];
          $("input").val('')
        } else {
          upload_status(data, index);
        }
      }
    })
    .error(function(){
      vm.service.showNoty("Upload Fail");
      $("input").val('');
      $scope.files = [];
      $scope.disable = false;
    });
  };

  function upload_status(msg, index) {
    if (!msg.includes("Success") && msg != "Upload Fail" && msg.indexOf("Orders exceeded") === -1) {
      $scope.uploads[parseInt(index)].download = "Download Error Form";
      $scope.uploads[parseInt(index)].value = msg;
      vm.service.showNotyNotHide("Please Download The Error Form");
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
  .controller('Uploads', ['$scope', 'Session', '$http', '$rootScope', 'Service', '$modal', uploads]);

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

function purchaseOrderPreview($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items, Data) {
  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  setTimeout(function(){
    $(".modal-dialog").addClass("print-width");
    $(".print-invoice2").addClass("print-height")
    angular.element(".modal-body").html($(items['data_preview']));
  }, 1000);
  vm.ok = function (input) {
    var data = {
      'input': input,
      'datum': items['data_list']
    }
    $modalInstance.close(data);
  };
}
angular
  .module('urbanApp')
  .controller('purchaseOrderPreview', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', purchaseOrderPreview]);
