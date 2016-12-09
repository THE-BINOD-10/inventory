$(document).ready(function() {
var fi = $('#fileupload'); //file input 
//initialize blueimp fileupload plugin
var process_url = 'http://path/to/file/upload.php'; //PHP script

$('#fileupload').fileupload({
    dataType: 'json',
    add: function (e, data) {            
        $("#up_btn").off('click').on('click', function () {
            data.submit();
        });
    },
});

var progressBar = $('<div/>').addClass('progress').append($('<div/>').addClass('progress-bar')); //create progress bar
var uploadButton = $('<button/>').addClass('button btn-blue btn btn-primary upload').text('Upload');    //create upload button

up_files = []

fi.on('fileuploadadd', function (e, data) {
        var node = $('<tr/>').addClass('template-upload fade in');
        var parent_node = $(".file-wrapper");
        data.context = node.appendTo('#files'); //create new DIV with "file-wrapper" class
        $.each(data.files, function (index, file){  //loop though each file
        var fname = file.name;
        var re = /(\.jpg|\.jpeg|\.bmp|\.gif|\.png)$/i;
        if(!re.exec(fname))
        {
            alert("File extension not supported!");
            $(this).val('');
            return true;
        }
        var removeBtn  = $('<button/>').addClass('button btn-red remove btn btn-warning').html('<i class="glyphicon glyphicon-ban-circle"></i>Remove'); //create new remove button
        var file_size = (file.size / (1024*1024)).toFixed(2) + " MB"
        var html_data = '<td><span><img src="' + URL.createObjectURL(data.files[0]) + '" width="51" height="80" style="float: left;"/></span></td><td><span>' + file.name + '</span></td><td><p class="size">' + file_size + '</p>'
        html_data += '<div class="progress progress-striped active" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="progress-bar progress-bar-success" style="width:0%;"></div></div></td><td>'
        html_data += removeBtn.wrap('<div>').parent().html() + '</td><td>'
        html_data += uploadButton.clone(true).data(data).wrap('<div>').parent().html() + '</td>'
        up_files.unshift(file);

        var file_txt = node.append(html_data);
        if (!index){
            parent_node.prepend(file_txt);
        }
        
    });
});


$.fn.start_upload = function(file_name, this_data){
    file_names = []
    file_names.push(file_name)
    formData = new FormData();
    $.each(file_names, function(i, file) {
        formData.append('files-' + i, file);
    });

    $.ajax({url: '/upload_images/',
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            'success': function(response) {
              if(response == 'Uploaded Successfully'){
                     this_data.prop('disabled', true);
                     this_data.parent().parent().find(".progress-bar-success").attr("style", "width:100%");
                     setTimeout(function() { 
                         $('.progress-striped.active').remove();
                         this_data.text(response);
                     }, 2000);
              }
              else {
                  this_data.parent().html('<div class="insert-status" style="margin-top:8px;">' + response + '</div>');
              }
            }});
}

$("body").on('click', 'table[role=presentation] .upload', function () { //button click function]
    var this_data = $(this);
    file_name = up_files[$(".file-wrapper tbody").children().index($(this).closest('tr'))]
    $.fn.start_upload(file_name, this_data);
});

  $("body").on('click', 'table[role=presentation] .remove', function(e, data){ //remove button function
            var ind = $("table tbody").children().index($(this).parent().parent());
            up_files.pop(ind);
            $(this).parent().parent().remove(); //remove file's wrapper to remove queued file
        });

  $("body").on('click', '#image-uploads #upload-all', function () {
    for(i=0; i<up_files.length; i++){
      this_data = $("table").find("tr:eq(" + i + ")" ).find(".upload");
      $.fn.start_upload(up_files[i], this_data);
    }
  });

});
