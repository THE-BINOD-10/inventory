'use strict';

angular
  .module('urbanApp')
  .service('colFilters', function($rootScope, $q, $http, $timeout, Session){

  /* column wise filter */
  var vm = this;
  vm.label = '';
  vm.value = '';

  vm.add_search_boxes = function(id) {
    var table = (id)? id+" > thead > tr > th": ".custom-table > thead > tr > th";
    var count = 0;
    $(this).text().length > 0;
    $(table).each( function() {
      var title = $(this).text();
      if (typeof title == "string" && title.length > 0) {
        $(this).empty();
        $(this).html("<span class='inpt-hd'>"+title+"</span><input style='width:100%;' class='inpt-vl hide' type='text' name='search"+count+"'>");
        count++;
      }
    })
    vm.bind_events();
    return true;
  }

  vm.bind_events = function () {
    $('.inpt-hd').click(function(e) {
      e.stopPropagation();
      e.preventDefault();
      $(this).addClass("hide");
      $(this).next().removeClass("hide");
      $(this).next().focus();
    })
    $('.inpt-hd').focus(function(e) {
      e.stopPropagation();
      e.preventDefault();
    })
    $(".inpt-vl").click(function(e) {
      e.stopPropagation();
      e.preventDefault();
    })
    $(".inpt-vl").keyup(function(e) {
      e.stopPropagation();
      e.preventDefault();
      e.stopPropagation();
      vm.label = $(this).attr('name');
      vm.value = $(this).val();
      vm.change_filter_data()
    })
    $(".inpt-vl").blur(function(e) {
      e.stopPropagation();
      e.preventDefault();
      var that = this;
      if ($(this).val().length==0) {
        $(this).addClass("hide");
        $(this).prev().removeClass("hide");
      }
    })
    $(".custom-table > thead > tr > th").each(function(){
      $(this).addClass("rm-blur");
    })
  }

  vm.change_filter_data = function() {
    $rootScope.$broadcast('change_filters_data');
  };

  vm.headers = [];
  vm.search = {};
  vm.download_excel = download_excel;
    function download_excel() {
      var data = {};
      data['excel'] = true;
      if (Session.roles.permissions['central_order_reassigning'] == true && vm.search.datatable == "OrderView") //for 72 networks
      {
        data['Central Order ID'] = 'Central Order ID';data['Batch Number'] = 'Batch Number';data['Batch Date'] = 'Batch Date';
        data['Branch Name'] = 'Branch Name';data['Branch ID'] = 'Branch ID'; ['Loan Proposal ID'] ='Loan Proposal ID';data ['Loan Proposal Code'] ='Loan Proposal Code';data ['Client Code'] ='Client Code';
        data ['Client ID'] ='Client ID';data ['Customer Name'] ='Customer Name';data ['Address1'] ='Address1';data ['Address2'] ='Address2';data ['Landmark'] ='Landmark';
        data ['Village'] ='Village';data ['District'] ='District';data ['State1'] ='State1';data ['Pincode'] ='Pincode';data ['Mobile Number'] ='Mobile Number';data ['Alternative Mobile Number'] ='Alternative Mobile Number';
        data ['SKU Code'] ='SKU Code';data ['Model'] ='Model';data ['Unit Price'] ='Unit Price';data ['CGST'] ='CGST';data ['SGST'] ='SGST';
        data ['IGST'] ='IGST';data ['Total Price'] ='Total Price';data ['Location'] ='Location';
      }
   else{
      angular.forEach(vm.headers, function(value, key) {
        if(value.mData) {
          data[value.mData] = value.sTitle;
         }
       })
     }
      angular.extend(data, vm.search);
      data['search[value]'] = $(".dataTables_filter:visible").find("input").val();
      data = $.param(data);
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http({
               method: 'POST',
               url: Session.url+"results_data/",
               data: data}).success(function(data, status, headers, config) {
           window.location = Session.host+data;
           vm.headers = [];
           vm.search = {};
      });
    }

  //notify
  //vm.msg = "message",
  //vm.type = "success"
  //vm.$layout = 'topRight';
  vm.showNoty = function (msg,type,$layout) {

    if (!type) {
      type = 'success';
    }
    if (!msg) {
      msg = 'Success';
    }
    if (!$layout) {
      $layout = 'topRight';
    }
    noty({
      theme: 'urban-noty',
      text: msg,
      type: type,
      timeout: 3000,
      layout: $layout,
      closeWith: ['button', 'click'],
      animation: {
        open: 'in',
        close: 'out',
        easing: 'swing'
      },
    });
  };

  //print page
  vm.print_data = function(data) {
    data = $(data).clone();
    var print_div= "<div class='print'></div>";
    print_div= $(print_div).html(data);
    print_div = $(print_div).clone();

    $(print_div).find("link").each(function(){
      var data = $(this).attr("href");
      $(this).attr("href", Session.host.slice(0,-1)+data);
    })

    $(print_div).find("script[type='text/javascript']").each(function(){
      var data = $(this).attr("src");
      $(this).attr("src", Session.host.slice(0,-1)+data);
    })

    $(print_div).find(".modal-body").css('max-height', 'none');
    $(print_div).find(".modal-footer").remove();
    print_div = $(print_div).html();

    var mywindow = window.open('', 'PICKLIST', 'height=400,width=600');
    mywindow.document.write('<html><head><title></title>');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="'+Session.host.slice(0,-1)+'/static/css/bootstrap-responsive.css" />');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="vendor/bootstrap/dist/css/bootstrap.min.css" />');
    mywindow.document.write('<link rel="stylesheet" type="text/css" href="'+Session.host.slice(0,-1)+'/static/css/page.css" />');
    mywindow.document.write('<script type="text/javascript" src="vendor/jquery/dist/jquery.min.js"></script>');
    mywindow.document.write('</head><body>');
    mywindow.document.write(print_div);
    mywindow.document.write('</body></html>');

    mywindow.document.close(); // necessary for IE >= 10
    mywindow.focus(); // necessary for IE >= 10

    $timeout(function(){
      mywindow.print();
      mywindow.close();
    }, 3000);

    return true;
  }
})
