"use strict";

	function addItem(){

		DATABASE.skumaster.put({
			ProductDescription: "laptop back cover",
			igst: 20,
			SKUCode: "228",
			price: 100,
			discount: 20,
			selling_price: 130,
			search: "228 Pavechas Cotton Sari",
			url: "http://img.fkcdn.com/image/sari/g/q/3/228-pavecha-free-size-1024x800-imadnbxqgfdbknef.jpeg",
			sgst: 20,
			data_id: 546,
			utgst: 8,
			stock_quantity: 120,
			cgst: 3
		}).then(function(res){
		 			console.log("data is "+res);
			}).catch(function(error){
					console.log("data error is "+error);
			});

	}
	//addItem();

	//add bulk sukitems
	function addSKUBulkItem(skulist){

		return new Promise(function(resolve,reject){

			 DATABASE.transaction('rw', DATABASE.skumaster, DATABASE.sku_search_words,
				    	 function () {

				DATABASE.skumaster.bulkPut(skulist).then(function(res){
				 			console.log("addSKUBulkItem data is "+res);
				 			//getData();
					return resolve(true);
					}).catch(Dexie.BulkError,function(error){
							console.log("some sku failed "+ skulist.length()-error.failures.length);
					  return reject("some sku failed "+ skulist.length()-error.failures.length);
					});

		        }).catch(function(error){
		  			return reject("some sku failed "+ skulist.length()-error.failures.length);
		        });
	        });    	
    }

    //add bulk cutomers
	function addCustomerBulkItem(customer_list){

    	return new Promise(function(resolve,reject){
			DATABASE.customer.bulkPut(customer_list).then(function(res){
			 			console.log("data is "+res);
			 			
				return resolve(true);
				}).catch(Dexie.BulkError,function(error){
						console.log("failed to load some customers "+ customer_list.length()-error.failures.length);
				   return reject("failed to load some customers " + customer_list.length()-error.failures.length);
				});
	    	
    	});
    }


    //serach sku items
    function getData(find_key){
    	
		return new Promise(function(resolve,reject){
	    	
		    DATABASE.transaction('rw', DATABASE.skumaster, DATABASE.sku_search_words,
					    	 function () {
	   
	   				 var foundIds = {};
	    			 DATABASE.sku_search_words.where("word").
	    						startsWith(find_key).limit(30).
	    						each(function (wordToSKUMapping) {
	        						foundIds[wordToSKUMapping.SKUCode.toString()] = true;
	    							}).
	    				then(function () {
								        // Now we got all sku IDs in the keys of foundIds object.
								        // Convert to array if IDs.
	        				var sku_ids = Object.keys(foundIds).
	        						map(function (sku_id) {
	         						return sku_id;
	          					});
	        
	           				DATABASE.skumaster.where("SKUCode").
	           						anyOf(sku_ids).toArray().
	        							then(function(skus){
	        								return resolve(skus);
	        							}).catch(function(error){
	        								console.log('collection error ' +err);
											return resolve([]);
	        							});
	        
	    				});
			}).catch(function (e) {
	    		console.log(e.stack || e);
	    		return resolve([]);
			}); 

			});
		        
	}

	//search customer
	function getCustomerData(find_key){

		return new Promise(function(resolve,reject){
			DATABASE.customer.where("Number").
								startsWithIgnoreCase(find_key).
								or("FirstName").startsWithIgnoreCase(find_key).
								toArray().then(function(data){
									return resolve(data);
								}).catch(function(error){
									return reject(error);
								});
		});
	}

	//addBulkItem();
	
	//check table in DATABASE
	function checktable(table_name){

            return new Promise(function(resolve,reject){
                var count=DATABASE.tables.length;
                var count_item=0; 
				DATABASE.tables.forEach(function(table) {
	    		count_item++;
	    		if(table.name==table_name){
	    		   console.log("Schema of " + table.name + ": " + JSON.stringify(table.schema));	
	    		   resolve(true) ;
	    		}else if(count_item==count){
	    			reject(false);
	    		}
    		 });
            }); 

		
	}

    //check sync data
	function checkSyncData(sync_type,messagechannel){
         console.log("call post message");
	     return new Promise(function(resolve, reject){
	        var msg_chan =messagechannel;

	        msg_chan.port1.onmessage = function(event){


	        	if(event.data.error)
	        		reject(event.data.error)
	        	else
	        		resolve(event.data);          
	         };

			sendMessage(sync_type,[msg_chan.port2]);

			
	        
    	});
	}

	//check sync sku items 
    function sync_SKUData(){
    	return new Promise(function(resolve,reject){

	    checkSyncData(SYNC_SKUMASTER,new MessageChannel()).then(function(data){
	    	console.log("SYNC_SKUMASTER sync data "+data);
	    	resolve();
	    }).catch(function(error){
	    	console.log("SYNC_SKUMASTER sync failed "+error);
	    	reject();
	    });

	});

    }

    //check sync sync customer data
    function syncCustomerData(){

	return new Promise(function(resolve,reject){
    	checkSyncData(SYNC_CUSTOMERMASTER,new MessageChannel()).then(function(data){
	    	console.log("SYNC_CUSTOMERMASTER sync data "+data);
	        sync_SKUData().then(function(){
              resolve();
	        }).catch(function(){
	        	reject();
	        });
    	}).catch(function(error){
	    	console.log("SYNC_CUSTOMERMASTER sync failed "+error);
	        sync_SKUData().then(function(){
              resolve();
	        }).catch(function(){
	        	reject();
	        });
    	});
   	});
    }


    //sync current order id 
    function sync_getCurrentOrderId(){

    return new Promise(function(resolve,reject){
	    checkSyncData(GET_CURRENT_ORDER,new MessageChannel()).then(function(data){
	    	console.log("GET_CURRENT_ORDER sync data "+data);
			
			syncCustomerData().then(function(){
				resolve();
			}).catch(function(){
				reject();
			});
			
	    }).catch(function(error){
	    	console.log("GET_CURRENT_ORDER sync failed "+error);
	        
	        syncCustomerData().then(function(){
				resolve();
			}).catch(function(){
				reject();
			});

	    });
	 });   

    }

    //sync POS transacctions data
    function syncPOSTransactionData(){

    	return new Promise(function(resolve,reject){
	        checkSyncData(SYNC_POS_DATA,new MessageChannel()).then(function(data){
		    	console.log(" sync POS  data "+data);
				
				sync_getCurrentOrderId().then(function(){
					resolve();
				}).catch(function(){
					reject();
				});
		   
		    }).catch(function(error){
		    	console.log(" sync POS DATA failed "+error);
		        
		        sync_getCurrentOrderId().then(function(){
					resolve();
				}).catch(function(){
					reject();
				});
		    });
	});
	}
    
       
    //send message to serviceWorker   
    function sendMessage(message,channel_port){


    	if (navigator.serviceWorker!=null && navigator.serviceWorker.controller) {
	 			navigator.serviceWorker.controller.postMessage(message,channel_port);
			} else {
				  navigator.serviceWorker.oncontrollerchange = function() {
				    this.controller.onstatechange = function() {
				      if (this.state === 'activated') {
				    	navigator.serviceWorker.controller.postMessage(message,channel_port);
				      }
				    };
				  };
			}

    		/*checkServiceWorker().then(function(data){
				navigator.serviceWorker.controller.postMessage(message,channel_port);
    		});*/

	}

	//check for serviceWOrker ready
	function syncPOSData(all_data_sync){

		if (navigator.serviceWorker!=null && navigator.serviceWorker.controller) {
	 			order_Sync(all_data_sync);
			} else {
				  navigator.serviceWorker.oncontrollerchange = function() {
				    this.controller.onstatechange = function() {
				      if (this.state === 'activated') {
				    		order_Sync(all_data_sync);
				      }
				    };
				  };
			}
	}


	//check service worker readdy
	function checkServiceWorker(){

		return	new Promise(function(resolve,reject){

			if (navigator.serviceWorker!=null && navigator.serviceWorker.controller) {
	 			resolve(true);
	 			
			} else {
				  navigator.serviceWorker.oncontrollerchange = function() {
				 	   this.controller.onstatechange = function() {
						      if (this.state === 'activated') {
					    			resolve(true);
					      	  }
				    	};
				  };
			}
		});
	}

	//sync pos data offline transations like customer and orders
	function order_Sync(all_data_sync){

		navigator.serviceWorker.ready.
					then(function(reg) {
           				if(reg.sync) {
             				reg.sync.register(SYNC_POS_DATA).
             		  					then(function(data){

             		  					console.log("sync data "+data);
             		  					if(all_data_sync)
             		  						sync_getCurrentOrderId();

             		  					}).catch(function(error){
						
										console.log("sync error "+JSON.stringify(error));
    									if(all_data_sync)
             		  						sync_getCurrentOrderId();         		  
             		  					});

             			}else{
             				console.log("sync not supported");
             				if(all_data_sync)
             		  			sync_getCurrentOrderId();
             			}	
					});
		
    }		 

    //get checksum data 
	function getCheckSumData(check_sumData){

		return new Promise(function (resolve, reject) {

			DATABASE.checksum.where("checksum").equals(check_sumData["checksum"]).
							toArray().then(function(data){

								if(data.length>0){
									return resolve(true);
								}else{

								setCheckSum(check_sumData).then(function(data){
                                     return resolve(data);
									}).catch(function(error){
										return resolve(error);
									});
                               }
							}).catch(function(error){

								setCheckSum(check_sumData).then(function(data){
                                     return resolve(data);
									}).catch(function(error){
										return resolve(error);
									});
							});
		});
			
	}

	//delete the item
	function checksumDelete(check_sumData){
	
			DATABASE.checksum.where("name").
				equals(check_sumData.name).delete();
				
	}

	// save check sum in local DB
	function setCheckSum(check_sumData){

		return new Promise(function (resolve, reject){
		
			SPWAN(function*(){

						checksumDelete(check_sumData);

						savegenralData(check_sumData).
										then(function(data){
											return resolve(data);
										}).catch(function(error){
											return reject(error);		
										});
									


			  });
		});
	}

	//save genral data
	function savegenralData(genralData){

    	return new Promise(function (resolve, reject){
	 
			DATABASE.checksum.put(genralData).then(function(data){
								console.log("set data is "+data);
								//DATABASE.checksum.get(check_sum);
		              			return resolve(data);
							}).catch(function(error){
								console.log("set data error "+error.stack || error);
				                 return reject(false);
							});
		});
	}	


	//save customer in DB
	function setSynCustomerData(customer_data){

        return new Promise(function (resolve, reject){
			DATABASE.sync_customer.put(customer_data).
					then(function(data){
                        resolve(true);                    
					}).catch(function(error){
						reject(error);
					});
		});
	}

	//save offline order in DB
	function setSynOrdersData(order_data){

        return new Promise(function (resolve, reject){

				SPWAN(function*(){

				//get the order id 	
                var order_number= yield DATABASE.checksum.where("name").
              			equals(ORDER_ID).toArray();
              
 				if(order_number.length>0){
              		
              		//add "order id" to order
              		order_data.summary.order_id=order_number[0].checksum;

              		//save order in DB
              		var id=yield DATABASE.sync_orders.put({order:JSON.stringify(order_data)});

              		// update the order id 
		            yield DATABASE.checksum.
		            			update(ORDER_ID,{checksum:++order_number[0].checksum});
		            
		            //return the order id
		            return {"order_id":order_number[0].checksum};		

              	}else{
              		reject(ORDER_ID_UPDATED_ERROR);
              	}

               	}).then(function(order_id){
					resolve(order_id);  
				}).catch(function(error){
					reject(error);
				});
        });
	}

	//get pos sync customers data
	function get_POS_sync_CustomersData(){

       return new Promise(function(resolve,reject){

       		DATABASE.sync_customer.
       				 toArray().
       				 then(function(data){
       				 	console.log("get sync customers "+data.length);
                      	resolve(data);
       				 }).catch(function(error){
					  	  console.log("get sync customers error "+error);
					  	  resolve([]);
       				 });
       });
	}

	//get pos sync orders
	function get_POS_Sync_Orders(){
		return new Promise(function(resolve,reject){
          
          	DATABASE.sync_orders.
          			 toArray().
          			 then(function(data){
                      console.log("get sync pos orders "+data.length);
                      	resolve(data);

          			 }).catch(function(error){
						console.log("get sync pos orders error "+error);
						resolve([]);
          			 });	
		});
	}

	//clear POS sync orders
	function clear_POS_sync_orders(){
	
		return new Promise(function(resolve,reject){
		          
		          	DATABASE.sync_orders.
		          			clear().
		          			then(function(){
		                      console.log("cleared pos sync order table ");
		                      resolve("sucess");

		          			}).catch(function(error){
								console.log("cleared pos sync order table error "+error);
								resolve(error);
		          			});	
				});
	}

	//clear POS sync customers
	function clear_POS_sync_customers(){
	
		return new Promise(function(resolve,reject){
		          
		          	DATABASE.sync_customer.
		          			clear().
		          			then(function(){
		                      console.log("cleared pos sync customers table ");
		                      resolve("sucess");

		          			}).catch(function(error){
								console.log("cleared pos sync customers table error "+error);
								resolve(error);
		          			});	
				});
	}

	//change order id formate like checksum 
	function setOrderID(data){
		if(Object.keys(data).indexOf("order_ids")>=0)
			data.order_id=data.order_ids[0];
		return {"checksum":data[ORDER_ID],"name":"order_id","path":""};
	}

	//change user data foramte like checksum
	function setUserData(data){
		return {"checksum":data,"name":""+USER_DATA,"path":""};
	}


	//get checksumdata based on name
	function getChecsumByName(name){

		return new Promise(function(resolve,reject){

			DATABASE.checksum.where("name").equals(name).toArray().
								then(function(data){
									if(data.length>0){
										resolve(data[0]);
									}else{
										reject();
									}
								}).catch(function(error){
                                      reject();
								});
		});
	}

	//append user id to url
	function appendUserID(url){

		return new Promise(function(resolve,reject){

			getChecsumByName(USER_DATA).
							then(function(result){
								var data=JSON.parse(result.checksum);
	                 			if (data.status == "Success"){
	                 				resolve(url+"&user="+data.parent_id);
	                 			}else{
	                 				resolve(url);
	                 			}

							}).catch(function(){
								resolve(url);
							});
		});				
	}

	async function isStoragePersisted() {
	  return await navigator.storage && navigator.storage.persisted &&
	    navigator.storage.persisted();
	}


	async function persist() {
	  return await navigator.storage && navigator.storage.persist &&
	    navigator.storage.persist();
	}

	async function showEstimatedQuota() {
 	 return await navigator.storage && navigator.storage.estimate ?
    	navigator.storage.estimate() :
    	undefined;
	}

	async function tryPersistWithoutPromtingUser() {
		  if (!navigator.storage || !navigator.storage.persisted) {
		    return "never";
		  }
		  let persisted = await navigator.storage.persisted();
		  if (persisted) {
		    return "persisted";
		  }
		  if (!navigator.permissions || !navigator.permissions.query) {
		    return "prompt"; // It MAY be successful to prompt. Don't know.
		  }
		  const permission = await navigator.permissions.query({
		    name: "persistent-storage"
		  });
		  if (permission.status === "granted") {
		    persisted = await navigator.storage.persist();
		    if (persisted) {
		      return "persisted";
		    } else {
		      throw new Error("Failed to persist");
		    }
		  }
		  if (permission.status === "prompt") {
		    return "prompt";
		  }
		  return "never";
	}


	async function initStoragePersistence() {
	  const persist = await tryPersistWithoutPromtingUser();
	  switch (persist) {
	    case "never":
	      console.log("Not possible to persist storage");
	      break;
	    case "persisted":
	      console.log("Successfully persisted storage silently");
	      break;
	    case "prompt":
	      console.log("Not persisted, but we may prompt user when we want to.");
	      break;
	  }
	}

	function checkPersistent(){

       return new Promise(function(resolve,reject){
		isStoragePersisted().then(async isPersisted => {
		                            if (isPersisted) {
		                              console.log(":) Storage is successfully persisted.");
		                              resolve(true);
		                            } else {
		                              console.log(":( Storage is not persisted.");
		                              console.log("Trying to persist..:");
		                              if (await persist()) {
		                                console.log(":) We successfully turned the storage to be persisted.");
		                              	resolve(true);
		                              } else {
		                                console.log(":( Failed to make storage persisted");
		                              	reject(false);
		                              }
		                            }
		                          });
	});

	}
