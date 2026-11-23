// The page of saving a filter: drag a condition between the quality checks and Skip if. The
// drop presses its button To Skip if or To the quality checks, which sends the form: the name,
// the description and the switches stay as they were typed, as without JavaScript.
(function () {
  "use strict";
  var form = document.querySelector("form[data-save-filter]");
  if (form && form.dataset.address && window.history.replaceState) {
    // after a button of a condition, the address shows the conditions of the page again
    window.history.replaceState(null, "", form.dataset.address);
  }
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
      if (!dragged || dragged.parentElement === section) { return; }
      var move = dragged.querySelector("button[data-to-skip], button[data-to-checks]");
      if (move && move.form && move.form.requestSubmit) {
        move.form.requestSubmit(move);
      } else {
        window.location.href = dragged.dataset.move.replace(/&amp;/g, "&");
      }
    });
  });
}());
