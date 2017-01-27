 'use strict';
 //TODO set the INDEXDB to localforage
 
 var db = new Dexie("stockone");

    db.version(2).stores({
         brands:'sku_brand',
     categories:'sku_category',
       sku_data:'id,sku_desc,style_name,wms_code,sku_size,sku_brand,sku_category,sku_class,image_url,price,mrp,intransit_quantity,physical_stock,sale_through,style_quantity',
      checksum:'check_sum',
      placeorder:'++id,time,order,status',
     loginstatus:'loginstatus',
     });

  db.open().then(function(){
      console.log("db created");
      
  }).catch(function(e) {
     console.log("db error :"+e);   
     alert ("Local DB creation failed: " + e);
  });

  function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
  }

  function setloginStatus(statuses){
      db.open();
    db.transaction("rw",db.loginstatus,function(){

     db.loginstatus.clear().then(function(){
        db.loginstatus.add({loginstatus:JSON.stringify(statuses)});
      });

   }).then(function(){
       return true;
    }).catch(function(err){
       return true;
    });
 
  }

 function getSkuBrands(sel_thru_type){
   var brands=[];
   return db.sku_data.where("sale_through").equalsIgnoreCase(sel_thru_type)
                .and(function(sku){
                  if(brands.indexOf(sku.sku_brand)==-1) {
                     brands.push(sku.sku_brand);
                     return true;
                  }else{
                    return false;
                  }
              }).toArray()
 }

 function getSkuCat(sel_thru_type){
   var cat=[];
   return db.sku_data.where("sale_through").equalsIgnoreCase(sel_thru_type)
                .and(function(sku){
                  if(cat.indexOf(sku.sku_category)==-1) {
                     cat.push(sku.sku_category);
                     return true;
                  }else{
                    return false;
                  }
              }).toArray()
 }



  function deleteDB(){

    db.brands.clear();
    db.categories.clear();
    db.sku_data.clear();
    db.checksum.clear();
    db.placeorder.clear();
    db.loginstatus.clear();
  }

  function getloginStatus(){
        return  db.loginstatus.toArray()
     .then(function(data){
             if(data.length>0){
                var data_item=data[0];
                var status_data=data_item["loginstatus"]; 
                var status_item=JSON.parse(status_data);
                   return status_item;
             }else{
                return false;  
             }
    }).catch(function(err){
        return false;
    });
  }

 function setCheckSum(checksum_val){

  db.checksum.clear();
  return db.checksum.put({check_sum:checksum_val}).then(function(){
      return true;
    }).catch(function(err){
      return true;
      console.log("checksum set error : "+err);
     });
 }

 function setBrands(brands){
          
     db.transaction("rw",db.brands,function(){

     brands.forEach(function(data){
       db.brands.put({sku_brand:data}).then(function(){
          }).then(function(data){
              console.log("insert brand  -"+data);
          }).catch(function(err){
             alert("brand set errror "+err);
          });
    });
 });			
 }

 function dbOpen(){
 if(!db.open())
     db.open();
 }

 function dbClose(){
  db.close();
 }

 function setCategories(categories){

    db.transaction("rw",db.categories,function(){

   categories.forEach(function(category){
     
    db.categories.put({sku_category:category}).then(function(){
      }).catch(function(err){
         console.log("category set error : "+err);
      });
   });
  });    
 }

 function setplaceOrder(order_data){
       db.transaction("rw",db.placeorder,function(){

     db.placeorder.put({time:new Date().getTime(),order:JSON.stringify(order_data),status:"pending"}).catch(function(err){ console.log("local place order error");
      });

   });     
  }

 function getplacedOrders(){
    
  return db.placeorder.where("status").equals("pending").toArray(); 

 }

 function deleteOrder(order_time){
    console.log("time is "+order_time);
    return db.placeorder.where("time").equals(order_time).delete();
 }


 function setSku(skus_data){
    var count=0;
    var sku_count=0;
   if(skus_data.length<=0){
    return true;
   }else{
    skus_data.forEach(function(skus){
       count++;
        if(skus['variants'].length>0){
          sku_count+=skus['variants'].length;
          db.sku_data.bulkAdd(skus['variants']).then(function(){
              console.log("item len are"+skus['variants'].length);  
           }).catch(function(err){
              console.log("sku set error : "+err +"\n  data "+skus); 
          });
        }
 
       if(count==skus_data.length){
         console.log("sku varients len is "+sku_count);
         return true ;
       }  
      
     }); 
   }
 }

 function getCategories(skuBrand, sale_thru){
   var  temp_catlog_data=[];
  if(skuBrand.trim().length>0){
     return  db.sku_data.where("sku_brand").equalsIgnoreCase(skuBrand)
                .and(function(sku){
                  if((capitalize(sku.sale_through) == sale_thru) && (temp_catlog_data.indexOf(sku.sku_class)==-1)) {
                     temp_catlog_data.push(sku.sku_class);
                     return true;
                  }else{
                    return false;
                  }
              }).toArray()
 
   }else{
     return  db.sku_data.where("sale_through").equalsIgnoreCase(sale_thru)
                .and(function(sku){
                  if(temp_catlog_data.indexOf(sku.sku_class)==-1) {
                     temp_catlog_data.push(sku.sku_class);
                     return true;
                  }else{
                    return false;
                  }
              }).toArray()
      //return  db.categories.toArray();
   }

 }
 

 function getCategoryData(brand,category,style, sale_thru){

   var temp_catelog_data=[];
   var skubrand=brand;
   var skucategory=category;
   var skustyle=style;
 // return db.sku_data.where("sku_brand").equalsIgnoreCase(brand).toArray();

   if(skubrand.trim().length>0){
  return   db.sku_data.where("sku_brand").equalsIgnoreCase(skubrand)
        .and(function(sku_item_cat_check){
          if(skucategory.trim().length>0)
            return sku_item_cat_check.sku_category.toLowerCase()===skucategory.toLowerCase();
          else
            return true;

     }).and(function(sku_item_style_check){
         if(skustyle.trim().length>0)
            return sku_item_style_check.sku_class.toLowerCase().startsWith(skustyle.toLowerCase());  
         else
           return true;
       }).and(function(sku){

       if((capitalize(sku.sale_through) == sale_thru) && (temp_catelog_data.indexOf(sku.sku_class)==-1)){
         temp_catelog_data.push(sku.sku_class);
         return true;
       }else{
        return false;
        }

    }).toArray();

  }else if(skucategory.trim().length>0){

   return  db.sku_data.where("sku_category").equalsIgnoreCase(skucategory)
     .and(function(sku_item_style_check){
          if(skustyle.trim().length>0)
            return sku_item_style_check.sku_class.toLowerCase().startsWith(skustyle.toLowerCase());
         else
            return true;

     }).and(function(sku){

       if((capitalize(sku.sale_through) == sale_thru) && (temp_catelog_data.indexOf(sku.sku_class)==-1)){
         temp_catelog_data.push(sku.sku_class);
        return true;
       }else{
        return false;
       }
    }).toArray();

   }else{

  return db.sku_data.where("sku_class").startsWithIgnoreCase(skustyle)
        .and(function(sku){
          if((capitalize(sku.sale_through) == sale_thru) && (temp_catelog_data.indexOf(sku.sku_class)==-1)){
            temp_catelog_data.push(sku.sku_class);
            return true;
          }else{
            return false;
          }
    }).sortBy('sku_class');
  }
 }
 function getskuVarients(skustyle, sale_thru){
    var styles = [];
    return  db.sku_data.where("sku_class").equalsIgnoreCase(skustyle)
            .and(function(sku){
          if((capitalize(sku.sale_through) == sale_thru) && (styles.indexOf(sku.wms_code)==-1)){
            styles.push(sku.wms_code);
            return true;
          }else{
            return false;
          }

    }).toArray();

 }

