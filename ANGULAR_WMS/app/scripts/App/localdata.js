'usestricct';
 //TODO set the INDEXDB to localforage
 // localforage.setDriver([localforage.INDEXEDDB,localforage.LOCALSTORAGE]);
 // console.log("driver is "+localforage.driver);
  localforage.config({
    driver: [localforage.INDEXEDDB,localforage.LOCALSTORAGE],
    name: 'stockone',
    vestion:'1.0',
    storeName:'stockone'
  });

  var local_pending_orders = localforage.createInstance({
    name: "pendingorders"
  });
  
  //TODO get the keys
  localforage.length().then(function(n){
  console.log("localforage keys size  "+n);
  });

  /*
  localDB_orders.length().then(function(n){
    console.log("orders length is "+n);
  });
  */

  /*TODO set item intolocldb 
   @title-item key
   @data- item value
  */
  function setItemDb(title,data){
    
     localforage.setItem(title,JSON.stringify(data)).then(function (value) {
     // Do other things once the value has been saved.
      console.log("setting "+title+" values are  "+value);
     
     }).catch(function(err) {
      // This code runs if there were any errors
      console.log(err);
      });

    }
 

  /*TODO get item from localdb
  @title-item fectch by title value
  */

  function getItemDb(title){
    
     localforage.getItem(title,function (err,value) {
     // Do other things once the value has been saved.
     if(err){
         return false;
    } else{
         console.log("getting "+title +" values are "+value);
         return JSON.parse(value);
     }});

    }

