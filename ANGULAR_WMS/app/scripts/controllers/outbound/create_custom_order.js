'use strict';

function CreateCustomOrder($scope, $http, $state, Session, colFilters, Service, $modal, Data, $timeout) {

  var vm = this;
  vm.customData = {};
  vm.service = Service;

  vm.products = ['T Shirts', 'Sweatshirts'];
  vm.product = vm.products[0];

  vm.product_types = {
    'T Shirts': {
      'categories': ['ROUND NECK', 'V NECK', 'CHINESE COLLAR', 'POLO', 'HENLEY'],
      'fabrics': ["SCOTT SAPPHIRE", "CRACKLE", "SULPHUR DRYFIT", "SULPHUR COTTON", "GREEN POLO", "LACOSTE", "BIOWASH", "HONEY COMB", "BUTTER HK", "SUPREME", "SPARK", "6 DEGREE", "SPRINT", "SCOTT YOUNG", "AWG DRYFIT", "SUPER POLY", "GRINDLE", "SLUB", "INNER COTTON"],
      'colors': ["RED", "BLACK", "GREY", "NAVY BLUE", "YELLOW", "ROYAL BLUE", "TURQUOISE GREEN", "TURQUOISE BLUE", "ELECTRIC GREEN", "ELECTRIC BLUE", "APPLE GREEN", "WHITE MELANGE", "WHITE", "BOTTLE GREEN", "PURPLE", "MILITARY GREEN", "ICE BLUE", "COFFEE BROWN", "MAROON", "BEIGE", "CRÈME", "CHARCOAL GREY", "INDIAN BLUE", "GOLDEN YELLOW", "LEMON YELLOW", "SKY BLUE", "PINK", "ORANGE", "MAGENTA", "PISTA GREEN", "DARK GREY", "ASH GREY", "MUSTARD", "HP BLUE", "DENIM BLUE", "GREY MELANGE", "CHARCOAL MELANGE", "GREEN MELANGE", "BLUE MELANGE", "PINK MELANGE"],
      'sleeve': ['Half Sleeve', 'Full Sleeve', '3/4 Sleeves', 'Sleeve Less'],
      'pockets': ['U-pocket', 'V-pocket'],
      'ROUND NECK': {
        'fabric': true,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': false,
        'neck_tape': true,
        'bottom': true,
        'slit_type': true,
        'label': true,
      },

      'V NECK': {
        'fabric': true,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': true,
        'neck_tape': true,
        'bottom': true,
        'slit_type': true,
        'label': true,
      },

      'CHINESE COLLAR': {
        'fabric': true,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': true,
        'print_embroidery': true,
        'collar_tape': false,
        'neck_tape': true,
        'bottom': true,
        'slit_type': true,
        'label': true,
      },

      'POLO': {
        'fabric': true,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': true,
        'print_embroidery': true,
        'collar_tape': true,
        'neck_tape': true,
        'bottom': true,
        'slit_type': true,
        'label': true,
      },

      'HENLEY': {
        'fabric': true,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': true,
        'neck_tape': true,
        'bottom': true,
        'slit_type': true,
        'label': true,
      },

      'DEFAULT': {
        'fabric': true,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': true,
        'neck_tape': true,
        'bottom': true,
        'slit_type': true,
        'label': true,
      },
    },

    'Sweatshirts': {
      'categories': ['300 GSM', '400 GSM', 'HIGH NECK (ALWAYS ZIP)', 'COLLAR NECK', 'CHINESE NECK'],
      'fabrics': ["SCOTT SAPPHIRE", "CRACKLE", "SULPHUR DRYFIT", "SULPHUR COTTON", "GREEN POLO", "LACOSTE", "BIOWASH", "HONEY COMB", "BUTTER HK", "SUPREME", "SPARK", "6 DEGREE", "SPRINT", "SCOTT YOUNG", "AWG DRYFIT", "SUPER POLY", "GRINDLE", "SLUB", "INNER COTTON"],
      'colors': ["BLACK", "NAVY BLUE", "CHARCOAL", "GREY", "ROYAL BLUE", "CHARCOAL MELANGE", "BLUE MELANGE", "PINK MELANGE", "ROYAL BLUE MELANGE"],
      'sleeve': ['Full Sleeve', 'Sleeveless'],
      'pockets': ['KANGAROO', 'CUT POCKET'],
      '300 GSM': {
        'fabric': false,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': false,
        'neck_tape': true,
        'bottom': false,
        'slit_type': false,
        'label': true,
      },
      '400 GSM': {
        'fabric': false,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': false,
        'neck_tape': true,
        'bottom': false,
        'slit_type': false,
        'label': true,
      },
      'HIGH NECK (ALWAYS ZIP)': {
        'fabric': false,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': true,
        'neck_tape': true,
        'bottom': false,
        'slit_type': false,
        'label': true,
      },
      'COLLAR NECK': {
        'fabric': false,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': true,
        'neck_tape': true,
        'bottom': false,
        'slit_type': false,
        'label': true,
      },
      'CHINESE NECK': {
        'fabric': false,
        'body_color': true,
        'design': true,
        'piping': true,
        'sleeve': true,
        'pocket': true,
        'placket': false,
        'print_embroidery': true,
        'collar_tape': true,
        'neck_tape': true,
        'bottom': false,
        'slit_type': false,
        'label': true,
      },
    }
  }

  vm.emptyData = {

    alteration: false,
    styles: [],
    style: "",
    fabric : {
      fabrics: {fabric1: "", fabric2: "", fabric3: "", fabric4: ""},
      fabricOptions: ["100% Cotton", "none"],
      fabric: true,
    },
    styleData: [],
    colorData: ["red", "green", "yellow"],
    bodyStyle: {},
    colors: ["red", "green", "yellow"],
    design: {
              designType: true,
              place: {front_design: "plain", back_design: "plain", front_color: "", back_color: ""},
            },
    piping: {piping: false, piping_design: "regular",
              reglanPiping: {piping: false, color: ''},
              shoulderPiping: {piping: false, color: ''}
            },
    sleeve: {sleeve: 'Half Sleeve', sleeves: ['Half Sleeve', 'Full Sleeve', '3/4 Sleeves', 'Sleeve Less'],
             colorTypes: ['Choose Colour', 'Body Colour'], colorType: 'Body Colour'},
    pocket: {pocketDesign: "U-pocket",
             pockets: ['U-pocket', 'V-pocket'],
             pocket: false
            },
    placket: {placketDesign: "", designs: ["V Style", "Zip", "Rib"],
              button: false, placketType: true
             },

    printEmbroidery: false,
    embroidery: {attachments: ["Chest", "Back", "Right Sleeve", "Left Sleeve", "Chest Center", "Chest Pocket"],
                 places: {},
                 placeImgs: {},
                 singleEmbroidery: true
                },
    print: {
            print: false,
            printOptions: ['Screen', 'Sticker/Digital', 'Sublimation'],
            printOption: 'Screen',
            singlePrint: true,
            places: {},
            placeImgs: {}
           },

    collarTip: {
               collarTip: false,
               collarRibs: ["Single", "Double"],
               collarRib: "Single",
               color: ''
              },

    neckType: {type: 'Self', types: ['Self', 'Satin']},
    bottom: {bottom: 'Straight', bottoms: ['Straight', 'Round']},

    slit: {slitTypes: ["No Slit", "Slit Tap", "Floding Tip"],
           slitType: "No Slit",
           bottom: false,
           bottomColor: '',
          },

    label: {label: 'Only Size', labels: ['Only Size', 'Neck Label']},

    sizes: {"Men": {
                    "S":38, "M": 40, "L": 42, "XL": 44, "2XL": 46, "3XL": 48, "4XL": 50
                   },
            "Women": {
                      "S":34, "M": 36, "L": 38, "XL": 40, "2XL": 42, "3XL": 26, "4XL": 48
                     },
            "Kids": {
                     "S":22, "M": 24, "L": 26, "XL": 28, "2XL": 30, "3XL": 32, "4XL": 34
                    }
           },
    sizeValues: { "Men": {}, "Women": {}, "Kids": {}},
    sizeTotals: {},
    sizeEnable: { "Men": false, "Women": false, "Kids": false}
  }

  angular.copy(vm.emptyData, vm.customData);


  vm.styles_loading = false;
  vm.getCustomStyles = function(category) {

    if(!vm.styles_loading) {

      vm.styles_loading = true;
    } else {

      return false;
    }
    vm.styles_loading = true;
    vm.customData.styleData = [];
    var send = {sub_category: category}
    Service.apiCall("get_sub_category_styles/", "GET", send).then(function(data){
      if(data.message) {
        console.log(data.data);
        if (data.data.message != 'Success') {
          console.log(data.data.message)
          return false;
        }
        vm.customData.styleData = data.data.data;
      }
      vm.styles_loading = false;
    })
  }

  vm.styleChange = function(style) {

    vm.customData.style = style;
    if (vm.product_types[vm.product][vm.customData.style]) {
      vm.style_pro = vm.product_types[vm.product][vm.customData.style];
    }  else {
      vm.style_pro = vm.product_types[vm.product]['DEFAULT'];
    }
    vm.customData.fabric.fabricOptions = vm.product_types[vm.product].fabrics;
    vm.customData.fabric.fabrics.fabric1 = vm.customData.fabric.fabricOptions[0];
    vm.customData.colorData = vm.product_types[vm.product].colors;
    //vm.getCustomStyles(vm.customData.style);
  }

  vm.productChange = function(product) {

    vm.product = product;
    vm.getCategories();
  }

  vm.getCategories = function() {

    //Service.apiCall("get_sku_categories/").then(function(data){

    //  if(data.message) {

    //    if(data.data.categories.length > 0) {
          vm.customData.styles = [];
          vm.customData.style = "";
          vm.customData.pocket.pockets = [];
          vm.customData.pocket.pocketDesign = "";
          $timeout(function() {

            vm.customData.styles = vm.product_types[vm.product]['categories']; //data.data.sub_categories;
            vm.customData.style = vm.customData.styles[0];
            vm.styleChange(vm.customData.style);
            vm.customData.pocket.pockets = vm.product_types[vm.product]['pockets'];
            vm.customData.pocket.pocketDesign = vm.customData.pocket.pockets[0];
          }, 500);
          vm.customData.sleeve.sleeves = vm.product_types[vm.product]['sleeve'];
          vm.customData.sleeve.sleeve = vm.product_types[vm.product]['sleeve'][0];
          //vm.getCustomStyles(vm.customData.style);
    //    } else {

    //      console.log("Categories empty");
    //    }
    //  }
    //})
  }

  vm.getCategories();

  vm.changed = function(data) {

    console.log(data)
  }

  vm.fabricChanged = function(option) {

    if (option) {

       vm.customData.fabric.fabrics.fabric2 = "none";
       vm.customData.fabric.fabrics.fabric3 = "none";
       vm.customData.fabric.fabrics.fabric4 = "none";
    }
  }

  vm.selectBodyStyle = function(style) {

    vm.customData.bodyStyle = style;
    console.log(style);
  }

  vm.pipingChanged = function(option) {

    console.log(option)
  }

  vm.pipingDesignChange = function(option) {
    vm.customData.piping.piping_design = option;
  }

  vm.sleeveColorChange = function(option) {
    vm.customData.sleeve.colorType = option;
  }

  vm.pocketChange = function(option) {

    vm.customData.pocket.pocketDesign = option;
  }

  vm.placketChange = function(option) {

    vm.customData.placket.placketDesign = option;
  }

  vm.calTotals = function(size, name) {

   var total = 0
   angular.forEach(vm.customData.sizeValues[size], function(value, key) {

     if(value) {
       total += value
     }
   })

   vm.customData.sizeTotals[size] = total;
  }

  vm.sizeCheck = function(size) {

    if(vm.customData.sizeEnable[size]) {
      vm.customData.sizeEnable[size] = false;
    } else {
      vm.customData.sizeEnable[size] = true;
    }
  }

  vm.showPreview = function() {
    var mod_data = {};
    angular.copy(vm.customData, mod_data);
    mod_data['style_pro'] = vm.style_pro;
    var modalInstance = $modal.open({
            templateUrl: 'views/outbound/toggle/customOrderDetails.html',
            controller: 'customOrderDetailsPreview',
            controllerAs: 'pop',
            size: 'lg',
            backdrop: 'static',
            keyboard: false,
            resolve: {
              items: function () {
                return mod_data;
              }
            }
          });

          modalInstance.result.then(function (selectedItem) {
            var data = selectedItem;
          }, function () {
          $log.info('Modal dismissed at: ' + new Date());
    });
  }

  vm.clearData = function() {
    $state.reload();
    //angular.copy(vm.emptyData, vm.customData);
  }

  vm.confirming = false;
  vm.confirmData = function() {

    if(vm.confirming) {
      return false;
    }
    vm.confirming = true;
    var data = {};
    if (!vm.customData.style) {
      Service.showNoty("Please Select Style First");
      vm.confirming = false;
      return false;
    }

    if (Object.values(vm.customData.sizeEnable).indexOf(true) == -1) {

      Service.showNoty("Please check the Size");
      vm.confirming = false;
      return false;
    } else {

      var counts = Object.values(vm.customData.sizeTotals);
      var count = 0;
      angular.forEach(counts, function(number){
        count += number;
      })

      if(count == 0) {

        Service.showNoty("Please Enter Size Quantity");
        vm.confirming = false;
        return false;
      }
    }

    var files = [];
    var fileNames = [];
    angular.forEach(vm.customData.print.places, function(value, key){

      if (value) {
        if ($("input[name='"+ "print_"+ key +"']")[0].files.length) {
          files.push($("input[name='"+ "print_"+ key +"']")[0].files[0]);
          fileNames.push("print_"+ key);
        }
      }
    })
    angular.forEach(vm.customData.embroidery.places, function(value, key){

      if (value) {
        if ($("input[name='"+ "embroidery_"+ key +"']")[0].files.length) {
          files.push($("input[name='"+ "embroidery_"+ key +"']")[0].files[0]);
          fileNames.push("embroidery_"+ key);
        }
      }
    })
    vm.customData.print.placeImgs = {}
    vm.customData.embroidery.placeImgs = {}
    vm.customData.style_pro = vm.style_pro;
    console.log(files)
    $http({
            method: 'POST',
            url: Session.url + "create_custom_skus/",
            headers: { 'Content-Type': undefined },
            transformRequest: function (data) {
                var formData = new FormData();
                formData.append("model", angular.toJson(data.model));
                for (var i = 0; i < data.files.length; i++) {
                    formData.append(fileNames[i], data.files[i]);
                }
                return formData;
            },
            data: { model: JSON.stringify(vm.customData), files: files }
        }).
        success(function (data, status, headers, config) {
          if(data.message == 'Success') {

            if (data.data.length > 0) {
                Data.create_orders.custom_order_data = data.data;
                $state.go("app.outbound.CreateOrders");
            }
          } else {
            vm.confirming = false;
          }
        }).
        error(function (data, status, headers, config) {
            console.log("failed!");
            vm.confirming = false;
        });
    /*Service.apiCall("create_custom_skus/", "POST", {data: JSON.stringify(vm.customData)}).then(function(resp){

      if(resp.message) {

        if(resp.data.message == 'Success') {

          console.log(resp.data.data);
          if (resp.data.data.length > 0) {
            Data.create_orders.custom_order_data = resp.data.data;
            $state.go("app.outbound.CreateOrders");
          }
        }
      }
    })
    */
  }

  function readURL(input) {

    var reader = new FileReader();

    reader.onload = function (e) {
        $('#blah').attr('src', e.target.result);
    }
    reader.readAsDataURL(input.file);
    //vm.customData.sampleImg = input.file;
  }

  function readImage(input) {
    var deferred = $.Deferred();

    var files = input.file;
    if (files) {
        var fr= new FileReader();
        fr.onload = function(e) {
            deferred.resolve(e.target.result);
        };
        fr.readAsDataURL( files );
    } else {
        deferred.resolve(undefined);
    }

    return deferred.promise();
}

  $scope.$on("fileSelected", function (event, args) {
    $scope.$apply(function () {
      console.log(args)
      readImage(args).done(function(base64Data){
        //vm.customData.sampleImg = base64Data;
        if (args.url == "sampleImg") {
          vm.customData.sampleImg = base64Data;
        } else if (args.url.split(":")[1]== 'print') {
          if(vm.customData.print.singlePrint) {
            var status = false;
            angular.forEach(vm.customData.print.placeImgs, function(value, key) {
              if (value) {
                status = true;
              }
            })
            if (!status) {
              vm.customData.print.placeImgs[args.url.split(":")[0]] = base64Data;
            } else {
              $("input[name='"+ "print_"+ args.url.split(":")[0] +"']").val('');
              Service.showNoty("image already selected");
            }
          } else {
            vm.customData.print.placeImgs[args.url.split(":")[0]] = base64Data;
          }
        } else if (args.url.split(":")[1]== 'embroidery') {
          if(vm.customData.embroidery.singleEmbroidery) {
            var status = false;
            angular.forEach(vm.customData.embroidery.placeImgs, function(value, key) {
              if (value) {
                status = true;
              }
            })
            if (!status) {
              vm.customData.embroidery.placeImgs[args.url.split(":")[0]] = base64Data;
            } else {
              $("input[name='"+ "embroidery_"+ args.url.split(":")[0] +"']").val('');
              Service.showNoty("image already selected");
            }
          } else {
            vm.customData.embroidery.placeImgs[args.url.split(":")[0]] = base64Data;
          }
        }
      });
    });
  });

  vm.removeImage = function(data, type, place) {

    if(!data.places[place]) {
      $("input[name='"+ type +"_"+ place +"']").val('');
      data.placeImgs[place] = "";
    }
  }

  vm.checkData = function(name, status) {

    if ((name == 'print' || name == 'embroidery') && !status) {
      vm.customData[name].places = {};
      vm.customData[name].placeImgs = {};
    } else if (name == 'print' || name == 'embroidery') {
      angular.forEach(vm.customData[name].places, function(value, key){
        $("input[name='"+ name +"_"+ key +"']").val('');
      })
      vm.customData[name].places = {};
      vm.customData[name].placeImgs = {};
    }
  }
}

angular
  .module('urbanApp')
  .controller('CreateCustomOrder', ['$scope', '$http', '$state', 'Session', 'colFilters', 'Service', '$modal', 'Data', '$timeout', CreateCustomOrder]);

function customOrderDetailsPreview($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.customData = items;
  vm.service = Service;

  vm.ok = function (msg) {
    $modalInstance.close("Close");
  };
}

angular
  .module('urbanApp')
  .controller('customOrderDetailsPreview', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', customOrderDetailsPreview]);


