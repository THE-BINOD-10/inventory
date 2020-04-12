;(function (angular) {
  "use strict";

  angular.module("order", [])
         .component("order", {

           "templateUrl": "/app/order/order.template.html",
           "controller"  : ["$http", "$scope", "urlService", "manageData", "printer", "$location", "$window",
  function ($http, $scope, urlService, manageData, printer, $location, $window) {

    var self = this;
    self.given = urlService.current_order.summary.total_amount;
    self.order_number = "";
    self.print_order = print_order;
    function print_order(order) {
      if(order.length <= 0) {
        return;
      }
      $http.get( urlService.mainUrl+'rest_api/print_order_data/?user='+urlService.userData.parent_id+'&order_id='+order).success(function(data, status, headers, config) {
            if(data.message === "invalid user") {
                $window.location.reload();
            } else if (data == '"No Data Found"') {
              alert('Sku With Zero Quantity Available')
            } else {
                if(data.status == "success") {
                  if(data.data.summary.issue_type === "Pre Order") {
                      printer.print('/app/views/pre_order_print.html', {'data': data.data,
                                                            'user':urlService.userData,
                                                            'print_type': 'DUPLICATE',
                                                            'date':data.data.order_date});
                  } else {
                      for (var i = 0; i < data.data['sku_data'].length; i++) {
                        data.data['sku_data'][i]['cgst'] = (data.data['sku_data'][i]['cgst'] * data.data['sku_data'][i]['quantity']) * data.data['sku_data'][i]['quantity']
                        data.data['sku_data'][i]['sgst'] = (data.data['sku_data'][i]['sgst'] * data.data['sku_data'][i]['quantity']) * data.data['sku_data'][i]['quantity']
                        data.data['sku_data'][i]['igst'] = (data.data['sku_data'][i]['igst'] * data.data['sku_data'][i]['quantity']) * data.data['sku_data'][i]['quantity']
                        data.data['sku_data'][i]['utgst'] = (data.data['sku_data'][i]['utgst'] * data.data['sku_data'][i]['quantity']) * data.data['sku_data'][i]['quantity']
                        data.data['sku_data'][i]['selling_price'] = (data.data['sku_data'][i]['selling_price']/data.data['sku_data'][i]['quantity'])
                        if ((data.data['sku_data'].length-1) == i) {
                          data.data['order_id'] = data.data['inv_order_prefix'] + data.data['order_id']
                          printer.print('/app/views/print.html', {'data': data.data,
                                                          'user':urlService.userData,
                                                          'print_type': 'DUPLICATE',
                                                          'date':data.data.order_date});
                        }
                      }
                 }
                }
            }
        })
    };

  }]
 });
}(window.angular));
