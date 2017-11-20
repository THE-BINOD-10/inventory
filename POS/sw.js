importScripts('/app/data/dexie.js');
importScripts('/app/config/Constants.js');
importScripts('/app/config/ServerConfig.js');
importScripts('/app/data/scheema.js');
importScripts('/app/data/offlineData.js');

(function(){
	"use strict";
	//service worker version number
	var VERSION="0.0.0.9-build-0.9.0.15"
	//service worker version name
	var CACHE_NAME="POS"+VERSION;
	//directory path 
	var DIRECTORY="";
	//white listed files
	var FILECACHEDLIST=[
        "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css",
        "https://fonts.googleapis.com/icon?family=Material+Icons",
        "dependencies/bootstrap.min.js",
        "dependencies/node_modules/angular-material/angular-material.min.css",
        "app/css/login.css",
        "app/css/menu.css",
        "app/css/pos.css",
        "app/css/sku.css",
        "app/css/redirect.css",
        "dependencies/jquery.js",
        "dependencies/new/angular.min.js",
        "dependencies/angular-animate.min.js",
        "dependencies/angular-aria.min.js",
        "dependencies/angular-messages.min.js",
        "dependencies//node_modules/angular-material/angular-material.min.js",
        "dependencies/simple-autocomplete.js",
        "dependencies/fullscreen/angular-fullscreen.js",
        "dependencies/angular-ui-router.min.js",
        "dependencies/new/ui-bootstrap-tpls-1.3.3.js",
        "dependencies/print/print.js",
        "app/customer/customer.module.js",
        "app/customer/customer.component.js",
        "app/customer/customer.template.html",
        "app/sku/sku.module.js",
        "app/sku/sku.component.js",
        "app/sku/sku.css",
        "app/sku/sku.template.html",
        "app/cal_money/money.module.js",
        "app/cal_money/money.component.js",
        "app/cal_money/money.template.html",
        "app/last/last.component.js",
        "app/last/last.module.js",
        "app/last/last.template.html",
        "app/less/menu.less",
        "app/less/receipt.less",
        "app/less/sku.less",
        "app/login/login.module.js",
        "app/login/login.component.js",
        "app/login/login.template.html",
        "app/order_summary/summary.module.js",
        "app/order_summary/summary.component.js",
        "app/order_summary/summary.template.html",
        "app/pending/pending.module.js",
        "app/pending/pending.component.js",
        "app/pending/pending.template.html",
        "app/order/order.module.js",
        "app/order/order.component.js",
        "app/order/order.template.html",
        "app/app.js",
        "manifest.json",
        "app/config/Constants.js",
        "app/config/ServerConfig.js",
        "app/data/scheema.js",
        "app/data/offlin.js",
		"app/data/dexie.js",
		"app/views/home.html",
		"app/views/print.html",
		"app/app.config.js",
		"app/app.js",
		"app/app_dev.js",
        //"sw.js",
        "sw_reg.js"

    ];

   //black list files 
   var BLACKLIST = [
        "/rest_api/",
        "/search_product_data",
        "/get_current_order_id/"

      ];

    //check url is black listed or not  
    function isBlacklisted (url) {

		    var blacklisted = false,index, item;

		    for (index in BLACKLIST) {
			      item = BLACKLIST[index];
			      blacklisted = url.indexOf(item) >= 0;
			      if (blacklisted) {
			        break;
			      }
		    }

	    return blacklisted;
    }
  
    //service worker install event listner
    self.addEventListener("install", function (event) {

	    event.waitUntil(caches.open(CACHE_NAME).then(function (cache) {

	        return cache.addAll(FILECACHEDLIST).then(function(){
	               self.skipWaiting();})
	            }, function (err) {
	             log("Unable to cache Error: " + err);
	        })
	    );

    });


    self.addEventListener('push', function(event) {
		  console.log('[Service Worker] Push Received.');
		  console.log(`[Service Worker] Push had this data: "${event.data.text()}"`);

		  const title = 'Push Codelab';
		  const options = {
		    body: 'Yay it works.',
		    icon: 'images/icon.png',
		    badge: 'images/badge.png'
		  };

		  event.waitUntil(self.registration.showNotification(title, options));
	});


    //service worker message event listner
    self.addEventListener('message', function(event){

		if(event.data==SYNC_SKUMASTER){
			appendUserID(GET_SKU_MASTER_CHECKSUM_API).
						then(function(url){
							getCheckSum(event,REQUEST_METHOD_GET,url);				
						});
		    
	    }else if(event.data==SYNC_CUSTOMERMASTER){
		    appendUserID(GET_CHECKSUM_CUSTOMER_API).
						then(function(url){
							getCheckSum(event,REQUEST_METHOD_GET,url);
						});
		}else if(event.data==GET_CURRENT_ORDER){
			getCurrentOrder(event);
		}else if(event.data==SYNC_POS_DATA){
			
			mPOSSync(event).then(function(data){
        		event.ports[0].postMessage(data);	
			}).catch(function(error){
				event.ports[0].postMessage(error);	
			});
		}
  	});


    //service worker active listner
 	self.addEventListener("activate", function (event) {

	    if (self.clients && clients.claim) {
	        clients.claim();
	    }

	    event.waitUntil(caches.keys().then(function (cachesList) {

	        return Promise.all(cachesList.map(function (name) {
				          if (name !== CACHE_NAME) {
				            return caches.delete(name);
				          }
	        }));
	    }));
    });

 	//service worker fetch event listner get the files and cached
    self.addEventListener("fetch", function (event) {

	    var url = event.request.url;
	    console.log("fetch url "+url);
	    event.respondWith(caches.match(event.request).then(function (response) {
	        if (response) {
	          return response;
	        }
	        var fetchRequest = event.request.clone();

	      return fetch(fetchRequest).then(function (response) {
	          if (fetchRequest.method === "POST"
	          	  || fetchRequest.method === "GET"
	              || isBlacklisted(url)
	              || !response
	              || response.status !== 200
	              || response.type !== "basic") {

	            console.log("Not caching " + url);
	            return response;
	          }else{
	          	console.log("caching " + url);
	           }

	          var cacheResponse = response.clone();

	          caches.open(CACHE_NAME).then(function (cache) {

	            cache.put(event.request, cacheResponse);
	          });

	          return response;
	        });
	    }).catch(function(error){
	    	console.log(url+" fetch error "+error);	
	    }));
    });

    //service worker sync event listner
    self.addEventListener("sync",function(event){

	    if(event.tag==SYNC_POS_DATA){
		      	event.waitUntil(mPOSSync(false).
		      				then(function(data){

			      			}).catch(function(error){
			      				throw error;
			      			}));
	    }
    });

    //POS transactions  sync 
    function mPOSSync(event){

    	 //sync added pos customers to network	
    	return new Promise(function(resolve,reject){
	         sync_POS_Customers().
	         		then(function(data){
	         			console.log("sync pos customet data "+data);
	    				
	    				//clear pos sync customers data	
	    				clear_POS_sync_customers();

		       			//sync created pos orders to network
	         			sync_POS_Orders().
	         				then(function(data){
	         				console.log("sync pos orders data "+data);	
	         				//clear pos sync orders data
	         				clear_POS_sync_orders().then(function(data){
	         					resolve(data);
	         				}).catch(function(error){
	         					reject(error);
	         				});
	         			}).catch(function(error){
							console.log("sync pos orders data "+JSON.stringify(error));	
							reject(error);
	         			});
	         		}).catch(function(error){
	 					
	 					console.log("sync pos orders data "+JSON.stringify(error));	
	 					reject(error);
	         		});

        }); 		
    	
    }

   	//sync POS offline added customers 	
   function sync_POS_Customers(){

      return new Promise(function(resolve,reject){

      	get_POS_sync_CustomersData().
         		then(function(data){
                   
                   if(data.length>0){

                   	var content='customers=' + encodeURIComponent(JSON.stringify(data));
                   	
                   	getServerData(REQUEST_METHOD_POST,ADD_POS_CUSTOMER_API,content).
                   				then(function(data){
                                	resolve(data);
                   				}).catch(function(error){
                   					reject(error);

                   				});

                   }else{
                   		resolve(true);
                   }

         		});
      });

   }

   //sync POS offline added orders
   function sync_POS_Orders(){

   		return new Promise(function(resolve,reject){

      		get_POS_Sync_Orders().
         		then(function(data){
                   
                   if(data.length>0){
                   	var sync_data=[]; 
                   	data.forEach(function(item){
                   		sync_data.push(JSON.parse(item.order));
                   	});
                    
                    var content='order=' + encodeURIComponent(JSON.stringify(sync_data));
                    
                    getServerData(REQUEST_METHOD_POST,SYNC_POS_ORDERS_API,content).
                   				then(function(data){
                                		resolve(data);
                   				}).catch(function(error){
                   					reject(error);
                   				});
                   }else{
                   		resolve(true);
                   }
         		});
	    });
   }

   	//get currnet order id from network
    function getCurrentOrder(event){	

    	appendUserID(GET_CURRENT_ORDER_ID_API).then(function(url){

    		getServerData(REQUEST_METHOD_GET,url,"").
  		 					then(function (result) {
  		 			          if(Object.keys(result).length>0){
            						
            						var val_data=JSON.parse(result);
						          	
						          	setCheckSum(setOrderID(val_data)).
						          			then(function(data){
						          				console.log("order no is sync with server "+JSON.stringify(val_data));
						          				event.ports[0].postMessage(val_data);	
						          			}).catch(function(error){
						          				console.log("order no is sync error "+error);
						          				event.ports[0].postMessage([]);	
						          			});
          						}
  		 	
					  		}).catch(function(error){
									event.ports[0].postMessage([]);	
					  		});	 	

    	});
	}


    //get the check sum from network
  	function getCheckSum(event,request_method,request_url){
  		 getServerData(request_method,request_url,"").
  		 then(function (result) {
  		 		
  		 		var val_data=JSON.parse(result);

  		 		var file_data; 
  		 		if(Object.keys(val_data).length>0)
					file_data=val_data['file_data'];
				var diff_checksum=false;
				//var val=false;
                if(file_data!=undefined){
		           
					getCheckSumData(file_data).then(function(data){
                   		//val=data;
                      if(data){

                   		console.log("event name is "+event.data);
                      	getContent(event,data);
                     		//ent.ports[0].postMessage("1"); 	
                      }

					}).catch(function(error){
						console.log("event name is "+event.data);
						getContent(event,error);
						//ent.ports[0].postMessage("0");
					});
				}
			}).catch(function(error){
					console.log("event name is "+event.data);
					getContent(event,false);
			
			});

  	}

  	//check message event and get the content 
  	function getContent(event,data){

  		if(data==true){
			event.ports[0].postMessage(data);
  		}else{
			if(event.data==SYNC_SKUMASTER){
				appendUserID(GET_SKUDATA_API).then(function(url){
					getSkuConent(event,REQUEST_METHOD_GET,url);
				});
			    
		    }else if(event.data==SYNC_CUSTOMERMASTER){
			    appendUserID(GET_CUSTOMER_API).then(function(url){
					getCustomerContent(event,REQUEST_METHOD_GET,url);
				});

			}
		}

   	}

   	//get the sku content from network
  	function getSkuConent(event,request_method,request_url){
		getServerData(request_method,request_url,"").
							then(function(result){
								var val_data=JSON.parse(result);
								var file_data=[]; 
		  		 				if(Object.keys(val_data).length>0){
									file_data=val_data["file_content"];
									addSKUBulkItem(file_data).then(function(val){
										event.ports[0].postMessage(val);
									}).catch(function(error){
										event.ports[0].postMessage(error);
									});
		  		 				}
								console.log(request_url+ " sku data is "+result);
							}).catch(function(error){
								console.log(request_url+" sku data is "+error);
							});

  	}

  	//get the customer content from network
  	function getCustomerContent(event,request_method,request_url){

		getServerData(request_method,request_url,"").
							then(function(result){
								var val_data=JSON.parse(result);
								var file_data=[]; 
		  		 				if(Object.keys(val_data).length>0){
									file_data=val_data["file_content"];
									addCustomerBulkItem(file_data).
									then(function(val){
										event.ports[0].postMessage(val);
									}).catch(function(error){
										event.ports[0].postMessage(error);
									});
		  		 				}
								console.log("customer data is "+file_data.length);
							}).catch(function(error){
								console.log("customer  data is "+error);
							});

  	}

	//do network call
	function getServerData(request_method,request_url,content_body){

	    return new Promise(function (resolve, reject) {
	        var header = {};
			var body_cotent;
			
			//request headders
			var contenet_data={
					method: request_method,
					mode  : 'cors',
				    redirect :'follow',
			        credentials: 'include'
			        		        
			   };

			//add body and headers for post method   
			if(REQUEST_METHOD_POST == request_method){
			
			   	contenet_data.body=content_body;
			   	contenet_data.headers={"Content-Type": "application/x-www-form-urlencoded"};
			
			}

			fetch(request_url,contenet_data).then(function(response){
				if(response.status==200){
				   response.text().then(function(data){
					   // var val_data=JSON.parse(data);
					    console.log(request_url+" response is " +data);
					  	return resolve(data);
					  
				   }).catch(function(error){
				  		console.log(request_url+" response error is " +error);
				  		return reject(error.text);
					});
				 }else{
				 	return reject("error"); 
				   //return resolve(false);  
				}
			   }).catch(function(error){
			   		console.log(request_url+ " response error is " +error);
				 	return reject(error.text);
			  });
	  	});
	}

 
}());
