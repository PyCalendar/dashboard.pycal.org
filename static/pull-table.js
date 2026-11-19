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
  // the menus of conditions: only the fields of the chosen group are required
  table.querySelectorAll("[data-condition-form]").forEach(function (form) {
    var select = form.querySelector(".group-select");
    function require() {
      form.querySelectorAll("[data-required-for]").forEach(function (field) {
        field.required = field.dataset.requiredFor === select.value;
      });
      form.querySelectorAll("[data-switches]").forEach(function (set) {
        var boxes = set.querySelectorAll("input[type=checkbox]");
        var on = Array.prototype.some.call(boxes, function (box) { return box.checked; });
        boxes[0].setCustomValidity(set.dataset.switches === select.value && !on ?
          set.querySelector("legend").textContent + ": " + (table.dataset.chooseOne || "?") : "");
      });
    }
    form.addEventListener("change", require);
    require();
  });
  // drag a column of conditions onto another one to move it there
  var dragged = null;
  table.querySelectorAll("[data-condition-column]").forEach(function (head) {
    head.addEventListener("dragstart", function (event) {
      dragged = head.dataset.conditionColumn;
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", dragged);
    });
    head.addEventListener("dragover", function (event) {
      if (dragged !== null) { event.preventDefault(); head.classList.add("dragged-over"); }
    });
    head.addEventListener("dragleave", function () { head.classList.remove("dragged-over"); });
    head.addEventListener("drop", function (event) {
      event.preventDefault();
      head.classList.remove("dragged-over");
      var to = head.dataset.conditionColumn;
      if (dragged === null || dragged === to) { return; }
      var address = new URL(window.location.href);
      address.searchParams.delete("page");
      address.searchParams.set("move", dragged);
      address.searchParams.set("to", to);
      window.location.assign(address.toString());
    });
  });
  var form = table.querySelector("[data-per-page]");
  form.querySelector("[data-per-page-submit]").hidden = true;
  form.querySelector("select").addEventListener("change", function () { form.submit(); });
}());
