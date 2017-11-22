"use strict";
(function () {

  var endpoint;
   var key;
   var authSecret;

  
    
          if ("serviceWorker" in navigator) {
             //registering service worker 
              	navigator.serviceWorker.register("sw.js").
              			then(function(reg){
                      navigator.serviceWorker.ready;
                    }).then(function(reg){

                
 
          					if(navigator.serviceWorker.controller){
                    				 if (navigator.storage && navigator.storage.persist) 
                          navigator.storage.persisted().then(persistent=>{
                            if (persistent)
                              console.log("Storage will not be cleared except by explicit user action");
                            else
                              console.log("Storage may be cleared by the UA under storage pressure.");
                          });
               
                          console.log("page controlled by Service worker");
                   			}else{
                   				console.log("page not controlled Service worker");
                        }
                  }).catch(function (err) {
                   		console.log("Service worker failed with error " + err);
              });
         }
    /*
      Notification.requestPermission(function(result) {
           if (result !== 'granted')
             return reject(Error("Denied notification permission"));
        });

     navigator.serviceWorker.ready.then(function(registration) {
        return registration.pushManager.getSubscription()
              .then(function(subscription) {
                 if (subscription) {
                    return subscription;
                  }

      return registration.pushManager.subscribe({ userVisibleOnly: true });
      });
    }).then(function(subscription) {
       var rawKey = subscription.getKey ? subscription.getKey('p256dh') : '';
       key = rawKey ?
        btoa(String.fromCharCode.apply(null, new Uint8Array(rawKey))) :
        '';
       var rawAuthSecret = subscription.getKey ? subscription.getKey('auth') : '';
       authSecret = rawAuthSecret ?
               btoa(String.fromCharCode.apply(null, new Uint8Array(rawAuthSecret))) :
               '';

       endpoint = subscription.endpoint;

     
  });

   */




}());                  
