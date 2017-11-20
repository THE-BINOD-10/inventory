"use strict";

//create index db for pos
var DB_NAME="pwa_pos";

//Dexie.debug=true;
var db_exists=false;
var ASYNC = Dexie.async;
var SPWAN = Dexie.spawn;
var DATABASE=new Dexie("pwa_pos");


DATABASE.version(1).stores({
              skumaster:"SKUCode,ProductDescription,price,igst,discount,selling_price,url,sgst,data-id,utgst,stock_quantity,cgst",
              checksum:"checksum,name,path",
          });

DATABASE.open().then(function(){
      console.log("db open");
      
  }).catch(function(e) {
     console.log("db error :"+e);   
     //alert ("Local DB creation failed: " + e);
  });

   /* //creating an hook for ProductDescription
	DATABASE.skumaster.hook("creating", function (primKey, obj, trans) {
	        if (typeof obj.ProductDescription == 'string') 
	        	obj.sku_name_words = getAllWords(obj.ProductDescription);
	});
    
    
    DATABASE.skumaster.hook("updating", function (mods, primKey, obj, trans) {
        if (mods.hasOwnProperty("ProductDescription")) {
            // "message" property is being updated
            if (typeof mods.ProductDescription == 'string')
                // "message" property was updated to another valid value. Re-index messageWords:
                return { sku_name_words: getAllWords(mods.ProductDescription) };
            else
                // "message" property was deleted (typeof mods.message === 'undefined') or changed to an unknown type. Remove indexes:
                return { sku_name_words: [] };
        }

    });

    function getAllWords(text) {
        
        var allWordsIncludingDups = text.split(' ');
        var wordSet = allWordsIncludingDups.reduce(function (prev, current) {
            prev[current] = true;
            return prev;
        }, {});
        return Object.keys(wordSet);
    }*/


