'use strict';

function dashboardCtrl($scope, $http, $interval, COLORS, Session) {

  $scope.pending_orders;
  $scope.pending_pos;
  $scope.completed_orders;
  $scope.space_utilization;
  $scope.pick_and_put;
  $scope.daily_transactions;
  $scope.track_order;
  $scope.track_po;
  $scope.top_skus_cat;
  $scope.top_skus_data;
  $scope.links = ['Raise PO', 'Orders', 'Back Orders', 'Report Issues', 'Stock Detail', 'Stock Report']//'Monthly Dispatch', 'Summary']

   $http.get(Session.url+'dashboard/').success(function(data, status, headers, config) {

     console.log(data);
     $scope.pending_orders = data.orders_count;
     $scope.pending_pos = data.putaway.pending;
     $scope.completed_orders = data.picking.executed;
     $scope.space_utilization = data.location_count;
     $scope.pick_and_put = {picking:data.picking,putaway:data.putaway}
     $scope.daily_transactions = data.weekly_tr;
     $scope.top_skus_cat = data.top_skus_cat;
     $scope.top_skus_data = data.top_skus_data;
     space_utilization(data.locations_count);
     pick_and_put(data.picking, data.putaway);
     $scope.track_order = data.pie_picking;
     $scope.track_po = data.pie_putaway;
     daily_transactions(data.daily_trans);
     pie();
     top_selling_skus(data.top_selling_skus_data);
     render_top_skus(data.top_skus_data);
     $scope.orders = data.orders_count;
     $scope.delightScore = {'percentage':data.orders_count*(100/data.max_order), 'orders':data.orders_count, 'max':data.max_order};
     $scope.max = data.max_order;
     var g = new JustGage({
      id: "gauge",
      value: data.orders_count,
      min: 0,
      max: data.max_order,
      title: "Total Orders",
      label: "Orders",
      levelColors: ['#CE1B21', '#D0532A', '#FFC414', '#d96557']
      });
      var g = new JustGage({
      id: "gauge2",
      value: data.pending_orders,
      min: 0,
      title: "Total PO's",
      max: data.max_purchase,
      label: "Orders",
      levelColors: ['#CE1B21', '#D0532A', '#FFC414', '#d96557']
      });
   }) 

  $scope.category;
  $scope.alter_graph = function(){

    return $scope.category ? render_top_skus($scope.top_skus_cat) : render_top_skus($scope.top_skus_data);
  }
  var perShapeGradient = {
            x1: 0,
            y1: 0,
            x2: 1,
            y2: 0
        };

  function space_utilization(data) {

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
            categories: data.zones
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
            data: data.Free
        }, {
            name: 'Utilized',
            data: data.Utilized
        }]
    });
  }

  function pick_and_put(pick, put) {

    Highcharts.chart('pick-and-putaway', { 
      chart: {
            type: 'column'
        },
        credits: {
            enabled: false
        },
        colors: ['#2ecc71', '#2196f3','#d96557'],
        title: {
            text: ''
        },
        xAxis: {
            categories: [
                'Pick',
                'Put-away'
            ],
            crosshair: true
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Number Of Orders'
            }
        },
        tooltip: {
            headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        plotOptions: {
            column: {
                pointPadding: 0.2,
                borderWidth: 0
            }
        },
        series: [{
            name: 'Executed',
            data: [pick.executed, put.executed]

        }, {
            name: 'In-Progress',
            data: [pick.progress, put.progress]

        }, {
            name: 'Pending',
            data: [pick.pending, put.pending]

        }]  
    });
  }

  var od_url = '/track_orders/';
  function track_orders(data, container) {

    Highcharts.chart(container, {
      chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: ''
            },
            colors: ['#fe6672', '#FFFF33', '#2ecc71'],//['#d96557', '#2196f3','#2ecc71'],//['#f2784b', '#f3c200','#8E44AD'],
            credits: {
              enabled: false
            },
            tooltip: {
            },
            plotOptions: {
                pie: {
                    allowPointSelect: true,
                    cursor: 'pointer',
                    dataLabels: {
                        enabled: false
                    },
                    showInLegend: true
                },
                series: {
                    dataLabels: {
                        enabled: true,
                        //format: '<b>{point.name}</b>: {point.percentage:.1f} %',
                        formatter: function() {
                            if(this.y > 0) {
                            return Math.round(this.percentage*100)/100 + ' %';
                            }
                        },
                        distance: -50,

                        style: {
                            textShadow: '0 0 0px 0px'
                        },
                        color:'black'
                    }
                }
            },
            series: [{
                name: 'Orders',
                colorByPoint: true,
                point: {
                       events: {
                           click: function(e) {
                                 location.href = e.point.url;
                                 e.preventDefault();
                      }
                  }
                },
                data: [{
                    name: 'Pending Orders',
                    y: data.pending,
                    url: od_url 
                }, {
                    name: 'In-Progress',
                    y: data.inprogress,
                    url: od_url
                }, {
                    name: 'Executed',
                    y: data.executed,
                    url: od_url
                }]
            }]
    });
  };

  function daily_transactions(data) {

    Highcharts.chart('dtr', { 
      chart: {
            type: 'line'
        },
        credits: {
            enabled: false
        },
        title: {
            text: ''
        },
        xAxis: {
            categories: data.cate
        },
        yAxis: {
             min: 0,
            title: {
                text: 'Number of Orders'
            }
        },
        colors: ['#7CB5EC', '#FFBC75','#90ed7d'],
        plotOptions: {
            line: {
                dataLabels: {
                    enabled: true
                },
                enableMouseTracking: false
            }
        },
        series: [{
            name: 'Total',
            data: data.orders
        }, {
            name: 'Picked',
            data: data.picked
        }, {
            name: 'Dispatched',
            data: data.dispatched
        }] 
    }) 
  }

  function top_selling_skus(data) {

    $scope.top_selling_options = {
    series: {
      pie: {   
        show: true,
        innerRadius: 0.5,
        stroke: {
          width: 2
        },
        label: {
          show: true,
        }
      }
    },
    legend: {
      show: false
    },
    }

    $scope.top_selling_data = [{
      data: 20,
      color: COLORS.danger,
      label: data[0].sku
        },
    {
      data: data[1].value,
      color: COLORS.success,
      label: data[1].sku
        },
    {
      data: data[2].value,
      color: COLORS.warning,
      label:data[2].sku
        }, 
    {
      data: data[3].value,
      color: COLORS.warning,
      label:data[3].sku
        },
    {
      data: data[4].value,
      color: COLORS.warning,
      label: data[4].sku
    }];
  }

  function pie() {
  $scope.doughnutOptions1 = {
    series: {
      pie: {
        show: true,
        innerRadius: 0.5,
        stroke: {
          width: 2
        },
        label: {
          show: true,
        }
      }
    },
    legend: {
      show: false
    },
  }
  $scope.doughnutData1 = [{
      data: $scope.track_order.pending,
      color: COLORS.danger,
      label: 'Pending'
        },
    {
      data: $scope.track_order.executed,
      color: COLORS.success,
      label: 'Executed'
        },
    {
      data: $scope.track_order.inprogress,
      color: COLORS.warning,
      label: 'In Progress'
    }];
  
  $scope.doughnutData2 = [{
      data: $scope.track_po.pending,
      color: COLORS.danger,
      label: 'Pending'
        },
    { 
      data: $scope.track_po.executed,
      color: COLORS.success,
      label: 'Executed'
        },
    { 
      data: $scope.track_po.inprogress,
      color: COLORS.warning,
      label: 'In Progress'
    }];
    }

  $scope.config2 = {
        options: {
            chart: {
                type: 'solidgauge'
            },
            pane: {
                center: ['50%', '55%'],
                size: '100%',
                startAngle: -90,
                endAngle: 90,
                background: {
                    backgroundColor:'#EEE',
                    innerRadius: '60%',
                    outerRadius: '100%',
                    shape: 'arc'
                }
            },
            solidgauge: {
                dataLabels: {
                    y: -40,
                    borderWidth: 0
                }
            }
        },
        series: [{
            data: [0],
            dataLabels: {
                        format: '<div style="text-align:center"><span style="font-size:25px;color:black">{y}</span><br/>' +
                        '<span style="font-size:12px;color:silver">orders</span></div>'
                }
        }],
        title: {
            text: '',
            y: 50
        },
        yAxis: {
            currentMin: 0,
            currentMax: 0,
            title: {
                y: 140
            },
                        stops: [
                [0.1, '#DF5353'], // red
                        [0.5, '#DDDF0D'], // yellow
                        [0.9, '#55BF3B'] // green
                        ],
                        lineWidth: 0,
            tickInterval: 20,
            tickPixelInterval: 400,
            tickWidth: 0,
            labels: {
                y: 15
            }
        },
        exporting:false,
        credits: false,
        loading: false
    };

  function render_top_skus(data) {

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
            categories: data['labels'],
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
        colors: ['#2196F3'],
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
            data: data['data']
        }]
    });
  }
}

app =angular.module('urbanApp')
app.controller('dashboardCtrl', ['$scope', '$http','$interval', 'COLORS', 'Session', dashboardCtrl]);
