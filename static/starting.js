// The page while the site starts (docker/starting.html, served by nginx): instead of reloading
// itself, it asks /health/ until the site answers, then opens the page again with GET. A page
// that only takes a form (POST), whose form was sent during the start, would answer 405
// Method Not Allowed: then it goes back to the page with the form.
(function () {
  "use strict";
  var WAIT = 3000;
  function open() {
    fetch(window.location.href, {method: "HEAD", cache: "no-store", credentials: "same-origin"})
      .then(function (answer) {
        var back = answer.status === 405 ? (document.referrer || "/") : window.location.href;
        window.location.replace(back);  // GET, never the form again
      })
      .catch(function () { window.location.replace(window.location.href); });
  }
  function check() {
    fetch("/health/", {cache: "no-store"})
      .then(function (answer) { if (answer.ok) { open(); } else { setTimeout(check, WAIT); } })
      .catch(function () { setTimeout(check, WAIT); });
  }
  setTimeout(check, WAIT);
}());
