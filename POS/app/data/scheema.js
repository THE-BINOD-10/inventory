'use strict';
  
var ASYNC = Dexie.async;
var SPWAN = Dexie.spawn;
 var DATABASE = new Dexie("pos_pwa");

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
    
  //create index on sku_search_words table
   DATABASE._createTransaction = Dexie.override(DATABASE._createTransaction, function (createTransaction) {
    // Override DATABASE._createTransaction() to make sure to add _emailWords table to any transaction being modified
    // If not doing this, error will occur in the hooks unless the application code has included _emailWords in the transaction when modifying emails table.
    return function(mode, storeNames, DATABASESchema) {
        if (mode === "readwrite" && storeNames.indexOf("sku_search_words") == -1) {
            storeNames = storeNames.slice(0); // Clone storeNames before mippling with it.
            storeNames.push("sku_search_words");
        }
        return createTransaction.call(this, mode, storeNames, DATABASESchema);
    }
});

DATABASE.skumaster.hook("creating", function (primKey, obj, trans) {
    // Must wait till we have the auto-incremented key.
    trans._lock(); // Lock transaction until we got primary key and added all mappings. App code trying to read from _emailWords the line after having added an email must then wait until we are done writing the mappings.
    this.onsuccess = function (primKey) {
        // Add mappings for all words.
        getAllWords(obj.search).forEach(function (word) {
            DATABASE.sku_search_words.add({ word: word, SKUCode: primKey });
        });
        trans._unlock();
    }
    this.onerror = function () {
        trans._unlock();
    }
});

DATABASE.skumaster.hook("updating", function (mods, primKey, obj, trans) {
    /// <param name="trans" type="DATABASE.Transaction"></param>
    if (mods.hasOwnProperty("search")) {
        // message property is about to be changed.
        // Delete existing mappings
        DATABASE.sku_search_words.where("SKUCode").equals(primKey).delete();
        // Add new mappings.
        if (typeof mods.search == 'string') {
            getAllWords(mods.search).forEach(function (word) {
                DATABASE.sku_search_words.add({ word: word, SKUCode: primKey });
            });
        }
    }
});

DATABASE.skumaster.hook("deleting", function (primKey, obj, trans) {
    /// <param name="trans" type="DATABASE.Transaction"></param>
    if (obj.search) {
        // Email is about to be deleted.
        // Delete existing mappings
        DATABASE.sku_search_words.where("SKUCode").equals(primKey).delete();
    }
});


function getAllWords(text) {
    
    if (text) {
        var allWordsIncludingDups = text.toLowerCase().split(' ');
        var wordSet = allWordsIncludingDups.reduce(function (prev, current) {
            prev[current] = true;
            return prev;
        }, {});
        return Object.keys(wordSet);
    }
}

 DATABASE.open().then(function(){
      console.log("Opened");
      
  }).catch(function(e) {
     console.log("DATABASE error :"+e);   
     //alert ("Local DATABASE creation failed: " + e);
  });


