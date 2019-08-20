;(function(){

'use strict';

function AppManualEnquiry($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  var $ctrl = this;
  $ctrl.service = Service;

  $ctrl.loading = true;
  $ctrl.is_skuId_empty = false;

  var empty_data = {customer_name: '', sku_id: '', category: '', customization_type: 'custom_price', ask_price: '', expected_date: '', remarks: ''};

  $ctrl.category = '';
  $ctrl.categories = [];
  $ctrl.categories_loading = true;
  $ctrl.customization_types = {};
  $ctrl.client_logo = Session.parent.logo;
  $ctrl.api_url = Session.host;
  $ctrl.enable_table = false;


  $ctrl.style = '';
  $ctrl.styles = [];
  function get_styles(category){

    if(!category) {
      $ctrl.style = "";
      $ctrl.styles = [];
      $ctrl.sku = "";
      $ctrl.skus = [];
      return false;
    }

    if (category == 'ALL') {
      category = "";
    }

    var data = {category: category, is_catalog:true, customer_id: Session.userId, file: true}
    $ctrl.styles_loading = true;
    $ctrl.styles = [];
    Service.apiCall("get_sku_catalogs/", "POST", data).then(function(data) {
      if(data.message) {
        $ctrl.styles = data.data.data;
        $ctrl.style = "";
        $ctrl.sku = "";
        $ctrl.skus = [];
      }
      $ctrl.styles_loading = false;
    });
  }

  $ctrl.get_categories = function() {

    var data = {brand: ''};
    Service.apiCall("get_sku_categories/", "GET",data).then(function(data){
      if(data.message) {
        $ctrl.categories = data.data.categories;
        $ctrl.category = "";
        $ctrl.customization_types= data.data.customization_types;
        $ctrl.corporates = data.data.reseller_corporates;
      }
      $ctrl.categories_loading = false;
    });
    get_styles('ALL');
  }
  $ctrl.get_categories();

  $ctrl.selected_style = {};
  $ctrl.select_style = function(style, styles) {
    $ctrl.variant_url = ''
    $ctrl.selected_data = ''
    angular.forEach(styles, function(data){
      if(style == data.sku_class){
        $ctrl.selected_data = data
      }
    })
    if ($ctrl.selected_data != '') {
      $ctrl.variant_url = $ctrl.api_url.slice(0, -1) + $ctrl.selected_data.image_url
    }
    $ctrl.enable_table = false
    $ctrl.is_skuId_empty = false;
    $ctrl.selected_style = {};
    if(style){
      var send = {sku_class:style, customer_id: Session.userId, is_catalog: true, level: 1, is_style_detail: true}
      $ctrl.service.apiCall("get_sku_variants/", "POST", send).then(function(data) {
        $ctrl.selected_style = $ctrl.get_table_data($ctrl.selected_data, data.data.lead_times, data.data.data)
        $ctrl.enable_table = true
      })
    }
  }
  $ctrl.get_table_data = function(data, leadtimes, variants){
    $ctrl.temp_selected_style = {}
    $ctrl.temp_selected_style = data.variants;
    angular.forEach(variants, function(data){
      var physical_quantity = 0
      for (var i = 0; i < leadtimes.length; i++) {
        if (data[leadtimes[i]] == 'null') {
          physical_quantity = physical_quantity + 0;
        } else {
          physical_quantity = physical_quantity + data[leadtimes[i]];
        }
      }
      physical_quantity = physical_quantity + data.intransit_quantity;
      angular.forEach($ctrl.temp_selected_style, function(item){
        if(item.wms_code == data.wms_code){
          item.style_quantity = physical_quantity;
          item.blocked_quantity = data.blocked_quantity;
        }
      })
    })
    return $ctrl.temp_selected_style;
  }
  $ctrl.change_variant_quantity = function(data, size) {
    $ctrl.totalQuantity = 0
    for(let k=0; k<data.length; k++) {
      if(data[k].quantity){
        $ctrl.totalQuantity += parseInt(data[k].quantity)
        $ctrl.model_data.quantity = $ctrl.totalQuantity
      }else if(data[k].quantity == 'undefined' || data[k].quantity == ''){
        $ctrl.model_data.quantity = $ctrl.totalQuantity
      }
    }
  }
  $ctrl.place = function(form) {
    $ctrl.loading = true;
    let sku_quantity = {}
    for(let j=0; j<$ctrl.selected_style.length; j++) {
      if($ctrl.selected_style[j].quantity){
        sku_quantity[$ctrl.selected_style[j].wms_code] = parseInt($ctrl.selected_style[j].quantity)
      }else if($ctrl.selected_style[j].quantity == 'undefined' || $ctrl.selected_style[j].quantity == ''){}
    }
    if(form.$valid) {
      var formData = new FormData();
      var el = $("#image-upload");
      if (el.length) {
        var files = el[0].files;
      }

      $.each(files, function(i, file) {
        formData.append('po_file', file);
      });

      if ($ctrl.model_data.sku_id === "") {
        $ctrl.is_skuId_empty = true;
        return false;
      }

      $.each($ctrl.model_data, function(key, value) {
        formData.append(key, value);
      });
      formData.append('enq_status', 'new_order');
      // formData['status'] = 'new_order';
      var remarks = "";
      angular.forEach($ctrl.custom_remarks, function(remark) {

        if(remark.remark) {

          if(!remarks) {

            remarks = remark.remark;
          } else {

            remarks += "<<>>" + remark.remark;
          }
        }
      })
      formData.append("custom_remarks", remarks);
      formData.append("sku_quantity_map", JSON.stringify(sku_quantity));
      $ctrl.uploading = true;
      $.ajax({url: Session.url+'place_manual_order/',
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              if(response == 'Success') {
                Service.showNoty(response);
                $ctrl.loading =false;
                $scope.$apply(function() {
                  angular.copy(empty_data, $ctrl.model_data);
                  // $ctrl.custom_remarks = ['remarks':''];
                  $ctrl.upload_name = [];
                  $ctrl.uploading = false;
                  $ctrl.clearFiles();
                });
                $("input[type='file']").val('');
              } else {
                Service.showNoty(response, 'warning');
                $scope.$apply(function() {
                  $ctrl.uploading = false;
                })
              }
            },
            'error': function(response) {
              console.log('fail');
              Service.showNoty('Something Went Wrong', 'warning');
              $ctrl.uploading = false;
            }
      });
    }
    $ctrl.loading =true;
  }

  var imagesPreview = function(input, placeToInsertImagePreview) {
    if (input.files) {
      var filesAmount = input.files.length;
      for (var i = 0; i < filesAmount; i++) {
        var reader = new FileReader();
        reader.onload = function(event) {
          if(filesAmount == 1) {
            $($.parseHTML('<div class="col-lg-8 col-md-8 col-sm-12 col-xs-12 image_display1" align="center"><img src="'+event.target.result+'" width="100%"></div>')).appendTo(placeToInsertImagePreview);
          } else {
            $($.parseHTML('<div class="col-md-3 dyn_imgs no-padding m5"><img src="'+event.target.result+'" width="100%"></div>')).appendTo(placeToInsertImagePreview);
          }
        }
        reader.readAsDataURL(input.files[i]);
      }
    }
  };

  $('#image-upload').on('change', function() {
    $("div.multi_imgs_display").empty();
    imagesPreview(this, 'div.multi_imgs_display');
  });

  $ctrl.clearFiles = function(){
    $ctrl.totalQuantity = 0
    $('#image-upload').val('');
    $("div.multi_imgs_display").empty();
  }

  $ctrl.upload_name = [];
  $scope.$on("fileSelected", function (event, args) {
    $scope.$apply(function () {
      // readURL(this);
      $ctrl.upload_name = [];
      if (args.msg == 'success') {
        angular.forEach(args.file, function(data){
          $ctrl.upload_name.push(data.name)
        })
      } else {
        Service.showNoty(args.msg, 'warning');
      }
    });
  });
}

angular
  .module('urbanApp')
  .controller('AppManualEnquiry', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppManualEnquiry]);

})();
