'use strict';

function uploadCtrl($scope, FileUploader, Session) {

  var uploader = $scope.uploader = new FileUploader({
    url: Session.url+"upload_images/",
    withCredentials: 'true'
  });

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