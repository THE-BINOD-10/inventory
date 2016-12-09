$(document).ready(function () {

    var zones = [];
    var utilized = [];
    var free = [];

    $('#zone-util tbody tr').find('td:first').each(function() {
           zones.push($(this).text());
        });
    $('#zone-util tbody tr').find('td:first').next().each(function() {
           utilized.push(parseInt($(this).text(), 10));
        });
    $('#zone-util tbody tr').find('td:last').each(function() {
           free.push(parseInt($(this).text(), 10));
        });

    $('#zone-utilization').highcharts({
        chart: {
            type: 'column'
        },
        credits: {
            enabled: false
        },
        title: {
            text: 'Space Utilization'
        },
        xAxis: {
            title: {
                text: 'Zone'
            },
            categories: zones
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
            align: 'right',
            x: -30,
            verticalAlign: 'top',
            y: 25,
            floating: true,
            backgroundColor: (Highcharts.theme && Highcharts.theme.background2) || 'white',
            borderColor: '#CCC',
            borderWidth: 1,
            shadow: false
        },
        tooltip: {
            formatter: function () {
                return '<b>' + this.x + '</b><br/>' +
                    this.series.name + ': ' + this.y + '<br/>' +
                    'Total: ' + this.point.stackTotal;
            }
        },
        plotOptions: {
            column: {
                stacking: 'normal',
                dataLabels: {
                    enabled: true,
                    formatter: function() {
                        if(this.y > 0) {
                           return Math.round((this.percentage*100)/100) + ' %';
                            }
                          },
                    color: (Highcharts.theme && Highcharts.theme.dataLabelsColor) || 'white',
                    style: {
                        textShadow: '0 0 3px black'
                    }
                }
            }
        },
        series: [{
            name: 'Free',
            data: free
        }, {
            name: 'Utilized',
            data: utilized
        }]
    });


    var cate = [];
    var total = [];
    var picked = [];
    var dispatched = [];

    $('#dtr-report tbody tr').find('td:first').each(function() {
           cate.push($(this).text());
        });

    $('#dtr-report tbody tr').find('td:first').next().each(function() {
           total.push(parseInt($(this).text(), 10));
        });
    $('#dtr-report tbody tr').find('td:last').prev().each(function() {
           picked.push(parseInt($(this).text(), 10));
        });
    $('#dtr-report tbody tr').find('td:last').each(function() {
           dispatched.push(parseInt($(this).text(), 10));
        });


    $('#dtr').highcharts({
        chart: {
            type: 'line'
        },
        credits: {
            enabled: false
        },
        title: {
            text: 'Daily Transactions'
        },
        xAxis: {
            categories: cate
        },
        yAxis: {
             min: 0,
            title: {
                text: 'Number of Orders'
            }
        },
        plotOptions: {
            line: {
                dataLabels: {
                    enabled: true
                },
                enableMouseTracking: false
            }
        },
        series: [{
            name: 'Total Orders',
            data: total
        }, {
            name: 'Picked Orders',
            data: picked
        }, {
            name: 'Dispatched Orders',
            data: dispatched
        }]
    });

    var executed = [];
    var progress = [];
    var pending = [];

    executed.push(parseInt($('#putaway-report tbody tr:first').find('td:first').next().text(), 10));
    executed.push(parseInt($('#putaway-report tbody tr:last').find('td:first').next().text(), 10));

    progress.push(parseInt($('#putaway-report tbody tr:first').find('td:last').prev().text(), 10));
    progress.push(parseInt($('#putaway-report tbody tr:last').find('td:last').prev().text(), 10));

    pending.push(parseInt($('#putaway-report tbody tr:first').find('td:last').text(), 10));
    pending.push(parseInt($('#putaway-report tbody tr:last').find('td:last').text(), 10));

    $('#pick-putaway').highcharts({
        chart: {
            type: 'column'
        },
        credits: {
            enabled: false
        },
        colors: ['#8bbc21', '#E6E600', '#d9534f'],
        title: {
            text: 'Pick & Putaway'
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
            data: executed

        }, {
            name: 'In-Progress',
            data: progress

        }, {
            name: 'Pending',
            data: pending

        }]
    });

  var aging_node = $('#inventory-aging tbody')
  var data1 = parseInt(aging_node.find('tr:first').find('td:last').text(), 10);
  var data2 = parseInt(aging_node.find('tr:first').next().find('td:last').text(), 10);
  var data3 = parseInt(aging_node.find('tr:last').find('td:last').text(), 10);

  $('#aging').highcharts({
        chart: {
            type: 'column'
        },
        title: {
            text: 'Inventory Aging'
        },
        credits: {
            enabled: false
        },
        xAxis: {
            title: {
                text: 'Age'
            },
            type: 'category',
            labels: {
                style: {
                    fontSize: '13px',
                    fontFamily: 'Verdana, sans-serif'
                }
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Quantity'
            }
        },
        legend: {
            enabled: false
        },
        series: [{
            name: 'Quantity',
            data: [
                ['3 months old', data1],
                ['3-6 months old', data2],
                ['Older than 6 months', data3],
            ],
            dataLabels: {
                    enabled: true,
                    color: (Highcharts.theme && Highcharts.theme.dataLabelsColor) || 'gray',
                    style: {
                    }
                }
        }]
    });

    var order_executed = parseInt($('#db-track-po tbody tr:first').find('td:first').next().text());
    var order_progress = parseInt($('#db-track-po tbody tr:first').find('td:first').next().next().text());
    var order_pending = parseInt($('#db-track-po tbody tr:first').find('td:last').text());
    var od_url = '/track_orders/'

    $('#db-track-order').highcharts({
            chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: 'Track Orders'
            },
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
                            return Math.round((this.percentage*100)/100) + ' %';
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
            colors: ['#7CB5EC', '#FFBC75','#90ed7d'],
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
                    y: order_pending,
                    url: od_url 
                }, {
                    name: 'In-Progress',
                    y: order_progress,
                    url: od_url
                }, {
                    name: 'Executed',
                    y: order_executed,
                    url: od_url
                }]
            }]
        });

    var executed = parseInt($('#db-track-po tbody tr:last').find('td:first').next().text());
    var progress = parseInt($('#db-track-po tbody tr:last').find('td:first').next().next().text());
    var pending = parseInt($('#db-track-po tbody tr:last').find('td:last').text());
    var po_url = '/track_orders/#purchase-orders'
    $('#db-track-po').highcharts({
            chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: 'Track Purchase Orders'
            },
            credits: {
                enabled: false
            },
            events:{
                  click: function (event, i) {
                     alert(event.point.name);
                  }
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
                            if(this.y > 0)
                            {
                              return Math.round((this.percentage*100)/100) + ' %';
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
            colors: ['#7CB5EC', '#FFBC75','#90ed7d'],
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
                    y: pending,
                    url: po_url,
                }, {
                    name: 'In-Progress',
                    y: progress,
                    url: po_url,
                }, {
                    name: 'Executed',
                    y: executed,
                    url: po_url,
                }]
            }]
        });


    var gaugeOptions = {

        chart: {
            type: 'solidgauge'
        },

        title: null,

        pane: {
            center: ['50%', '85%'],
            size: '140%',
            startAngle: -90,
            endAngle: 90,
            background: {
                backgroundColor: (Highcharts.theme && Highcharts.theme.background2) || '#EEE',
                innerRadius: '60%',
                outerRadius: '100%',
                shape: 'arc'
            }
        },

        tooltip: {
            enabled: false
        },

        // the value axis
        yAxis: {
            stops: [
                [0.1, '#55BF3B'], // green
                [0.5, '#DDDF0D'], // yellow
                [0.9, '#DF5353'] // red
            ],
            lineWidth: 0,
            minorTickInterval: null,
            tickPixelInterval: 400,
            tickWidth: 0,
            title: {
                y: -70
            },
            labels: {
                y: 16
            }
        },

        plotOptions: {
            solidgauge: {
                dataLabels: {
                    y: 5,
                    borderWidth: 0,
                    useHTML: true
                }
            }
        }
    };

    var count = parseInt($("[name=db-pending-order]").attr("min"));
    var max = parseInt($("[name=db-pending-order]").attr("max"));

    // The RPM gauge
    $('#container-rpm').highcharts(Highcharts.merge(gaugeOptions, {
        yAxis: {
            min: 0,
            max: max,
            title: {
                text: 'Total Orders'
            }
        },
        credits: {
            enabled: false
        },
        series: [{
            name: 'RPM',
            data: [count],
            dataLabels: {
                format: '<div style="text-align:center"><span style="font-size:25px;color:' +
                    ((Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black') + '">{y:1f}</span><br/>' +
                       '<span style="font-size:12px;color:silver">Orders</span></div>'
            },
            tooltip: {
                valueSuffix: ' revolutions/min'
            }
        }]

    }));

    var count = parseInt($("[name=db-pending-purchases]").attr("min"));
    var max = parseInt($("[name=db-pending-purchases]").attr("max"));

    // The RPM gauge
    $('#container-pos').highcharts(Highcharts.merge(gaugeOptions, {
        yAxis: {
            min: 0,
            max: max,
            title: {
                text: 'Total POs'
            }
        },
        credits: {
            enabled: false
        },
        series: [{
            name: 'RPM',
            data: [count],
            dataLabels: {
                format: '<div style="text-align:center"><span style="font-size:25px;color:' +
                    ((Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black') + '">{y:1f}</span><br/>' +
                       '<span style="font-size:12px;color:silver">Orders</span></div>'
            },
            tooltip: {
                valueSuffix: ' revolutions/min'
            }
        }]

    }));

    if($("#db-top-selling").length != 0)
    {
      setInterval(function() {
        chart = $('#container-rpm').highcharts();
        if (chart) {
           $.ajax({url: '/get_orders_count/',
                   'success': function(response) {
                   newVal = parseInt(JSON.parse(response).orders);
                   point = chart.series[0].points[0];

                   if (newVal < 0 || newVal > max) {
                       newVal = point.y ;
                    }
                    point.update(newVal);
           
            } });
        }
      }, 10000);
    }

   var sku1 = $('#db-top-selling tbody tr:first').find('td:first').text();
   var sku1_val = parseInt($('#db-top-selling tbody tr:first').find('td:first').next().text());
   var sku2 = $('#db-top-selling tbody tr:eq(1)').find('td:first').text();
   var sku2_val = parseInt($('#db-top-selling tbody tr:eq(1)').find('td:first').next().text());
   var sku3 = $('#db-top-selling tbody tr:eq(2)').find('td:first').text();
   var sku3_val = parseInt($('#db-top-selling tbody tr:eq(2)').find('td:first').next().text());
   var sku4 = $('#db-top-selling tbody tr:eq(3)').find('td:first').text();
   var sku4_val = parseInt($('#db-top-selling tbody tr:eq(3)').find('td:first').next().text());
   var sku5 = $('#db-top-selling tbody tr:eq(4)').find('td:first').text();
   var sku5_val = parseInt($('#db-top-selling tbody tr:eq(4)').find('td:first').next().text());
    $('#db-top-selling').highcharts({
            chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: 'Top Selling SKUs'
            },
            credits: {
                enabled: false
            },
            events:{
                  click: function (event, i) {
                     alert(event.point.name);
                  }
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
            },
            colors: ['#7CB5EC', '#FFBC75','#90ed7d', '#434348', '#8085E9'],
            series: [{
                name: 'Amount',
                colorByPoint: true,
                data: [{
                    name: sku1,
                    y: sku1_val,
                }, {
                    name: sku2,
                    y: sku2_val,
                }, {
                    name: sku3,
                    y: sku3_val,
                }, {
                    name: sku4,
                    y: sku4_val,
                }, {
                    name: sku5,
                    y: sku5_val,
                }]
            }]
        });

  var skus_lis = [];
  var skus_val = [];

  $.each($("#db-top-skus table:first").find("tr"), function(ind, obj){
    skus_lis.push($(obj).find("td:first").text());
    skus_val.push(parseInt($(obj).find("td:first").next().text()))
  });

  max_count = Math.max.apply(null, skus_val)


  if($("#db-top-selling").length != 0)
  {
  var charts = [],
    $containers = $('#trellis td'),
    datasets = [{
        name: 'Top SKUs',
        data: skus_val}];



  $.each(datasets, function(i, dataset) {
    charts.push(new Highcharts.Chart({

        chart: {
            renderTo: $containers[i],
            type: 'bar',
            marginLeft: i === 0 ? 100 : 10
        },

        title: {
            text: dataset.name,
            align: 'left',
            x: i === 0 ? 90 : 0
        },

        credits: {
            enabled: false
        },

        xAxis: {
            categories: skus_lis,
            labels: {
                enabled: i === 0
            }
        },

        yAxis: {
            allowDecimals: false,
            title: {
                text: null
            },
            min: 0,
            max: max_count
        },


        legend: {
            enabled: false
        },

        series: [dataset]

    }));
  });
 }


 $('#dashboard [data-toggle=collapse]').on('click', function(e) { 
    $(this).siblings("form").collapse('hide');
 });

 $('#dashboard #month_dispatch').on('click', function(e) {
    obj_lis = ['Order ID', 'WMS Code', 'Description', 'Location', 'Quantity', 'Picked Quantity', 'Date', 'Time']
    col_lis = []
    var today = new Date();
    var end_date = String(today.getMonth() + 1) + '/' + String(today.getDate()) + '/' + String(today.getFullYear());
    var start_date = String((today.getMonth() - 1) + 1) + '/' + String(today.getDate()) + '/' + String(today.getFullYear());
    data = "excel_name=dispatch_summary&from_date=" + start_date + "&to_date=" + end_date;
    for(i=0;i<(obj_lis.length); i++){
      col_lis.push({data: obj_lis[i]})
    }
    $.ajax({type: 'POST',
    url: '/excel_reports/',
    data: {
            "columns": col_lis,
            "serialize_data": data,

    },
    'success': function(response) {
      window.location = response;
    }

    });
    
 });
    

});
