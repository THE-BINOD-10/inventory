!(function () {
  "use strict";

  var global = window.MIEBACH;

  $(function () {

    var $container = $("body div.container");

    var $formContainer = $("#form-container"),
        $loginForm = $("#login-form"),
        fHeight = $loginForm.height();

    var $window = $(window);

    var $bg = $("body .bg");

    $bg.css("background-image", "url(" + global.login_bg + ")");

    $formContainer.removeClass("out");

  });
}());
