"use strict";

    //add bulk sukitems
    function addSKUBulkItem(skulist){
        console.log("got the bulk skuitems "+skulist.length);
        return new Promise(function(resolve,reject){
            openDB().then(function(){

            DATABASE.transaction('rw', POS_TABLES.skumaster, POS_TABLES.sku_search_words,
                function () {

                    SPWAN(function*(){
                                                
                        yield POS_TABLES.skumaster.clear();
                        console.log("clear all the local sku master"); 

                        for(var skudata=1;skudata<=skulist.length;skudata++){

                            yield POS_TABLES.skumaster.bulkPut(skulist.slice(0,1000)).then(function(res){
                                    
                                    console.log("sku successfully insert the list "+skudata +" of 1000 items");
                                    skulist.splice(0,1000);
                                    console.log("sku remove the list "+skudata +" of 1000 items");
                                    }).catch(Dexie.BulkError,function(error){
                                    if(error==Dexie.errnames.QuotaExceeded){
                                        return reject(error.message);
                                    }else{
                                        console.log("some sku failed "+ error.failures.length);
                                        return reject("some sku failed "+ error.failures.length);
                                    }
                                });

                            if(skulist.length==0){
                                return resolve(true);
                            }        
                                    
                        }  

                    }).catch(function(error){
                        return reject("some sku failed "+ error.message);
                    });

                });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });     
    }

    //add bulk cutomers
    function addCustomerBulkItem(customer_list){

        return new Promise(function(resolve,reject){
            openDB().then(function(){

            SPWAN(function*(){
                yield POS_TABLES.customer.clear();

                for(var customer_data=1;customer_data<=customer_list.length;customer_data++){
                    yield POS_TABLES.customer.bulkPut(customer_list.splice(0,1000)).then(function(res){
                                     console.log("data is "+res);
                                    //checkStoragePercent();
                                     console.log("customer successfully insert the list "+customer_data +" of 1000 items");
                                    customer_list.splice(0,1000);
                                    console.log("customer remove the list "+customer_data +" of 1000 items");
                                    
                                }).catch(Dexie.BulkError,function(error){

                                    if(error==Dexie.errnames.QuotaExceeded){
                                        return reject(error.message)
                                    }else{
                                        console.log("failed to load some customers "+ error.failures.length);
                                        return reject("failed to load some customers " + error.failures.length);
                                    }
                                    
                                });

                    if(customer_list.length==0){
                        return resolve(true);
                    }              
                }
                });   

            }).catch(function(error){
                console.log(error);
                return reject(error);
            });             
        });
    }


    //serach sku items
    function getData(find_key){

        return new Promise(function(resolve,reject){

            openDB().then(function(){

            DATABASE.transaction('rw', POS_TABLES.skumaster, POS_TABLES.sku_search_words,
                function () {

                    if(find_key!=undefined && find_key.length>0){
                        var foundIds = {};
                        POS_TABLES.sku_search_words.where("word").
                        startsWithIgnoreCase(find_key).limit(200).
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
                            
                            POS_TABLES.skumaster.where("SKUCode").
                            anyOf(sku_ids).toArray().
                            then(function(skus){
                                return resolve(skus);
                            }).catch(function(error){
                                console.log('collection error ' +err);
                                return resolve([]);
                            });
                                            
                        });
                    }else{
                        POS_TABLES.skumaster.toArray().
                                then(function(skus){
                                    return resolve(skus);
                                }).catch(function(error){
                                    console.log('collection error ' +err);
                                    return resolve([]);
                                });
                        
                    }
                }).catch(function (e) {
                    console.log(e.stack || e);
                    return resolve([]);
                }); 
             }).catch(function(error){
                console.log(error);
                return reject(error);
            }); 

            });
        
    }

    //search customer
    function getCustomerData(find_key){

        return new Promise(function(resolve,reject){
            openDB().then(function(){
            POS_TABLES.customer.where("Number").
            startsWithIgnoreCase(find_key).
            or("FirstName").startsWithIgnoreCase(find_key).
            limit(30).toArray().then(function(data){

                if(data.length>0){
                    return resolve(data);   
                }else{

                    POS_TABLES.sync_customer.where("number").
                    startsWithIgnoreCase(find_key).
                    or("firstName").startsWithIgnoreCase(find_key).
                    limit(30).toArray().then(function(data){

                        var data_list=[],user={};

                        for(var user_list=0;user_list<data.length;user_list++){
                            user=data[user_list];
                            data_list.push({"FirstName":user.firstName,"Address":"","Email":user.mail,"ID":'',"LastName":user.secondName,"Number":""+user.number});
                        }

                        return resolve(data_list);
                    }).catch(function(error){
                        return reject(error);
                    });
                }
                
            }).catch(function(error){
                return reject(error);
            });

           }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
    }

    //check table in DATABASE
    function checktable(table_name){

        return new Promise(function(resolve,reject){
            openDB().then(function(){
            var count=DATABASE.tables.length;
            var count_item=0; 
            DATABASE.tables.forEach(function(table) {
                count_item++;
                if(table.name==table_name){
                    console.log("Schema of " + table.name + ": " + JSON.stringify(table.schema));   
                   return resolve(true) ;
                }else if(count_item==count){
                   return reject(false);
                }
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        }); 

        
    }

    //check sync data
    function checkSyncData(sync_type,messagechannel){
        console.log("call post message "+sync_type);

        return new Promise(function(resolve, reject){
            var msg_chan =messagechannel;

            msg_chan.port1.onmessage = function(event){


                if(event.data!=undefined && event.data.error!=undefined && event.data.error)
                    return reject(event.data.error)
                else
                    return resolve(event.data);          
            };

            sendMessage(sync_type,[msg_chan.port2]);
            
        });
    }

    //sync get preorders data
    function sync_getPreOrderData(){

        return new Promise(function(resolve,reject){
            checkSyncData(GET_PRE_ORDERS,new MessageChannel()).then(function(data){
                console.log("GET_PRE_ORDERS sync data "+data);
                
               return resolve();
            }).catch(function(error){
                console.log("GET_PRE_ORDERS sync failed "+error);
               return reject();
            });
        });   
    }

    //check sync sku items 
    function sync_SKUData(){
        return new Promise(function(resolve,reject){

            checkSyncData(SYNC_SKUMASTER,new MessageChannel()).then(function(data){
                console.log("SYNC_SKUMASTER sync data "+data);
                sync_getPreOrderData().then(function(){
                   return resolve();
                }).catch(function(){
                   return reject();
                });
            }).catch(function(error){
                console.log("SYNC_SKUMASTER sync failed "+error);
                sync_getPreOrderData().then(function(){
                   return resolve();
                }).catch(function(){
                   return reject();
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
                   return resolve();
                }).catch(function(){
                   return reject();
                });
            }).catch(function(error){
                console.log("SYNC_CUSTOMERMASTER sync failed "+error);
                sync_SKUData().then(function(){
                   return resolve();
                }).catch(function(){
                   return reject();
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
                   return resolve();
                }).catch(function(){
                   return reject();
                });
                
            }).catch(function(error){
                console.log("GET_CURRENT_ORDER sync failed "+error);

                syncCustomerData().then(function(){
                   return resolve();
                }).catch(function(){
                   return reject();
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
                   return resolve();
                }).catch(function(){
                   return reject();
                });
                
            }).catch(function(error){
                console.log(" sync POS DATA failed "+error);

                sync_getCurrentOrderId().then(function(){
                   return resolve();
                }).catch(function(){
                   return reject();
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

        return  new Promise(function(resolve,reject){       

            if (navigator.serviceWorker!=null && navigator.serviceWorker.controller) {
                order_Sync(all_data_sync).then(function(){
                    return resolve();
                });
            } else {
                navigator.serviceWorker.oncontrollerchange = function() {
                    this.controller.onstatechange = function() {
                        if (this.state === 'activated') {
                            order_Sync(all_data_sync).then(function(){
                                return resolve();
                            });
                        }
                    };
                };
            }
        }); 
    }

    //check service worker readdy
    function checkServiceWorker(){

        return  new Promise(function(resolve,reject){

            if (navigator.serviceWorker!=null && navigator.serviceWorker.controller) {
               return resolve(true);
                
            } else {
                navigator.serviceWorker.oncontrollerchange = function() {
                    this.controller.onstatechange = function() {
                        if (this.state === 'activated') {
                          return resolve(true);
                        }
                    };
                };
            }
        });
    }

    //sync pos data offline transations like customer and orders
    function order_Sync(all_data_sync){

        return  new Promise(function(resolve,reject){
            navigator.serviceWorker.ready.
            then(function(reg) {
                if(reg.sync) {
                    reg.sync.register(SYNC_POS_DATA).
                    then(function(data){

                        console.log("sync data "+data);
                        if(all_data_sync){
                            sync_getCurrentOrderId().then(function(){
                                return resolve();   
                            });
                            
                        }else{
                            return resolve();
                            
                        }
                    }).catch(function(error){

                        console.log("sync error "+JSON.stringify(error));
                        
                        if(all_data_sync){
                            sync_getCurrentOrderId().then(function(){
                                return resolve();   
                            });
                            
                        }else{
                            return resolve();    
                        }
                    });

                }else{
                    console.log("sync not supported");
                    if(all_data_sync){
                        sync_getCurrentOrderId().then(function(){
                            return resolve();   
                        });
                        
                    }else{
                        return resolve();
                    }
                }   
            });
        });         
        
    }        

    //get checksum data 
    function getCheckSumData(check_sumData){

        return new Promise(function (resolve, reject) {
            openDB().then(function(){

            POS_TABLES.checksum.where("checksum").equals(check_sumData["checksum"]).
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
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
        
    }

    //delete the item
    function checksumDelete(check_sumData_name){

        return new Promise(function (resolve, reject){
            openDB().then(function(){
            POS_TABLES.checksum.where("name").
            equals(check_sumData_name).delete().then(function(data){
                return resolve(data);
            }).catch(function(error){
                return reject(error.message);
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
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
            openDB().then(function(){

            POS_TABLES.checksum.put(genralData).then(function(data){
                console.log("set data is "+data);
                                //checkStoragePercent();
                                //DATABASE.checksum.get(check_sum);
                                return resolve(data);
                            }).catch(function(error){
                                console.log("set data error "+error.stack || error.message);    
                                return reject(false);
                                
                            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
            });
    }   

    //save customer in DB
    function setSynCustomerData(customer_data){

        return new Promise(function (resolve, reject){
            openDB().then(function(){
            POS_TABLES.sync_customer.put(customer_data).
            then(function(data){
                        //checkStoragePercent();
                       return resolve(true);                    
                    }).catch(function(error){
                        console.log("set data error "+error.stack || error.message);    
                       return reject(error.message);
                    });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
            });
    }

    //save offline order in DB
    function setSynOrdersData(order_data,qty_reduce_status){

        return new Promise(function (resolve, reject){
            openDB().then(function(){

            SPWAN(function*(){

                //get the order id  
                var order_number= yield POS_TABLES.checksum.where("name").
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
                    yield reduceSKUQty(order_data).then(function(){
                        console.log("sucess to reduce sku qty ");
                    }).catch(function(error){
                        console.log("error at reduce sku qty "+error.message);
                    });

                    //save order in DB
                    var id=yield POS_TABLES.sync_orders.
                    put({"order_id":JSON.stringify(order_data.summary.order_id),
                        "order":JSON.stringify(order_data)}).then(function(data){
                            console.log("data saved in local db "+data);    
                        }).catch(function(error){
                            console.error("error "+error.message);  
                            return reject(error.message);
                        });

                    // update the order id 
                    yield POS_TABLES.checksum.
                    update(ORDER_ID,{checksum:updated_order_id});
                    
                    //return the order id
                    return {"order_id":order_data.summary.order_id,"is_all_return":is_all_return};      

                }else{
                   return reject(ORDER_ID_UPDATED_ERROR);
                }

            }).then(function(order_id){
                return resolve(order_id);  
            }).catch(function(error){
                return reject(error.message);
            });
        }).catch(function(error){
                console.log(error);
                return reject(error);
        });   
        });
    }

    
    //get pos sync customers data
    function get_POS_sync_CustomersData(){
        console.log("call sync customer data");

        return new Promise(function(resolve,reject){
            openDB().then(function(){
            POS_TABLES.sync_customer.
            toArray().
            then(function(data){
                console.log("get sync customers "+data.length);
                return resolve(data);
            }).catch(function(error){
                console.log("get sync customers error "+error);
               return resolve([]);
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
    }

    //sync POS  preorder 
    function get_transaction_POS_PreOrders(){

        return new Promise(function(resolve,reject){
            getOrderDeliveredItems("").then(function(data){

                if(data.length>0){
                    return resolve(data);
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
            openDB().then(function(){
            POS_TABLES.sync_orders.
            toArray().
            then(function(data){
                console.log("get sync pos orders "+data.length);
                return resolve(data);

            }).catch(function(error){
                console.log("get sync pos orders error "+error);
                return resolve([]);
            }); 
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
    }

    //get POS sync orders
    function get_POS_Sync_OrdersByID(pos_sync_orer_id){
        return new Promise(function(resolve,reject){
            openDB().then(function(){
            POS_TABLES.sync_orders.where("order_id").equals(pos_sync_orer_id).
            toArray().
            then(function(data){
                console.log("get sync pos orders "+data.length);
                if(data.length>0){
                    return resolve(data);
                }else{
                    return resolve([]);
                }
            }); 
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
        
    }

    //get Customers data
    function getcustomerData(){
        return new Promise(function(resolve,reject){
            openDB().then(function(){
            POS_TABLES.customer.toArray()
            .then(function(data){
                return resolve(data);
            }).catch(function(error){
                return resolve([]);
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
    }

    //get skumasres data
    function getSkumasterData(){
        return new Promise(function(resolve,reject){
            openDB().then(function(){
            POS_TABLES.skumaster.toArray()
            .then(function(data){
                return resolve(data);
            }).catch(function(error){
                return resolve([]);
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
    }

    //clear POS sync orders
    function clear_POS_sync_orders(){

        return new Promise(function(resolve,reject){
            openDB().then(function(){    
            POS_TABLES.sync_orders.
            clear().
            then(function(){
                console.log("cleared pos sync order table ");
                return resolve("sucess");

            }).catch(function(error){
                console.log("cleared pos sync order table error "+error);
                return resolve(error);
            }); 
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
    }

    //clear POS sync customers
    function clear_POS_sync_customers(){

        return new Promise(function(resolve,reject){
            openDB().then(function(){
            POS_TABLES.sync_customer.
            clear().
            then(function(){
                console.log("cleared pos sync customers table ");
                return resolve("sucess");

            }).catch(function(error){
                console.log("cleared pos sync customers table error "+error);
                return resolve(error);
            }); 
            }).catch(function(error){
                console.log(error);
                return reject(error);
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
            openDB().then(function(){
            POS_TABLES.checksum.where("name").equals(name).toArray().
            then(function(data){
                if(data.length>0){
                    return resolve(data[0]);
                }else{
                    return  reject();
                }
            }).catch(function(error){
                return  reject();
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
    }

    //append user id to url
    function getUserID(){

        return new Promise(function(resolve,reject){
            openDB().then(function(){
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
            }).catch(function(error){
                console.log(error);
                return reject(error);
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
                    var storage_per=(quota.usage/quota.quota)*100;
                    console.log("used percentage is "+storage_per);
                    return storage_per; 
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

                await POS_TABLES.skumaster.where("SKUCode").
                equals(data.sku_data[i].sku_code).
                modify(function(sku){

                    if(sku.stock_quantity>=data.sku_data[i].quantity)
                        sku.stock_quantity=sku.stock_quantity-data.sku_data[i].quantity;
                    else
                        sku.stock_quantity=0;

                }).then(function(data){
                    console.log("sucessfully updated "+data);
                }).catch(function(error){
                    console.log(error.message);
                });
            }
        }
        
    }

    //Bulk add pre-orders data
    function addPreOrdersBulkItems(data_preoder_list){

        console.log("get the bulk preorders "+Object.keys(data_preoder_list).length);
        var preoder_list=Object.keys(data_preoder_list);
        return new Promise(function(resolve,reject){

            openDB().then(function(){
            DATABASE.transaction('rw', POS_TABLES.pre_orders,function () {

                SPWAN(function*(){
                    
                    yield POS_TABLES.pre_orders.clear();
                    console.log("clear all the local preorders");

                    for(var preorder_item=1;preorder_item<=preoder_list.length;preorder_item++){

                        var preorderData=preoder_list.slice(0,1000);

                        var data=[];
                           for(var key=1;key<=preorderData.length;key++){
                            var preoder_key=preorderData[key];
                            data.push({order_id:preoder_key,
                                order_data:JSON.stringify(data_preoder_list[preoder_key])});
                           }                                             
                        /*Object.keys(preorderData).forEach(function(key){
                            data.push({"order_id":key,"order_data":JSON.stringify(preoder_list[key])});
                        });*/

                        yield POS_TABLES.pre_orders.bulkPut(data).then(function(res){
                            console.log("add bulk predorders data is "+res);
                            console.log("sku successfully insert the list "+preorder_item +" of 1000 items");
                             preoder_list.splice(0,1000);
                             console.log("sku remove the list "+preorder_item +" of 1000 items");
                            
                            
                        }).catch(function(error){
                            console.log("get an error adding bulk preorders "+error.stack);
                            if(error==Dexie.errnames.QuotaExceeded){
                                return reject(error.message);
                            }else if(error==Dexie.BulkError){
                                console.log("some preorders saving failed "+error.failures.length);
                                return reject("some preorder saving failed "+error.failures.length);
                            }
                            preoder_list.splice(0,1000);

                        });

                        if(preoder_list==0){
                                return resolve(true);
                            }
                        
                    }
                });
            }).catch(function(error){
                return reject("some preorder saving failed "+ error.message);
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
            
        });
    }

    //get preorder data using order_id
    function getPreOrderData(order_id){

        return new Promise(function(resolve,reject){
            openDB().then(function(){
            POS_TABLES.pre_orders.
            where("order_id").equals(order_id).toArray().
            then(function(data){
                return resolve(data);
            }).catch(function(error){
                return resolve([]);
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
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
                        
                        getOrderDeliveredItems(order_id).then(function(data){

                            if(data.length>0){
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
                                order_data.customer_data.Name=order_data.customer_data.FirstName;
                                var preorder_data={"customer_data":order_data.customer_data,
                                "sku_data":order_data.sku_data,
                                "order_id":order_data.summary.order_id,
                                "order_date":order_data.summary.order_date,
                                "status":order_data.status};

                                getOrderDeliveredItems(order_id).then(function(data){

                                    if(data.length>0){
                                        order_data.status=0;
                                        return resolve(order_data);
                                    }else{
                                        return resolve(order_data);
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
                openDB().then(function(){
                //get all peorders in preorder where status is 1.
                POS_TABLES.pre_orders.filter(function(data){

                    data=JSON.parse(data.order_data);
                    if(data.status.toString()=="1")
                        return true;    
                }).toArray().then(function(data){

                    pre_order_data=data;

                    //get all orders where issuetype is "pre order".
                    POS_TABLES.sync_orders.filter(function(data){
                        data=JSON.parse(data.order);
                        if(data.summary.issue_type.toLowerCase()==="pre order" && data.status==="1"){
                            return true;
                        }
                    }).toArray().then(function(preorders){

                        sync_pre_orders=preorders;              
                        
                        //get the offline preorder delivered order id's
                        getOrderDeliveredItems("").then(function(order_data){

                            var data=[];
                            for(var orders=0;orders<order_data.length;orders++){
                                data.push(order_data[orders].order_id);
                            }


                            //checkwith preorder order id

                            for(var pre_order=0;pre_order<pre_order_data.length;pre_order++){


                                if(data.length==0 || data.indexOf(pre_order_data[pre_order].order_id)==-1){
                                    all_pre_orders[pre_order_data[pre_order].order_id]=(JSON.parse(pre_order_data[pre_order].order_data));
                                }       
                            }
                            
                            //check with sync order order id
                            for(var pre_order=0;pre_order<sync_pre_orders.length;pre_order++){
                                if(data.length==0 ||  data.indexOf(sync_pre_orders[pre_order].order_id)==-1){
                                    var order_data=JSON.parse(sync_pre_orders[pre_order].order);
                                    order_data.customer_data.Name=order_data.customer_data.FirstName;
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
                }).catch(function(error){
                    console.log(error);
                    return reject(error);
                });
            }   

        }); 
    }

    //change the preorder status
    function setPreOrderStatus(order_id,status,delete_order){

        return new Promise(function(resolve,reject){
            openDB().then(function(){
            SPWAN(function*(){

                var user_id="";
                //get user id
                yield getUserID().then(function(id){
                    user_id=id;
                });

                //getting order from preorder
                var orders= yield POS_TABLES.pre_orders.
                where("order_id").equals(order_id).toArray();

                if(orders.length>0){
                    var order_data=JSON.parse(orders[0].order_data);
                    if(Object.keys(order_data).indexOf("status")>0){
                        order_data.status=status;

                    //reduce sku qty
                    if(delete_order=="false"){
                        reduceSKUQty(order_data).then(function(){
                            console.log("sucess to reduce sku qty ");
                        }).catch(function(error){
                            console.log("error at reduce sku qty "+error.message);
                        }); 
                    }

                    yield POS_TABLES.pre_orders.
                    where("order_id").equals(order_id).
                    modify(function(data){
                        data.order_data=JSON.stringify(order_data);
                    }).then(function(data){
                        console.log("changed the sstatus o preorder "+JSON.stringify(data));
                    }).catch(function(error){
                        return reject(error.message);
                    });     

                    setOrderDeliveredItems(user_id,order_id,delete_order).
                    then(function(data){
                        var result_data={};
                         result_data.data=data;
                        if(delete_order=="true"){
                            result_data.message="Deleted Successfully !";
                            return resolve(result_data);
                        } else{
                           if(result_data.data.status){
                                result_data.data.status="sucess";
                            }
                            result_data.message="Delivered Successfully !";
                            return resolve(result_data);
                        }
                    }).catch(function(error){
                        return reject(error.message);
                    });

                }else{
                    return reject({});
                }
            }else{

                    var sync_order_data=[];
                    //check order in syn_orders
                    yield get_POS_Sync_OrdersByID(order_id).
                    then(function(data){
                        sync_order_data=data;
                            
                    }).catch(function(error){
                        return reject(error.message);
                    });

                    if(sync_order_data.length>0){
                        var order_data=JSON.parse(sync_order_data[0].order);
                        if(Object.keys(order_data).indexOf("status")>0){
                            order_data.status=status;
                             //reduce sku qty
                            reduceSKUQty(order_data).then(function(){
                                console.log("sucess to reduce sku qty ");
                            }).catch(function(error){
                                console.log("error at reduce sku qty "+error.message);
                            }); 
                                        
                           yield POS_TABLES.sync_orders.
                                    where("order_id").equals(order_id).
                                    modify(function(data){
                                        data.order=JSON.stringify(order_data);
                                    }).then(function(data){
                                        console.log("changed the status of preorder "+JSON.stringify(data));
                                    }).catch(function(error){
                                        return reject(error.message);
                                    }); 

                            yield setOrderDeliveredItems(user_id,order_id,delete_order).
                                    then(function(data){
                                        var result_data={};
                                        result_data.data={};
                                        result_data.data.data=order_data;
                                        if(delete_order=="true"){
                                            result_data.message="Deleted Successfully !";
                                            return resolve(result_data);
                                        } else{
                                            if(result_data.data.status){
                                                result_data.data.status="sucess";
                                            }
                                            result_data.message="Delivered Successfully !";
                                            return resolve(result_data);
                                        }
                                    }).catch(function(error){
                                        return reject(error.message);
                                    });

                        }else{
                            return reject("order has not a status");
                        }
                    }else{
                        return reject("unable to get the order information in offline");
                    }          

               
            }
            
        }).catch(function(error){
            return reject(error.message);
        });
        }).catch(function(error){
                console.log(error);
                return reject(error);
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
    function checkPOSSync(){
        return new Promise(function(resolve,reject){
            get_POS_Sync_Orders().then(function(data){

                if(data.length>0){
                    return resolve(true);
                }else{
                    get_POS_sync_CustomersData().then(function(data){
                        if(data.length>0){
                            return resolve(true);
                        }else{
                            getOrderDeliveredItems("").then(function(data){
                                if(data.length>0){
                                    return resolve(true);
                                }else{
                                    return resolve(false);
                                }
                            });
                            
                        }
                    }); 
                }       
            });
            
        });
    }

    //set formate data

    //set the order delivered items
    function setOrderDeliveredItems(user_id,order_id,delete_order){

        return new Promise(function(resolve,reject){
            openDB().then(function(){
            var result_data={};
            result_data.data={};
            POS_TABLES.order_delivered.put({"user":user_id,
                "order_id":order_id,
                "delete_order":delete_order}).
            then(function(){
                getPreOrderData(order_id).then(function(result){
                    if(result.length>0){
                        result_data.data=JSON.parse(result[0].order_data);
                        return resolve(result_data);
                    }else{
                        
                        return resolve(result_data);
                    }
                }).catch(function(error){
                       result_data.data={};
                       return resolve(result_data);
                });
                                
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        });
    }

    //get the order delivered items
    function getOrderDeliveredItems(order_id){

        return new Promise(function(resolve,reject){
            openDB().then(function(){
            if(order_id.length==0){

                POS_TABLES.order_delivered.toArray().then(function(data){
                    return resolve(data);
                }).catch(function(error){
                    return resolve([]);
                });
                
            }else{

                POS_TABLES.order_delivered.where("order_id").equals(order_id).toArray().then(function(data){
                    if(data.length>0)   
                        return resolve(data);
                    else
                        return resolve([]);
                }).catch(function(error){
                    return resolve([]);
                });
                
            }
            }).catch(function(error){
                console.log(error);
                return reject(error);
            });
        }); 
        
    }

    //clear the pos transactions
    function clearDeliveredOrders(){

        return new Promise(function(resolve,reject){
            openDB().then(function(){

            SPWAN(function*(){

                yield POS_TABLES.order_delivered.toArray(function(delivered_orders){

                    for(var orders=0;orders<delivered_orders.length;orders++){

                        POS_TABLES.sync_orders.
                        where("order_id").equals(delivered_orders[orders].order_id).
                        modify(function(modify_order){
                            modify_order.order.status="0";

                        }).then(function(data){

                            if(data.length==0){

                                POS_TABLES.pre_orders.
                                where("order_id").equals(delivered_orders[orders].order_id).
                                modify(function(modify_order){
                                    modify_order.order.status="0";
                                }).then(function(data){
                                    console.log("change the status of preorder"+data);
                                });
                            }
                        });
                    }


                }).catch(function(error){

                    POS_TABLES.order_delivered.
                    clear().
                    then(function(data){
                        return resolve();
                    }).catch(function(error){
                        return resolve();
                    });
                });

                POS_TABLES.order_delivered.
                clear().
                then(function(data){
                    return resolve();
                }).catch(function(error){
                    return resolve();
                });
            });
            }).catch(function(error){
                console.log(error);
                return reject(error);
            }); 

        });     
    } 


