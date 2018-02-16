"use strict";
(function () {

  if ("serviceWorker" in navigator) {
      //registering service worker 
     	navigator.serviceWorker.register("sw.js").
               		then(function(reg){
                     	console.log("service worker registered"+reg);

                        localStorage.setItem('reload_flag','0');
                      reg.addEventListener('updatefound',function(){
                              console.log("service worker update founded");
                              const newWorker = reg.installing;
                              var flag = localStorage.getItem('reload_flag') || '0';
                              if(flag === '0') {
                                  localStorage.setItem('reload_flag','1');
                                  location.reload(true);
                                  POS_UPDATE_FOUND=true;
                                  reloadPOSPage();
                              }else {
                                  localStorage.setItem('reload_flag','0');
                              }
                              
                              //check if reg is installing null or not
                              if(newWorker!=null)}{
                                newWorker.addEventListener('statechange', function(e){
                                      console.log(" state changed "+e.target.state);
                                     // reg.showNotification("POS found update", {icon:"app/images/pos_icon.png"});
                                      POS_UPDATE_FOUND=true;
                                      reloadPOSPage();
                                });
                              }
                      });
                  }).catch(function (err) {
	                   	console.log("Service worker failed with error " + err);
                  });
  

         navigator.serviceWorker.addEventListener('controllerchange',function(){

                        console.log("controllerchange the service worker");
                        // POS_UPDATE_FOUND=true;
                         //reloadPOSPage();
                        

                      });          

  }

}());

  //reload the pos page
  function reloadPOSPage(){
    
    if(POS_ENABLE_SYNC===false && POS_UPDATE_FOUND){
      
      navigator.serviceWorker.ready.then(function(reg){
          reg.showNotification("POS found update,reloading the page", {icon:"app/images/pos_icon.png"});
      });
      
      POS_UPDATE_FOUND=false;
      location.reload(true);
    }
  }

  //enable the notificaiton
  function enableNotificaiton(){

    return new Promise(function(resolve,reject){

      navigator.serviceWorker.ready.then(function(reg){

        Notification.requestPermission(function(result) {
               if (result == 'granted')
                  resolve(true);
               else
                 resolve(false);

            });
      }).catch(function(error){
          resolve(false);
      });
    });
  }
  //check if the storage is persisted or not
  async function isStoragePersisted() {
    return await navigator.storage && navigator.storage.persisted &&
      navigator.storage.persisted();
  }

  //storage will be persistent
  async function persist() {
    return await navigator.storage && navigator.storage.persist &&
      navigator.storage.persist();
  }

  //show the estimate quota
  async function showEstimatedQuota() {
   return await navigator.storage && navigator.storage.estimate ?
      navigator.storage.estimate() :
      undefined;
  }

  //persist the storage wihout user confirmation
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
          isStoragePersisted().
                then(async isPersisted => {
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
