'use strict';
  
var ASYNC = Dexie.async;
var SPWAN = Dexie.spawn;
var DATABASE = new Dexie("pos_pwa");
var POS_TABLES=DATABASE._allTables;
    if(Object.keys(POS_TABLES).length>0){
      enableHook();     
    }

    function createDB(){
    DATABASE.version(1).stores({
       skumaster:"SKUCode,ProductDescription,search,price,igst,discount,selling_price,url,sgst,data_id,utgst,stock_quantity,cgst,*sku_search_words",
       sku_search_words:"++,word,SKUCode",
       checksum:"name,checksum,path",
       customer:"FirstName,LastName,Number,ID,Address,Email",
       sync_customer:"number,firstName,secondName,mail,user",
       sync_orders:"order_id,order",
       pre_orders:"order_id,order_data",
       order_delivered:"order_id,delete_order,user"
    });

     //delete the the table for for change the primery key
    DATABASE.version(2).stores({
    customer:null
    });

    //create the customer table and hte primery key is customer id
    DATABASE.version(3).stores({
     customer:"ID,FirstName,LastName,Number,Address,Email"
    });

    DATABASE.version(4).stores({
      sync_customer:null,
      pre_orders:null
    });

    DATABASE.version(5).stores({
      sync_customer:"++,number,firstName,secondName,mail,user",
      skumaster:"SKUCode,ean_number,ProductDescription,search,price,igst,discount,selling_price,url,sgst,data_id,utgst,stock_quantity,cgst",
      pre_orders:"++id,order_id,order_data",
    });

    openDB().then(function(){
      console.log("opened");
    }).catch(function(error){
      console.log(error);
    });
    POS_TABLES=DATABASE._allTables;

 
    enableHook();
}

function enableHook(){
       //create index on sku_search_words table
       DATABASE._createTransaction = Dexie.override(DATABASE._createTransaction, function (createTransaction) {
       
        return function(mode, storeNames, DATABASESchema) {
            if (mode === "readwrite" && storeNames.indexOf("sku_search_words") == -1) {
                storeNames = storeNames.slice(0); // Clone storeNames before mappling with it.
                storeNames.push("sku_search_words");
            }
            return createTransaction.call(this, mode, storeNames, DATABASESchema);
        }
    });

    POS_TABLES.skumaster.hook("creating", function (primKey, obj, trans) {
        // Must wait till we have the auto-incremented key.
        trans._lock(); 
        // Lock transaction until we got primary key and added all mappings. 
        //App code trying to read from SKU word the line after having added an SKUCode must then 
        //wait until we are done writing the mappings.
        this.onsuccess = function (primKey) {
            // Add mappings for all words.
            getAllWords(obj.search).forEach(function (word) {
                POS_TABLES.sku_search_words.
                        add({ word: word, SKUCode: primKey });
            });
            trans._unlock();
        }
        this.onerror = function () {
            trans._unlock();
        }
    });

    POS_TABLES.skumaster.hook("updating", function (mods, primKey, obj, trans) {
        /// <param name="trans" type="DATABASE.Transaction"></param>
        if (mods.hasOwnProperty("search")) {
            // SKUCode property is about to be changed.
            // Delete existing mappings
            POS_TABLES.sku_search_words.where("SKUCode").equals(primKey).delete();
            // Add new mappings.
            if (typeof mods.search == 'string') {
                getAllWords(mods.search).forEach(function (word) {
                    POS_TABLES.sku_search_words.
                            add({ word: word, SKUCode: primKey });
                });
            }
        }
    });

    POS_TABLES.skumaster.hook("deleting", function (primKey, obj, trans) {
        /// <param name="trans" type="DATABASE.Transaction"></param>
        if (obj.search) {
            // SKUCode is about to be deleted.
            // Delete existing mappings
            POS_TABLES.sku_search_words.
                        where("SKUCode").equals(primKey).delete();
        }
    });
}

function getAllWords(text) {
    
    if (text) {
        var allWordsIncludingDups = text.toLowerCase().split(/[\b\s!@#$%^&*-.,=?+]+/);
        allWordsIncludingDups.push(text);
        allWordsIncludingDups.filter(Boolean);
        var remove_duplicates=new Set(allWordsIncludingDups);
        allWordsIncludingDups=Array.from(remove_duplicates);
        var wordSet = allWordsIncludingDups.reduce(function (prev, current) {
            prev[current] = true;
            return prev;
        }, {});
        return Object.keys(wordSet);
    }
}

//opent local DB
function openDB(){
  return new Promise(function(resolve,reject){
   if(DATABASE.isOpen()==false){
     DATABASE.open().then(function(){
          console.log("Opened");
          enableHook();
          return resolve();    
      }).catch(Dexie.errnames.NoSuchDatabase,function(error){
          createDB(); 
          return resolve();  
      }).catch(function(e) {
         console.log("DATABASE error :"+e);   
         //alert ("Local DATABASE creation failed: " + e);
         return resolve(e.stack);
      });
    }else{
      return resolve();
    }
  });
}


