'use strict';

function uploadCtrl($scope, FileUploader, Session) {

  $scope.categories = ['SKU', 'Category', 'Brand'];
  $scope.category_type = $scope.categories[0];
  var files_type = '';

  var uploader = $scope.uploader = new FileUploader({
    url: Session.url+"upload_images/",
    // formData: [
    //     { "files_type": $scope.category_type },
    // ],
    withCredentials: 'true'
  });

  files_type = [{'files_type': $scope.category_type}];
  uploader.formData = files_type;
  // uploader.formData = [{'files_type': $scope.category_type}];

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
  .controller('uploadCtrl', ['$scope', 'FileUploader', 'Session', uploadCtrl]);
