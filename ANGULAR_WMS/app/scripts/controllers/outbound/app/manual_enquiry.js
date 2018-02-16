;(function(){

'use strict';

function AppManualEnquiry($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  var $ctrl = this;
  $ctrl.service = Service;

  $ctrl.loading = true;

  $ctrl.category = '';
  $ctrl.categories = [];
  $ctrl.categories_loading = true;
  $ctrl.get_categories = function() {

    var data = {brand: ''};
    Service.apiCall("get_sku_categories/", "GET",data).then(function(data){
      if(data.message) {
        $ctrl.categories = data.data.categories;
        $ctrl.category = "";
      }    
      $ctrl.categories_loading = false;
    });  
  }
  $ctrl.get_categories();

  $ctrl.style = '';
  $ctrl.styles = [];
  $ctrl.get_styles = function(category){

    if(!category) {
      $ctrl.style = "";
      $ctrl.styles = [];
      $ctrl.sku = "";
      $ctrl.skus = [];
      return false;
    }    

    var data = {category: category, is_catalog:true, customer_id: Session.userId}
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

  $ctrl.selected_style = {};
  $ctrl.select_style = function(style, styles) {

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

      console.log($ctrl);

      var formData = new FormData();
      var el = $("#image-upload");
      var files = el[0].files;

      $.each(files, function(i, file) {
        formData.append('po_file', file);
      });

      $.each($ctrl.model_data, function(key, value) {
        formData.append(key, value);
      });
      $ctrl.uploading = true;
      $.ajax({url: Session.url+'upload_po/',
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              if(response == 'Uploaded Successfully') {

                Service.showNoty(response);
              } else {
                Service.showNoty(response, 'warning');
              }
              $ctrl.uploading = false;
            },
            'error': function(response) {
              console.log('fail');
              Service.showNoty('Something Went Wrong', 'warning');
              $ctrl.uploading = false;
            }
      });
    }
  }
}

angular
  .module('urbanApp')
  .controller('AppManualEnquiry', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppManualEnquiry]);

})();
