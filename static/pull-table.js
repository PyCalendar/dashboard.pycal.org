// The table of pull requests: CSS shows and hides the columns by their checkboxes; this script
// remembers the choice in this browser, names the shown columns in the summary, and changes the
// number per page at once. Without JavaScript, the checkboxes still work for the page.
(function () {
  "use strict";
  var KEY = "pull-table-columns";
  var table = document.querySelector("[data-pull-requests]");
  if (!table) { return; }
  var boxes = Array.prototype.slice.call(table.querySelectorAll("[data-column]"));
  var shown = table.querySelector("[data-columns-shown]");
  function read() {
    try { return JSON.parse(window.localStorage.getItem(KEY) || "null"); } catch (e) { return null; }
  }
  function save() {
    var hidden = boxes.filter(function (box) { return !box.checked; })
      .map(function (box) { return box.dataset.column; });
    try { window.localStorage.setItem(KEY, JSON.stringify(hidden)); } catch (e) { /* this page only */ }
  }
  function name() {
    var names = boxes.filter(function (box) { return box.checked; })
      .map(function (box) { return box.parentNode.textContent.trim(); });
    shown.textContent = names.length ? names.join(", ") : "–";
  }
  var hidden = read();  // null: the columns that the page shows first
  boxes.forEach(function (box) {
    if (hidden) { box.checked = hidden.indexOf(box.dataset.column) < 0; }
    box.addEventListener("change", function () { save(); name(); });
  });
  name();
  var form = table.querySelector("[data-per-page]");
  form.querySelector("[data-per-page-submit]").hidden = true;
  form.querySelector("select").addEventListener("change", function () { form.submit(); });
}());
