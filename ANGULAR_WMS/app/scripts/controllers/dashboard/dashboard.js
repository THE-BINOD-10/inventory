'use strict';

function dashboardCtrl($scope, $state, $http, $interval, COLORS, Session, $timeout, Service) {

  $scope.session = Session;

  // purchase order data
  $scope.po_data = [{key: 'pending_confirmation', value: 'PENDING CONFIRMATION'},
                    {key: 'yet_to_receive', value: 'YET TO RECEIVE'},
                    {key: 'pending_month', value: 'PENDING >1 MONTH'},
                    {key: 'received_today', value: 'RECEIVED TODAY'},
                    {key: 'putaway_pending', value: 'PUTAWAY PENDING'}
                   ]
  // quick links data
  $scope.quick_links =[
                       {name: 'Receipt', url: '#/reports/GoodsReceiptNote', title: 'Good Receipt Note Report', color: 'btn-success'},
                       {name: 'Stock Detail', url: '#/stockLocator/StockDetail', title: 'Stock Detail Page', color: 'btn-danger'},
                       {name: 'Stock Reports', url: Session.url+'daily_stock_report/', title: 'Daily Stock Report Download',
                        color: 'btn-warning'},
                       {name: 'Uploads', url: '#/uploads', title: 'Upload Page', color: 'btn-primary'}
                      ]

  //dash display leve
  $scope.display_level = Session.roles.permissions.dashboard_order_level;
  $scope.display_level = ($scope.display_level == undefined)? false: $scope.display_level;
  $scope.switches = function() {
    Service.apiCall("switches/?dashboard_order_level="+$scope.display_level).then(function(data){
      if(data.message) {
        $scope.update_dashboard();
      }
    });
    Session.roles.permissions["dashboard_order_level"] = $scope.display_level;
  }

  //top sku graph
  function render_top_skus(graph_d) {

    var categories = [];
    var data = [];
    graph_d = (graph_d.length > 5)? graph_d.slice(0,5) : graph_d;
    for (var i=0; i<graph_d.length; i++) {
      categories.push(graph_d[i].sku__wms_code);
      data.push(Number(graph_d[i].quantity__sum.toFixed(2)));
    }

    $('#top-skus').highcharts({
        chart: {
            type: 'bar'
        },
        title: {
            text: ''
        },
        subtitle: {
            text: ''
        },
        xAxis: {
            categories: categories,
            title: {
                text: null
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: '',
                align: 'high'
            },
            labels: {
                overflow: 'justify'
            }
        },
        colors: ['#0099cc'],
        tooltip: {
            valueSuffix: ''
        },
        plotOptions: {
            bar: {
                dataLabels: {
                    enabled: true
                }
            }
        },
        legend: {
            align: 'center',
            x: 0,
            verticalAlign: 'bottom',
            y: 15
        },
        credits: {
            enabled: false
        },
        series: [{
            name: 'Top SKUS',
            showInLegend: false,
            data: data
        }]
    });
  }

  //space utilization graph
  function space_utilization(graph_d) {

    Highcharts.chart('space-utilization', {

      chart: {
            type: 'column'
        },
        credits: {
            enabled: false
        },
        title: {
            text: ''
        },
        colors: ['#2ecc71', '#d96557','#90ed7d'],
        xAxis: {
            categories: graph_d.zones
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Total Quantity'
            },
            stackLabels: {
                enabled: true,
                style: {
                    fontWeight: 'bold',
                    color: (Highcharts.theme && Highcharts.theme.textColor) || 'gray'
                }
            }
        },
        legend: {
            align: 'center',
            x: 0,
            verticalAlign: 'bottom',
            y: 15
        },
        tooltip: {
            headerFormat: '<span style="font-size:10px"></span><table>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        series: [{
            name: 'Free',
            data: graph_d.Free
        }, {
            name: 'Utilized',
            data: graph_d.Utilized
        }]
    });
  }

  //pie chart
  function pie_donut(data) {

    $("#"+data.div).highcharts({
        chart: {
          margin: [0, 0, 0, 0],
          spacingTop: 0,
          spacingBottom: 0,
          spacingLeft: 0,
          spacingRight: 0
        },
        title: {
            text: null
        },
        tooltip: {
            enabled: false,
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        credits: {
            enabled: false
        },
        colors:["#d96557", "#ffc65d", "#2ECC71"],
        plotOptions: {
            pie: {
                size:'120%',
                dataLabels: {
                    enabled: true,
                    formatter: function() {
                        console.log(this);
                        return this.y ;
                    },
                    distance: 10,
                    style: {
                        fontWeight: 'bold',
                        color: 'black',
                    }
                },
                startAngle: -90,
                endAngle: 90,
                center: ['50%', '70%'],
                showInLegend: true
            }
        },
        series: [{
            type: 'pie',
            name: 'Browser share',
            innerSize: '60%',
            data: data.data
        }]
    });
  }

  $scope.options2 = {
    renderer: 'area',
    height: 200,
    padding: {
      top: 2, left: 0, right: 0, bottom: 0
    },
    interpolation: 'cardinal'
  };
  $scope.features5 = {

    hover: {
      xFormatter: function (x) {
        return new Date(x * 1000).toString();
      },
      yFormatter: function (y) {
        return Math.round(y);
      }
    }
  };

  var seriesData = [[], []];

  $scope.series = [{
    color: COLORS.primary,
    data: seriesData[0],
    name: 'PICKED'
    }, {
    color: COLORS.bodyBg,
    data: seriesData[1],
    name: 'RECEIVED'
    }];

  $scope.interval = undefined;
  $scope.updateInterval = function() {

    if(angular.isDefined($scope.interval)) {

      $interval.cancel($scope.interval);
    }

    $scope.interval = $interval(function() {
      console.log(new Date(), $scope.display_level);
      if($state.current.name == "app.dashboard") {
        $scope.update_dashboard();
      }
    }, 60000);
  }

  $scope.d_data = {}
  $scope.update_dashboard = function() {
    if(angular.isDefined($scope.interval)) {

      $interval.cancel($scope.interval);
    }
    $scope.loadingData = true;
    Service.apiCall('dashboard/?display_order_level='+$scope.display_level).then(function(data) {
     if(data.message) {
      data = data.data;
      angular.copy(data, $scope.d_data);
      render_top_skus($scope.d_data.top_inventory);
      space_utilization($scope.d_data.locations_count);
      console.log(data);
      update_graphs();

      $scope.updateInterval();
     }
     $scope.loadingData = false;
    })
  }
  $scope.update_dashboard();


  function update_graphs() {

    var pick_data = {div:"picking", data: [['Picklist not generated',$scope.d_data.picking['Picklist not generated']],
                                           ['In-progress', $scope.d_data.picking['In-progres']],
                                           ['Picked', $scope.d_data.picking['Picked']]]}
    pie_donut(pick_data);

    var putaway_data = {div:"putaway", data: [['Putaway not generated',$scope.d_data.putaway['Putaway not generated']],
                                           ['In-progress', $scope.d_data.putaway['In-progress']]]}

    pie_donut(putaway_data);

    $timeout(function () {
      $(".sales").find(".pieLabel > div > b").each(function(){
        var data = $(this).text(); 
        if(data.indexOf("%") == -1) {
          $(this).text(data+"%")
        }
      })
    }, 500);

    seriesData = [[],[]];
    var index = 1;
    angular.forEach($scope.d_data.orders_stats, function(stat, date) {
      seriesData[0].push({x:date, y:stat.Picked});
      seriesData[1].push({x:date, y:stat.Received});
      index = index + 1;
    });

    changeDateTimeToTimestamp(seriesData[0]);
    changeDateTimeToTimestamp(seriesData[1]);
    $scope.series[0].data = seriesData[0];
    $scope.series[1].data = seriesData[1];
  }

  var changeDateTimeToTimestamp = function(data){
    for(var key in data){
        data[key].x = new Date(data[key].x).getTime() / 1000;
    }
    return data;
  }

  var timezone = jstz.determine();
  var tz = timezone.name()
  $http.get(Session.url+'set_timezone/?tz=' + tz, {withCredential:  true}).success(function(data){
    console.log("time zone updated");
  });
}

app =angular.module('urbanApp')
app.controller('dashboardCtrl', ['$scope', '$state', '$http','$interval', 'COLORS', 'Session', '$timeout', 'Service', dashboardCtrl]);
