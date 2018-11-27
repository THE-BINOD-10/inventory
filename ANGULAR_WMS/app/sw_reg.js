
(function (win) {
        "use strict";
   var endpoint;
   var key;
   var authSecret;

        if ("serviceWorker" in win.navigator) {

          win.navigator.serviceWorker.register("./sw.js").then(function (reg) {
                     
            win.console.log("Service worker registered successfully"+reg);
          }, function (err) {
            
            win.console.log("Service worker failed with error " + err);
          });
        }

         Notification.requestPermission(function(result) {
           if (result !== 'granted' && typeof(reject) != 'undefined')
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

  }(window))


