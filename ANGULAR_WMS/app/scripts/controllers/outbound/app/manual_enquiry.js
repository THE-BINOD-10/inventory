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

    $ctrl.is_skuId_empty = false;
    $ctrl.selected_style = {};
    for(let i=0; i<styles.length; i++) {
      if(styles[i].sku_class == style){
        $ctrl.selected_style = styles[i];
      }
    }
    console.log($ctrl.selected_style);
  }

  $ctrl.place = function(form) {

    if(form.$valid) {
      var formData = new FormData();
      var el = $("#image-upload");
      debugger
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
                $scope.$apply(function() {
                  angular.copy(empty_data, $ctrl.model_data);
                  $ctrl.upload_name = [];
                  $ctrl.uploading = false;
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
  }

  var imagesPreview = function(input, placeToInsertImagePreview) {
    if (input.files) {
        var filesAmount = input.files.length;
        for (var i = 0; i < filesAmount; i++) {
          var reader = new FileReader();
          reader.onload = function(event) {
          // $($.parseHTML('<div class="col-md-3" ng-mouseover="Enquiry.show_remove[$index]=true" ng-mouseleave="Enquiry.show_remove[$index]=false"><img src="'+event.target.result+'" width="100%"><button class="btn btn-danger mr10" ng-hide="Enquiry.show_remove[$index]"  ng-if="Enquiry.show_remove[$index]" style="position:absolute;top:0px;right:0px;" ng-click="Enquiry.remove_image($index)">X</button></div>')).appendTo(placeToInsertImagePreview);
          $($.parseHTML('<div class="col-md-3 dyn_imgs no-padding m5"><img src="'+event.target.result+'" width="100%"></div>')).appendTo(placeToInsertImagePreview);
        }
        reader.readAsDataURL(input.files[i]);
      }
    }
  };

  $('#image-upload').on('change', function() {
    $("div.multi_imgs_display").empty();
    imagesPreview(this, 'div.multi_imgs_display');
  });

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
