$(document).ready(function(){

  $('body').on("click", '#manage-users .results', function() {
    var data_id = $(this).attr('id');
    var context = this;
    $('#user-toggle').empty();
    
    $.ajax({url: '/get_user_data?data_id=' + data_id,
            'success': function(response) {
                $('#user-toggle').append(response);
                $("#user-toggle").modal();
                $(".selectpicker").selectpicker();
            }});
            
  });

  $("#add_group").on("click",function() {
   $('#user-toggle').empty();
   $.ajax({url: '/add_group_data',
            'success': function(response) {
                $('#user-toggle').append(response);
               $('#user-toggle').modal();
               $("#locationModal").modal();
               $(".selectpicker").selectpicker();
            }});
    });

  $("#add_user").on("click",function() {
   $('#user-toggle').empty();
   $.ajax({url: '/add_user_data',
            'success': function(response) {
                $('#user-toggle').append(response);
               $('#user-toggle').modal();
               $("#locationModal").modal();

            }});
    });

  $("body").on("submit","#add_group",function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    data = {}
    selected = [];
    var nodes = $(".selectpicker").find("option:selected")
    for(i=0; i<nodes.length; i++) {
      selected.push($(nodes[i]).val())
    }
     data['selected'] = selected.join();
     data['name'] = $(this).parent().find("input[name=group]").val();

    if(data.name)
    {
        $.ajax({url: '/add_group/',
                method: 'POST',
                data: data,
                'success': function(response) {
          $("body").find(".insert-status").html(response).show();
          $("#sortingTable").dataTable().fnReloadAjax();
        }});
    }
    $('.loading').addClass('display-none');
  });


  $("body").on("submit","#update_user",function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    selected = [];
    var nodes = $(".selectpicker").find("option:selected")
    for(i=0; i<nodes.length; i++) {
      selected.push($(nodes[i]).val())
    }
     selected_list = selected.join();
     values = $(this).serialize(); 
     data = values + "&perms=" + selected_list
        $.ajax({url: '/update_user?' + data,
                'success': function(response) {
          $("body").find(".insert-status").html(response).show();
          $("#sortingTable").dataTable().fnReloadAjax();
          $('.loading').addClass('display-none');
        }});
    $('.loading').addClass('display-none');
  });


  $("body").on("submit","#add_user",function( e ) {
    e.preventDefault();
    $('.loading').removeClass('display-none');
    var values = $(this).serialize();
    var this_data = $(this);
    username = $("body").find("[name=username]").val()
    if(username)
    {
        $.ajax({url: '/add_user?' + values,
                'success': function(response) {
          this_data.find(".insert-status").html(response).show();
          $("#sortingTable").dataTable().fnReloadAjax();
          $('.loading').addClass('display-none');
        }});
    }
  });



});

