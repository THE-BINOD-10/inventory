
// self.importScripts('./scripts/App/dexie.js');
// self.importScripts('./scripts/App/offlineDB.js');
if( 'undefined' === typeof window){
  importScripts('./scripts/App/dexie.js');
  importScripts('./scripts/App/offlineDB.js');
}

 ;(function(){
   "use strict";


 var version        = "0.0.1-build03.0.176",
      cacheName     = "stock1-app-" + version,
      Directory     ="";
 var APICALL        ="https://api.stockone.in/rest_api/";
 var UIAPICALL      ="https://go.stockone.in/";
// var APICALL        ="http://176.9.181.43:7654/rest_api/";
 window['current_version'] = version;

 var filesToBeCached = [
       Directory+ "/",
       //Directory+ "/index.html",
       Directory+ "/sw_reg.js",
       Directory+ "/favicon.ico",
       Directory+ "/vendor/bootstrap/dist/css/bootstrap.min.css",
       Directory+ "/vendor/perfect-scrollbar/css/perfect-scrollbar.min.css",
       Directory+ "/styles/roboto.css",
       Directory+ "/styles/font-awesome.css",
       Directory+ "/styles/panel.css",
       Directory+ "/styles/feather.css",
       Directory+ "styles/animate.css",
       Directory+ "/styles/urban.skins.css",
       Directory+ "/styles/urban.css",
       Directory+ "/vendor/datatables/media/css/jquery.dataTables.min.css",
       Directory+ "/vendor/chosen_v1.4.0/chosen.min.css",
       Directory+ "/vendor/sweetalert/dist/sweetalert.css",
       Directory+ "/vendor/jquery.tagsinput/src/jquery.tagsinput.css",
       Directory+ "/vendor/checkbo/src/0.1.4/css/checkBo.min.css",
       Directory+ "/styles/custom/custom.css",
       Directory+ "/vendor/bootstrap-daterangepicker/daterangepicker-bs3.css",
       Directory+ "/vendor/bootstrap-datepicker/dist/css/bootstrap-datepicker3.min.css",
       Directory+ "/vendor/bootstrap-datepicker/dist/css/bootstrap-datepicker3.min.css",
       Directory+ "/scripts/extentions/modernizr.js",
       Directory+ "/vendor/jquery/dist/jquery.min.js",
       Directory+ "/vendor/angular/angular.min.js",
       Directory+ "/vendor/chosen_v1.4.0/chosen.jquery.min.js",
       Directory+ "/vendor/jquery.tagsinput/src/jquery.tagsinput.js",
       Directory+ "/vendor/datatables/media/js/jquery.dataTables.min.js",
       Directory+ "/scripts/extentions/plugins/angular-datatables.min.js",
       Directory+ "/vendor/noty/js/noty/packaged/jquery.noty.packaged.min.js",
       Directory+ "/scripts/extentions/noty-defaults.js",
       Directory+ "/vendor/moment/min/moment.min.js",
       Directory+ "/vendor/bootstrap-daterangepicker/daterangepicker.js",
       Directory+ "/vendor/bootstrap-datepicker/dist/js/bootstrap-datepicker.min.js",
       Directory+ "/vendor/angular-bootstrap/ui-bootstrap-tpls.min.js",
       Directory+ "/scripts/extentions/plugins/bootstrap.min.js",
       Directory+ "/vendor/angular-animate/angular-animate.min.js",
       Directory+ "/vendor/angular-ui-router/release/angular-ui-router.min.js",
       Directory+ "/vendor/angular-sanitize/angular-sanitize.min.js",
       Directory+ "/vendor/angular-touch/angular-touch.min.js",
       Directory+ "/vendor/angular-ui-utils/ui-utils.min.js",
       Directory+ "/vendor/ngstorage/ngStorage.min.js",
       Directory+ "/vendor/ocLazyLoad/dist/ocLazyLoad.min.js",
       Directory+ "/vendor/perfect-scrollbar/js/perfect-scrollbar.jquery.min.js",
       Directory+ "/scripts/extentions/lib.js",
       Directory+ "/vendor/fastclick/lib/fastclick.js",
       Directory+ "/scripts/extentions/angular-cookies.min.js",
       Directory+ "/vendor/jquery-validation/dist/jquery.validate.min.js",
       Directory+ "/vendor/jquery.maskedinput/dist/jquery.maskedinput.min.js",
       Directory+ "/scripts/extentions/plugins/typehead/typeahead.min.js",
       Directory+ "/scripts/extentions/auth/auth.js",
       Directory+ "/scripts/extentions/auth/authEvents.js",
       //Directory+ "/scripts/extentions/auth/session.js",
       Directory+ "/vendor/sweetalert/dist/sweetalert.min.js",
       Directory+ "/vendor/angular-sweetalert/SweetAlert.min.js",
       Directory+ "/vendor/checkbo/src/0.1.4/js/checkBo.min.js",
       Directory+ "/scripts/extentions/plugins/lodash/lodash.min.js",
       Directory+ "/scripts/extentions/plugins/multi-select/angularjs-dropdown-multiselect.js",
       Directory+ "/scripts/extentions/plugins/bootstrap-select/bootstrap-select.min.js",
       Directory+ "/scripts/extentions/plugins/bootstrap-select/bootstrap-select.min.css",
       Directory+ "/scripts/app.js",
       Directory+ "/scripts/app.main.js",
       Directory+ "/scripts/config.router.js",
       Directory+ "/scripts/directives/anchor-scroll.js",
       Directory+ "/scripts/directives/c3.js",
       Directory+ "/scripts/directives/chosen.js",
       Directory+ "/scripts/directives/navigation.js",
       Directory+ "/scripts/directives/offscreen.js",
       Directory+ "/scripts/directives/panel-control-collapse.js",
       Directory+ "/scripts/directives/panel-control-refresh.js",
       Directory+ "/scripts/directives/panel-control-remove.js",
       Directory+ "/scripts/directives/preloader.js",
       Directory+ "/scripts/directives/scrollup.js",
       Directory+ "/scripts/directives/vector.js",
       Directory+ "/scripts/directives/image.js",
       // Directory+ "/scripts/services/col_filters.js",
       // Directory+ "/scripts/services/wms_service.js",
       // Directory+ "/scripts/services/table_service.js",
       //
       // Directory+"/views/App/app.html",
       // Directory+"/views/App/create_orders.html",
       // Directory+"/views/App/create_orders/catlog.html",
       // Directory+"/views/App/create_orders/company_name.html",
       // Directory+"/views/App/create_orders/details.html",
       // Directory+"/views/App/create_orders/order.html",
       // Directory+"/views/App/create_orders/style.html",

       Directory+"/styles/App/app.css",

      // Directory+ "/scripts/App/**.{js}",
      // Directory+ "/scripts/App/**/**.{js}",

      ],

  blacklist = [
        "/rest_api/",

      ];

  function isBlacklisted (url) {

    var blacklisted = false,
        index, item;

    for (index in blacklist) {

      item = blacklist[index];

      blacklisted = url.indexOf(item) >= 0;

      if (blacklisted) {

        break;
      }
    }

    return blacklisted;
  }



 self.addEventListener('push', function(event) {
    var title = 'Yay a message.';
    var body = 'We have received a push message.';
    var icon = 'images/stockone_logo.png';
    var tag = 'simple-push-example-tag';
    event.waitUntil(
      self.registration.showNotification(title, {
        body: body,
        icon: icon,
        "sound":"./sounds/notification_sound.mp3",
    "vibrate": [200, 100, 200, 100, 200, 100, 400],
        tag: tag
      })
    );
  });


  self.addEventListener('notificationclick', function(event) {
    console.log('On notification click: ', event.notification.tag);
    // Android doesn't close the notification when you click on it
    // See: http://crbug.com/463146
    event.notification.close();

    // This looks to see if the current is already open and
    // focuses if it is
    event.waitUntil(
      clients.matchAll({
        type: "window"
      })
     .then(function(clientList) {
       for (var i = 0; i < clientList.length; i++) {
         var client = clientList[i];
         if (client.url == '/' && 'focus' in client)
           return client.focus();
         }
        if (clients.openWindow) {
         return clients.openWindow(UIAPICALL+'#/App/createorder');
        }
      })
    );
   });


 self.addEventListener("activate", function (event) {

     if (self.clients && clients.claim) {
        clients.claim();
    }

    event.waitUntil(

      caches.keys().then(function (cachesList) {

        return Promise.all(cachesList.map(function (name) {

          if (name !== cacheName) {

            return caches.delete(name);
          }
        }));
      })
    );
  });


 self.addEventListener("install", function (event) {

     event.waitUntil(

      caches.open(cacheName).then(function (cache) {

        return cache.addAll(filesToBeCached).then(function(){
               self.skipWaiting();})
      }, function (err) {

        log("Unable to cache Error: " + err);
      })
    );

 });


 self.addEventListener("fetch", function (event) {

    var url = event.request.url;
    console.log(event.request);
    event.respondWith(
      caches.match(event.request).then(function (response) {
        if (response) {
          return response;
        }
        var fetchRequest = event.request.clone();

      return fetch(fetchRequest).then(function (response) {
          if (fetchRequest.method === "POST"
              || isBlacklisted(url)
              || !response
              || response.status !== 200
              || response.type !== "basic") {

            console.log("Not caching " + url);
            return response;
          }

          var cacheResponse = response.clone();

          caches.open(cacheName).then(function (cache) {

            cache.put(event.request, cacheResponse);
          });

          return response;
        });
      })
    );
  });




 self.addEventListener('message', function(event){

      checkSum().then(function (result) {

          if(result) {
            getContent().then(function(result){
               event.ports[0].postMessage("1");
             }).catch(function(err){
                 event.ports[0].postMessage("1");
             });
          } else {
             event.ports[0].postMessage("1");
          }

      }).catch(function () {
		event.ports[0].postMessage("1");
      });
  });




  function checkSum(){

    return new Promise(function (resolve, reject) {

		   fetch( APICALL+"get_file_checksum/?name=sku_master",{
				method: 'get',
				mode  : 'cors',
			    redirect :'follow',
		        credentials: 'include'
		   }).then(function(response){
			if(response.status==200){
			   response.text().then(function(data){
				  var val_data=JSON.parse(data);
				  if(Object.keys(val_data).length>0){

					var file_data=val_data['file_data'];

						db.checksum.toArray().then(function(data){
						  var diff_checksum=false;
						  if(data.length>0){
							 var check_value=data[0];
							 check_value['check_sum']==file_data['checksum']?diff_checksum=false:diff_checksum=true;
						   }else{
							 diff_checksum=true;
						   }

						   if(diff_checksum){
								var checksum_status=setCheckSum(file_data['checksum']);
								checksum_status.then(function(data){
								  if(data)
									 return resolve(true);
								   else
									 return resolve(false);
								  });
						  }else{
							  return resolve(false);
						  }
						});
				  }
			   });
			 }else{
			   return resolve(false);
			}
		   }).catch(function(){
			 return resolve(false);
		  });
  });

 }


  function getContent(){

   return new Promise(function (resolve, reject) {


      fetch( APICALL +"get_file_content/?name=sku_master",{
        method: 'get',
        mode  : 'cors',
     redirect :'follow',
   credentials: 'include'
   }).then(function(response){
    if(response.status==200){
       response.text().then(function(data){
          var val_data=JSON.parse(data);
          if(Object.keys(val_data).length>0){
            var file_content=val_data['file_content'];
            var sku_data=file_content['skus_data'];
            var brands_data=file_content['brands_data'];
            var brands=brands_data[0];
            var categories=brands_data[1];
            var skus=sku_data[0];

            setBrands(brands);
            setCategories(categories);

            if(setSku(skus)){
              return resolve(true);
            }else{
              return reject(true);
            }
        }
       });
     }else{
     return reject(false);
     }
    }).catch(function(){return reject(false)});
  });
 }

 self.addEventListener('sync', function(event) {
   if(event.tag == 'place_order') {
     console.log("sync place order fired ");

     setTimeout(function(){
       event.waitUntil(getOrderKeys());
     }, 2000);
   }
 });

  function getOrderKeys(){

    var placed_orders=getplacedOrders();
      placed_orders.then(function(orders){
       orders.forEach(function(order){
         placeOrderSync(order);
       });
    });
  }

 function placeOrderSync(order_data){

   console.log("getting stored data"+order_data.order);
          var data=JSON.parse(order_data.order);
          var params="";
          var notification_body="";
          var count=0
          for(var key in data){
            params += data[key].name+"="+encodeURIComponent(data[key].value);
            notification_body +=data[key].name +":" + data[key].value;
            count++;

            if(count!=data.length){
              params +="&";
              notification_body +=",";
            }
          }



   fetch(APICALL +'insert_order_data/?'+params,{
           method: 'get',
           mode  : 'cors',
           redirect :'follow',
           credentials: 'include'
         }).then(function(response){
           if(response.status!==200){
               throw new Error;
           }else{
            console.log(order_data.time+"offline order req response is "+response);

              /*
              return  self.registration.showNotification("Order Place"+data,{
                  body:notification_body,
                  icon: "images/stockone_logo.png",
                  tag: "place order",
                  "sound":"./sounds/notification_sound.mp3"

              });
              */

               var data=deleteOrder(order_data.time);
                      data.then(function(count){
                         console.log("record deleted");
                      }).catch(function(err){
                         console.log("record del err "+err);
                      });



                self.registration.showNotification("Order Place",{
                  body:notification_body,
                  icon: "images/stockone_logo.png",
                  tag: "place order",
                  "sound":"./sounds/notification_sound.mp3"

                });

               return true;
           }

         });


 }
 }());
