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
				 			//checkStoragePercent();
				 			//getData();
					return resolve(true);
					}).catch(Dexie.BulkError,function(error){
					  if(error==Dexie.errnames.QuotaExceeded){
						return reject(error.message);
					  }else{
					   console.log("some sku failed "+ skulist.length()-error.failures.length);
					   return reject("some sku failed "+ skulist.length()-error.failures.length);
					   }
					});

		        }).catch(function(error){
		  			return reject("some sku failed "+ error.message);
		        });
	        });    	
    }

    //add bulk cutomers
	function addCustomerBulkItem(customer_list){

    	return new Promise(function(resolve,reject){
			DATABASE.customer.bulkPut(customer_list).then(function(res){
			 			console.log("data is "+res);
			 			//checkStoragePercent();
						return resolve(true);
				}).catch(Dexie.BulkError,function(error){
					
					if(error==Dexie.errnames.QuotaExceeded){
						return reject(error.message)
					}else{
					console.log("failed to load some customers "+ customer_list.length()-error.failures.length);
				   		return reject("failed to load some customers " + customer_list.length()-error.failures.length);
				   	}
				   
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
	    						startsWithIgnoreCase(find_key).limit(30).
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
								limit(30).toArray().then(function(data){
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


	        	if(event.data!=undefined && event.data.error!=undefined && event.data.error)
	        		reject(event.data.error)
	        	else
	        		resolve(event.data);          
	         };

			sendMessage(sync_type,[msg_chan.port2]);
        
    	});
	}

	//sync get preorders data
	function sync_getPreOrderData(){

		 return new Promise(function(resolve,reject){
		    checkSyncData(GET_PRE_ORDERS,new MessageChannel()).then(function(data){
		    	console.log("GET_PRE_ORDERS sync data "+data);
				
				resolve();
		    }).catch(function(error){
		    	console.log("GET_PRE_ORDERS sync failed "+error);
		        reject();
		    });
	 	});   
	}

	//check sync sku items 
    function sync_SKUData(){
    	return new Promise(function(resolve,reject){

	    checkSyncData(SYNC_SKUMASTER,new MessageChannel()).then(function(data){
	    	console.log("SYNC_SKUMASTER sync data "+data);
	    	sync_getPreOrderData().then(function(){
					resolve();
				}).catch(function(){
					reject();
				});
	    }).catch(function(error){
	    	console.log("SYNC_SKUMASTER sync failed "+error);
	    	sync_getPreOrderData().then(function(){
					resolve();
				}).catch(function(){
					reject();
				});
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
	function checksumDelete(check_sumData_name){
	
		return new Promise(function (resolve, reject){
				DATABASE.checksum.where("name").
					equals(check_sumData_name).delete().then(function(data){
						return resolve(data);
					}).catch(function(error){
						return reject(error.message);
					});
		});			
				
	}

	// save check sum in local DB
	function setCheckSum(check_sumData){

		return new Promise(function (resolve, reject){
		
			SPWAN(function*(){

					yield checksumDelete(check_sumData.name).then(function(data){
							console.log( "clear the "+check_sumData.name +" "+data);
						}).catch(function(error){
							console.log(error);
						});

					yield savegenralData(check_sumData).
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
								//checkStoragePercent();
								//DATABASE.checksum.get(check_sum);
		              			return resolve(data);
							}).catch(function(error){
								console.log("set data error "+error.stack || error.message);	
				                return reject(false);
				                
							});
		});
	}	

	//save customer in DB
	function setSynCustomerData(customer_data){

        return new Promise(function (resolve, reject){
			DATABASE.sync_customer.put(customer_data).
					then(function(data){
						//checkStoragePercent();
                        resolve(true);                    
					}).catch(function(error){
						console.log("set data error "+error.stack || error.message);	
						reject(error.message);
					});
		});
	}

	//save offline order in DB
	function setSynOrdersData(order_data,qty_reduce_status){

        return new Promise(function (resolve, reject){

				SPWAN(function*(){

				//get the order id 	
                var order_number= yield DATABASE.checksum.where("name").
              			equals(ORDER_ID).toArray();
              
 				if(order_number.length>0){
              		
              		
 					var updated_order_id;
              		
              		//check the return status
              		var is_all_return=true;
              		
              		//skus in order
              		var sku_data=order_data.sku_data;

              		//check return items
					for(var sku_item=0;sku_item<sku_data.length;sku_item++){
						if(sku_data[sku_item].return_status.toString()!="true"){
							is_all_return=false;
							break;
						}
					}

					//add "order id" to order
					if(is_all_return==false){
						order_data.summary.order_id=order_number[0].checksum;
	              		updated_order_id=++order_number[0].checksum;
	              	}else{
						updated_order_id=order_number[0].checksum;
						order_data.summary.order_id=--order_number[0].checksum;
						//order_data.summary.status="0";
	              	}

              		//reduce sku qty
              		if(qty_reduce_status){
					yield reduceSKUQty(order_data).then(function(){
						console.log("sucess to reduce sku qty ");
					}).catch(function(error){
						console.log("error at reduce sku qty "+error.message);
					});
					}

              		//save order in DB
              		var id=yield DATABASE.sync_orders.
              						put({"order_id":JSON.stringify(order_data.summary.order_id),
              							"order":JSON.stringify(order_data)}).then(function(data){
              								console.log("data saved in local db "+data);	
              						}).catch(function(error){
										console.error("error "+error.message);	
										return reject(error.message);
									});

              		// update the order id 
		            yield DATABASE.checksum.
		            			update(ORDER_ID,{checksum:updated_order_id});
		            
		            //return the order id
		            return {"order_id":order_data.summary.order_id};		

              	}else{
              		reject(ORDER_ID_UPDATED_ERROR);
              	}

               	}).then(function(order_id){
					return resolve(order_id);  
				}).catch(function(error){
					return reject(error.message);
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

	//sync POS  preorder 
	function get_transaction_POS_PreOrders(){

		return new Promise(function(resolve,reject){
		
				var delivered_ids=[];
				
				getOffline_PreOrder_DeliveredData().then(function(data){
					delivered_ids=data;
					if(delivered_ids.length>0){
						
						preparePreOrderTransactions(delivered_ids).
							then(function(delivered_data){
							return resolve(delivered_data);
						});				
	
					}else{
						return resolve([]);
					}		
				});

		}).catch(function(error){
				return  resolve([]);
			});	
	}

	//prepare preorder offline delivered details
	function preparePreOrderTransactions(delivered_ids){

		return new Promise(function (resolve, reject){

			SPWAN(function*(){
				var preorder_delivered_details=[];
				getUserID().then(function(data){
						if(data!=undefined){

							for(var delivered_id=0;delivered_id<delivered_ids.length;delivered_id++){
								preorder_delivered_details.push({'user':data, 'order_id':delivered_ids[delivered_id]});

								if(delivered_ids.length==delivered_id+1){
									return resolve(preorder_delivered_details);
								}
							}	

						}else{
							return resolve([]);
						}
				});

			});
		});		

	}


	 function delivered_preorder_details(delivered_ids) {

		return new Promise(function (resolve, reject){

				SPWAN(function*(){

				var preorder_delivered_details=[];
				 	
				for(var delivered_id=0;delivered_id<delivered_ids.length;delivered_id++){

							yield getPreOrderData(delivered_ids[delivered_id]).then(function(data){

								if(data.length>0){
									var val=JSON.parse(data[0].order_data);
									if(val.status!=0){
										val.status=0;
									}
									preorder_delivered_details.push(val);
								}
								if(delivered_ids.length==delivered_id+1){
									return resolve(preorder_delivered_details);
								}
							});
						}
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

	//get POS sync orders
	function get_POS_Sync_OrdersByID(pos_sync_orer_id){
		return new Promise(function(resolve,reject){
          
          	DATABASE.sync_orders.where("order_id").equals(pos_sync_orer_id).
          			 toArray().
          			 then(function(data){
                      console.log("get sync pos orders "+data.length);
                      	if(data.length>0){
                      		return resolve(data);
						}else{
							return resolve([]);
						}
          			 });	
		});
				
	}

	//get Customers data
	function getcustomerData(){
		return new Promise(function(resolve,reject){
		
			DATABASE.customer.toArray()
					.then(function(data){
						return resolve(data);
					}).catch(function(error){
						return resolve([]);
					});
		});
	}

	//get skumasres data
	function getSkumasterData(){
		return new Promise(function(resolve,reject){
		
			DATABASE.skumaster.toArray()
					.then(function(data){
						return resolve(data);
					}).catch(function(error){
						return resolve([]);
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
	function setCheckSumFormate(data,name){
		return {"checksum":data,"name":""+name,"path":""};
	}


	//get checksumdata based on name
	function getChecsumByName(name){

		return new Promise(function(resolve,reject){

			DATABASE.checksum.where("name").equals(name).toArray().
								then(function(data){
									if(data.length>0){
										return resolve(data[0]);
									}else{
										return  reject();
									}
								}).catch(function(error){
                                      return  reject();
								});
		});
	}

	//append user id to url
	function getUserID(){

		return new Promise(function(resolve,reject){

			getChecsumByName(USER_DATA).
							then(function(result){
								var data=JSON.parse(result.checksum);
	                 			if (data.status == "Success"){
	                 				return resolve(data.parent_id);
	                 			}else{
	                 				return resolve();
	                 			}

							}).catch(function(){
								return resolve();
							});
		});				
	}

	function appendUserID(url,id){
		if(id!=undefined)
			return url+"&user="+id;
		else
		return url;
	}

	//get storage percentage
	function GetStorage_Percentage(){

		return new Promise(function(resolve,reject){
			showEstimatedQuota().then(function(quota){
				if(quota!=undefined){
				  	return (quota.usage/quota.quota)*100;
				}else{
					return 0.00;
				}

			}).then(function(data){
				return resolve(data.toFixed(2));
			}).catch(function(error){
				return reject(error.message);
			});
		});
	}

	//check usage percent 
	function checkStoragePercent(){

		return new Promise(function(resolve,reject){
			GetStorage_Percentage().then(function(data){
				if(data>=70.00){
					return resolve(true);
				}else{
					return resolve(false);
				}
			}).catch(function(error){
				return reject(error);
			});		
		});
	}

	//reduce sku qty in IndexDB
	async function reduceSKUQty(data){

		
		if(data.sku_data.length>0 && data.status==0){
			
             
            for(var i=0;i<data.sku_data.length;i++){
				
				await DATABASE.skumaster.where("SKUCode").
             					equals(data.sku_data[i].sku_code).
             					modify(function(sku){
             						sku.stock_quantity=sku.stock_quantity-data.sku_data[i].quantity;
             					}).then(function(data){
             						console.log("sucessfully updated "+data);
             					}).catch(function(error){
             						console.log(error.message);
             					});
            }
        }
	}

	//Bulk add pre-orders data
	function addPreOrdersBulkItems(preoder_data){

		return new Promise(function(resolve,reject){

			 DATABASE.transaction('rw', DATABASE.pre_orders,function () {

				  var data=[];

				  Object.keys(preoder_data).forEach(function(key){

				  		data.push({"order_id":key,"order_data":JSON.stringify(preoder_data[key])});

				  });

				    	 	
				DATABASE.pre_orders.bulkPut(data).then(function(res){
				 			console.log("add bulk predorder data is "+res);
				 			
							return resolve(true);
				}).catch(function(error){
					  if(error==Dexie.errnames.QuotaExceeded){
						return reject(error.message);
					  }else if(error==Dexie.BulkError){
					   console.log("some preorders saving failed "+ data.length()-error.failures.length);
					   return reject("some preorder saving failed "+ data.length()-error.failures.length);
					   }
				});
	        }).catch(function(error){
	        	return reject("some preorder saving failed "+ error.message);
	        });   	
		});
	}

	//get preorder data using order_id
	function getPreOrderData(order_id){

		return new Promise(function(resolve,reject){

			DATABASE.pre_orders.
						where("order_id").equals(order_id).toArray().
								then(function(data){
									return resolve(data);
								}).catch(function(error){
									return resolve([]);
								});
		});					
	}

	//get the preorder data check with offline preorder delivered 
	function getPreOrderDetails_Check_Off_Delivered(order_id){

		return new Promise(function(resolve,reject){
				var order_data="",order_find=false;

			//check order id length	
			if(order_id.length>0){	

				 getPreOrderData(order_id).then(function(result){
					 if(result.length>0){
		              		order_data=JSON.parse(result[0].order_data);
		              		
		              		getOffline_PreOrder_DeliveredData().then(function(data){

			              	if(data.length>0 && data.indexOf(order_id)>=0){
			              		order_data.status=0;
			              		return resolve(order_data);
			              	}else{
			              		return resolve(order_data);
			              	}
			              });

		          	  }else{
		          		get_POS_Sync_OrdersByID(order_id).then(function(data){
		          	  		if(data.length>0){
		          	  			order_data=JSON.parse(data[0].order);
		          	  			var preorder_data={"customer_data":order_data.customer_data,
							                "sku_data":order_data.sku_data,
							                  "order_id":order_data.summary.order_id,
							                  "order_date":order_data.summary.order_date,
							                   "status":order_data.status};
					              
		          	  			getOffline_PreOrder_DeliveredData().then(function(data){

					              	if(data.length>0 && data.indexOf(order_id)>=0){
					              			preorder_data.status=0;
			              					return resolve(preorder_data);
					              	}else{
					              		return resolve(preorder_data);
					              	}
					            });

		          	  		}else{
		          	  			return resolve({});
		          	  		}
		          	  	});
		          	  }

				}).catch(function(error){
					return resolve({});
				});

			}else{

				//return all preorders

				var all_pre_orders={};
				var pre_order_data=[];
				var sync_pre_orders=[];
				
				//get all peorders in preorder where status is 1.
				DATABASE.pre_orders.filter(function(data){

						data=JSON.parse(data.order_data);
						if(data.status.toString()=="1")
							return true;	
				}).toArray().then(function(data){

					pre_order_data=data;

					//get all orders where issuetype is "pre order".
					DATABASE.sync_orders.filter(function(data){
						data=JSON.parse(data.order);
						if(data.summary.issue_type="Pre order"){
							return true;
						}
					}).toArray().then(function(preorders){
						
								sync_pre_orders=preorders;				
						
						//get the offline preorder delivered order id's
						getOffline_PreOrder_DeliveredData().then(function(data){


							//checkwith preorder order id
							for(var pre_order=0;pre_order<pre_order_data.length;pre_order++){

								if(data.indexOf(pre_order_data[pre_order].order_id)>0){
									pre_order_data.splice(pre_order);								
								}else{
									all_pre_orders[pre_order_data[pre_order].order_id]=(JSON.parse(pre_order_data[pre_order].order_data));
									
								}		
							}
							
							//check with sync order order id
							for(var pre_order=0;pre_order<sync_pre_orders.length;pre_order++){
								if(data.indexOf(sync_pre_orders[pre_order].order_id)>0){
									sync_pre_orders.splice(pre_order,1);								
								}else{
									var order_data=JSON.parse(sync_pre_orders[pre_order].order);
						
									all_pre_orders[sync_pre_orders[pre_order].order_id]={"customer_data":order_data.customer_data,
							                "sku_data":order_data.sku_data,
							                  "order_id":order_data.summary.order_id,
							                  "order_date":order_data.summary.order_date,
							                   "status":order_data.status};

								}

							}

							//return all preorders.
							return resolve({"data":all_pre_orders});
	
							});


					});

				});

			}	

			});	
	}

	//change the preorder status
	function setPreOrderStatus(order_id,status){
		
		return new Promise(function(resolve,reject){

			 SPWAN(function*(){

			 	//getting order from preorder
				var orders= yield DATABASE.pre_orders.
							where("order_id").equals(order_id).toArray();

				if(orders.length>0){
					var order_data=JSON.parse(orders[0].order_data);
					if(Object.keys(order_data).indexOf("status")>0){
						order_data.status=status;

					//reduce sku qty
					reduceSKUQty(order_data).then(function(){
						console.log("sucess to reduce sku qty ");
					}).catch(function(error){
						console.log("error at reduce sku qty "+error.message);
					});	

						yield DATABASE.pre_orders.
							where("order_id").equals(order_id).
								modify(function(data){
									data.order_data=JSON.stringify(order_data);
								}).then(function(data){
									console.log("changed the sstatus o preorder "+JSON.stringify(data));
								}).catch(function(error){
									return reject(error.message);
								});		

						 getOffline_PreOrder_DeliveredData().
									then(function(delivered_ids){

										delivered_ids.push(order_id);
										savegenralData(setCheckSumFormate(
											delivered_ids.toString(),OFFLINE_DELIVERED)).
													then(function(data){
														return resolve(true);
													}).catch(function(error){
															return reject(true);
													});

									});		

					}else{
						return reject({});
					}
				}else{

					//check order in syn_orders
					get_POS_Sync_OrdersByID(order_id).toArray().
								then(function(data){
									if(data.length>0){

										var order_data=JSON.parse(data[0].order);
										if(Object.keys(order_data).indexOf("status")>0){
											order_data.status=status;
											//reduce sku qty
											 reduceSKUQty(order_data).then(function(){
												console.log("sucess to reduce sku qty ");
											}).catch(function(error){
												console.log("error at reduce sku qty "+error.message);
											});	

											//store at offline deliverred items in checksum
											 getOffline_PreOrder_DeliveredData().
												then(function(delivered_ids){

													delivered_ids.push(order_id);
													savegenralData(setCheckSumFormate(
														delivered_ids.toString(),OFFLINE_DELIVERED)).
																then(function(data){
																	return resolve(true);
																}).catch(function(error){
																		return reject(true);
																});

												});	

										}else{
											return reject("order has not a status");
										}

									}else{
										return reject("unable to get the order information in offline");
										}		
								}).catch(function(error){
									return reject(error.message);
								});
					
				}
								
			}).catch(function(error){
				return reject(error.message);
			});					
		});	

	}

	//get offline delivered data
	function getOffline_PreOrder_DeliveredData(){

		return new Promise(function(resolve,reject){
			getChecsumByName(OFFLINE_DELIVERED).then(function(data){
								var delivered_ids=data.checksum.split(",");
									return resolve(delivered_ids);
							}).catch(function(error){
									return resolve([]);
							});
		});			
	
	}
