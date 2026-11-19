// Notices that can be clicked away ([data-dismissable] with a [data-dismiss] button): hidden for
// this browser until a new notice comes, whose key differs. Without JavaScript they stay.
(function () {
  "use strict";
  function hidden(key) {
    try { return window.localStorage.getItem("dismissed:" + key) === "1"; } catch (e) { return false; }
  }
  function remember(key) {
    try { window.localStorage.setItem("dismissed:" + key, "1"); } catch (e) { /* only for now */ }
  }
  document.querySelectorAll("[data-dismissable]").forEach(function (notice) {
    var key = notice.dataset.dismissable;
    if (hidden(key)) { notice.hidden = true; return; }
    var button = notice.querySelector("[data-dismiss]");
    if (!button) { return; }
    button.hidden = false;
    button.addEventListener("click", function () {
      notice.hidden = true;
      remember(key);
    });
  });
}());
