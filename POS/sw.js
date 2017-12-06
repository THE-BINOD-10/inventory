importScripts('/app/data/dexie.js');
importScripts('/app/config/Constants.js');
importScripts('/app/config/ServerConfig.js');
importScripts('/app/data/scheema.js');
importScripts('/app/data/offlineData.js');

(function(){
	"use strict";
	//service worker version number
	var VERSION="0.0.0.91-build-0.9.0.31"
	//service worker version name
	var CACHE_NAME="POS"+VERSION;
	//directory path 
	var DIRECTORY="";
	//white listed files
	var FILECACHEDLIST=[
        "/",
        "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css",
        "https://fonts.googleapis.com/icon?family=Material+Icons",
        "bower_components/bootstrap/dist/js/bootstrap.min.js",
        "bower_components/angular-material/angular-material.min.css",
        "app/css/login.css",
        "app/css/menu.css",
        "app/css/pos.css",
        "app/css/sku.css",
        "/app/css/receipt.css",
        "app/css/more.css",
        "bower_components/jquery/dist/jquery.min.js",
        "bower_components/angular/angular.min.js",
        "bower_components/angular-animate/angular-animate.min.js",
        "bower_components/angular-aria/angular-aria.min.js",
        "bower_components/angular-messages/angular-messages.min.js",
        "bower_components/angular-material/angular-material.min.js",
        "/dependencies/simple-autocomplete.js",
        "bower_components/angular-fullscreen/src/angular-fullscreen.js",
        "bower_components/angular-ui-router/release/angular-ui-router.min.js",
        "bower_components/angular-bootstrap/ui-bootstrap-tpls.min.js",
        "app/customer/customer.module.js",
        "app/customer/customer.component.js",
        "app/customer/customer.template.html",
        "app/sku/sku.module.js",
        "app/sku/sku.component.js",
        //"app/sku/sku.css",
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
        "app/more/more.module.js",
        "app/more/more.component.js",
        "app/more/more.template.html",
        "app/app.js",
        "manifest.json",
        "app/config/Constants.js",
        "app/config/ServerConfig.js",
        "app/data/scheema.js",
        "app/data/offlineData.js",
		"app/data/dexie.js",
		"app/views/home.html",
		"app/views/print.html",
		"app/app.config.js",
		"app/header/header.component.js",
		"app/header/header.module.js",
		"app/header/header.template.html",
		"app/app.js",
		"app/app_dev.js",
        "sw.js",
        "sw_reg.js",
        "index.html",
		"app/css/more.css",
		"app/header/header.component.js",
		"app/header/header.module.js",
		"app/header/header.template.html",
		"app/css/more.css",
        "favicon.ico"
    ];

   //black list files 
   var BLACKLIST = [
        "/rest_api/",
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

             event.waitUntil(caches.open(CACHE_NAME).then(function(cache) {

                           return cache.addAll(FILECACHEDLIST).then(function(){
                                          self.skipWaiting();
                                    });
                          }));
            
	});


    self.addEventListener('push', function(event) {
		  console.log('[Service Worker] Push Received.');
		  console.log(`[Service Worker] Push had this data: "${event.data.text()}"`);

		  const title = 'Push Codelab';
		  const options = {
		    body: ' it works.',
		    icon: 'images/icon.png',
		    badge: 'images/badge.png'
		  };

		  event.waitUntil(self.registration.showNotification(title, options));
	});


    //service worker message event listner
    self.addEventListener('message', function(event){

		if(event.data==SYNC_SKUMASTER){
			getUserID().
						then(function(id){
							getCheckSum(event,REQUEST_METHOD_GET,
								appendUserID(GET_SKU_MASTER_CHECKSUM_API,id));				
						});
		    
	    }else if(event.data==SYNC_CUSTOMERMASTER){
		    getUserID().
						then(function(id){
							getCheckSum(event,REQUEST_METHOD_GET,
								appendUserID(GET_CHECKSUM_CUSTOMER_API,id));
						});
		}else if(event.data==GET_CURRENT_ORDER){
			getCurrentOrder(event);
		}else if(event.data==SYNC_POS_DATA){
			
			mPOSSync(event).then(function(data){
        		event.ports[0].postMessage(data);	
			}).catch(function(error){
				event.ports[0].postMessage(error);	
			});
		}else if(event.data==GET_PRE_ORDERS){
			getPreOrdersData(event);
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
	    	console.log(url+" fetch error "+error.message);	
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

    		SPWAN(function*(){
	        yield sync_POS_Customers().
	         		then(function(data){
	         			console.log("sync pos customet data "+data);
	    				
	    				//clear pos sync customers data	
	    				clear_POS_sync_customers();
		     		}).catch(function(error){
	 					console.log("sync pos orders data "+JSON.stringify(error));	
	 					//return reject(error);
	         		});


	         //sync created pos orders to network
	       	yield sync_POS_Orders().
	        		then(function(data){
	        			console.log("sync pos orders data "+data);	
	        			//clear pos sync orders data
	        			clear_POS_sync_orders().then(function(data){
			    			console.log("cleared sync pos orders data "+data);	
	         					
	         			}).catch(function(error){
							console.log("sync pos orders data "+JSON.stringify(error));	
							//return reject(error);
	         			});
	         		}).catch(function(error){
	         			console.log("sync pos orders data "+JSON.stringify(error));	
	         		});

	        yield sync_Preorder_offline_delivered().
	         			then(function(data){
	         					console.log("sync pos preorder transactions data "+data);	
	         					checksumDelete(OFFLINE_DELIVERED).then(function(data){
	         						    console.log("cleared pos preorder transactions data "+data);	
	         					    	return resolve(data);
	         						}).catch(function(error){
	         							return reject(error.message);
	         						});
	         					}).catch(function(error){
	         						    return reject(error.message);
	         					});
	         			
	        }).catch(function(error){
	        	return reject(error.message);
	        }) 		

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
                                	return resolve(data);
                   				}).catch(function(error){
                   					return reject(error.message);
                   				});

                   }else{
                   		return resolve(true);
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
                                		return resolve(data);
                   				}).catch(function(error){
                   					return reject(error);
                   				});
                   }else{
                   		return resolve(true);
                   }
         		});
	    });
   }



	//sync POS preorder transactions 
	function sync_Preorder_offline_delivered(){

		return new Promise(function(resolve,reject){

      		get_transaction_POS_PreOrders().
         		then(function(data){
                   
                   if(data!=undefined && data.length>0){
                   	                  
                    var content="data="+encodeURIComponent(JSON.stringify(data));
                    
                    getServerData(REQUEST_METHOD_POST,UPDATE_PRE_ORDER_STATUS_API,content).
                   				then(function(data){
                                		return resolve(data);
                   				}).catch(function(error){
                   					return reject(error);
                   				});
                   }else{
                   		return resolve(true);
                   }
         		});
	    });
		
	}


   	//get currnet order id from network
    function getCurrentOrder(event){	

    	getUserID().then(function(id){

    		getServerData(REQUEST_METHOD_GET,appendUserID(GET_CURRENT_ORDER_ID_API,id),"").
  		 					then(function (result) {
  		 			          if(Object.keys(result).length>0){
            						
            						var val_data=JSON.parse(result);
						          	
						          	setCheckSum(setOrderID(val_data)).
						          			then(function(data){
						          				console.log("order no is sync with server "+JSON.stringify(val_data));
						          				event.ports[0].postMessage(val_data);	
						          			}).catch(function(error){
						          				console.log("order no is sync error "+error);
						          				event.ports[0].postMessage(error.message);	
						          			});
          						}
  		 	
					  		}).catch(function(error){
									event.ports[0].postMessage(error.message);	
					  		});	 	

    	});
	}

	function getPreOrdersData(event){

		getUserID().then(function(id){
					
			var content="data="+encodeURIComponent(JSON.stringify({'user':id,"request_from":"bulk"}));		
			getServerData(REQUEST_METHOD_POST,PRE_ORDER_API,content).
  		 					then(function (result) {
  		 			        	if(Object.keys(result).length>0){
            						
            						var val_data=JSON.parse(result);
						          	addPreOrdersBulkItems(val_data.data).then(function(data){
						          		event.ports[0].postMessage(data);	
						          	}).catch(function(error){
						          		console.log(" preorders data "+val_data.length);
          							    event.ports[0].postMessage(error.message);	
						          	});
						          	
          						}else{
          							event.ports[0].postMessage("data not available");	
          						}
  		 	
					  		}).catch(function(error){
									event.ports[0].postMessage(error.message);	
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
                    

                   		console.log("event name is "+event.data);
                      	getContent(event,data);
                     		//ent.ports[0].postMessage("1"); 	
                    

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

		if(event.data==SYNC_SKUMASTER){

			getSkumasterData().
						then(function(result){
							if(result.length<=0 || data!=true){

							getUserID().then(function(id){
								getSkuConent(event,REQUEST_METHOD_GET,
									appendUserID(GET_SKUDATA_API,id));
							});	
							
							}else{
								event.ports[0].postMessage(data);					
							}
						});
		}else if(event.data==SYNC_CUSTOMERMASTER){

			getcustomerData().
						then(function(result){
							if(result.length<=0 || data!=true){
								getUserID().then(function(id){
								getCustomerContent(event,REQUEST_METHOD_GET,
									appendUserID(GET_CUSTOMER_API,id));
							});
						
							}else{
								event.ports[0].postMessage(data);					
							}
						});


		}else{
			event.ports[0].postMessage(data);
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
                					console.log(request_url+ "skumaster saved locally is "+val);
                                      event.ports[0].postMessage(val);
									}).catch(function(error){
										event.ports[0].postMessage(error.message);
									});
		  		 				}
							}).catch(function(error){
								console.log(request_url+" sku data is "+error.message);
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
						         		console.log("customer data saved locally is "+val);
				        		    	event.ports[0].postMessage(val);
									}).catch(function(error){
										event.ports[0].postMessage(error.message);
									});
		  		 				}
										}).catch(function(error){
								console.log("customer  data is "+error);
								event.ports[0].postMessage(error.message);
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
					    console.log(request_url+"get the  response from network ");
					  	return resolve(data);
					  
				   }).catch(function(error){
				  		console.log(request_url+" response error is " +error);
				  		return reject(error);
					});
				 }else{
				 	return reject("error"); 
				   //return resolve(false);  
				}
			   }).catch(function(error){
			   		console.log(request_url+ " response error is " +error.message);
				 	return reject(error);
			  });
	  	});
	}

 
}());
