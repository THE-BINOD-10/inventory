;(function() {
'use strict';

function uploadCtrl($scope, FileUploader, Session, Data) {

  $scope.categories = ['SKU', 'Category', 'Brand'];
  $scope.category_type = $scope.categories[0];
  Data.files_type = $scope.category_type;

  var uploader = $scope.uploader = new FileUploader({
    url: Session.url+"upload_images/",
    // formData: [
    //     { "files_type": Data.files_type },
    // ],
    withCredentials: 'true'
  });

  $scope.change_img_type = function(type){
    Data.files_type = type;
    uploader.formData = [{'files_type': Data.files_type}];
  }

  $scope.change_img_type('SKU');

  // FILTERS

  uploader.filters.push({
    name: 'customFilter',
    fn: function (item /*{File|FileLikeObject}*/ , options) {
      return this.queue.length < 10000;
    }
  });

  uploader.onCompleteAll = function(data) {
    //console.info('onCompleteAll'+data);
    console.log(dat);
    dat = [];
  };

  var dat = [];
  uploader.onCompleteItem = function(item, response, status, headers) {
    if (response != "Uploaded Successfully") {
      item.isCancel = true
      item.isSuccess = false
    }
    if( response == "SKU Code doesn't exists") {
      dat.push(item.file.name);
    }
  }

}

angular
  .module('urbanApp')
  .controller('uploadCtrl', ['$scope', 'FileUploader', 'Session', 'Data', uploadCtrl]);
})();