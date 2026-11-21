// The page of saving a filter: drag a condition between the quality checks and Skip if. The
// drop opens the address that moves it, as its button does without JavaScript.
(function () {
  "use strict";
  var dragged = null;
  document.querySelectorAll("tr[data-condition-row][data-move]").forEach(function (row) {
    row.addEventListener("dragstart", function (event) {
      dragged = row;
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", row.dataset.conditionRow);
    });
    row.addEventListener("dragend", function () { dragged = null; });
  });
  document.querySelectorAll("tbody[data-section]").forEach(function (section) {
    section.addEventListener("dragover", function (event) {
      if (dragged && dragged.parentElement !== section) {
        event.preventDefault();
        section.classList.add("dragged-over");
      }
    });
    section.addEventListener("dragleave", function () { section.classList.remove("dragged-over"); });
    section.addEventListener("drop", function (event) {
      event.preventDefault();
      section.classList.remove("dragged-over");
      if (dragged && dragged.parentElement !== section) {
        window.location.href = dragged.dataset.move.replace(/&amp;/g, "&");
      }
    });
  });
}());
