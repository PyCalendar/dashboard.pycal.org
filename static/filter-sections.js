// The page of saving a filter: drag a condition onto another one or onto an AND to join them
// by AND, or between two conditions to move it there, also between the quality checks and
// Skip if, and out of its AND. Where it lands is highlighted: the AND, the condition, or the
// gap, which has room to drop in between. A drop where it was picked up changes nothing. The drop
// presses a button of the condition (AND with the one above, with the condition it was dropped
// onto, or a hidden one that places it), which sends the form: the name, the description and
// the switches stay as they were typed, as without JavaScript. The radio choice of a group, AND
// or OR, sends the form with its button Change, which is hidden then.
(function () {
  "use strict";
  var form = document.querySelector("form[data-save-filter]");
  if (form && form.dataset.address && window.history.replaceState) {
    // after a button of a condition, the address shows the conditions of the page again
    window.history.replaceState(null, "", form.dataset.address);
  }
  if (form) { form.dataset.droppable = ""; }  // the gaps between the conditions take room
  var dragged = null;
  var lit = [];  // the rows highlighted where the condition would land
  function field(owner, name, value) {
    var input = owner.querySelector("input[name=" + name + "][data-dropped]");
    if (!input) {
      input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.dataset.dropped = "";
      owner.appendChild(input);
    }
    input.value = value;
  }
  function press(button, values) {  // true when the button sends the form
    if (!button || !button.form || !button.form.requestSubmit) { return false; }
    Object.keys(values || {}).forEach(function (name) { field(button.form, name, values[name]); });
    button.form.requestSubmit(button);
    return true;
  }
  function andOf(row) {  // the number of the AND of a row, "" for none
    return row.dataset.and || row.dataset.andHead || "";
  }
  function rowsOf(row) {  // the rows of the condition of a row: its AND, or itself
    var and = andOf(row);
    if (!and) { return [row]; }
    return Array.prototype.filter.call(row.parentElement.children, function (other) {
      return andOf(other) === and;
    });
  }
  function together(row) {  // the row is the dragged one, or of its AND: nothing changes
    return rowsOf(dragged).indexOf(row) >= 0 && (row === dragged || Boolean(dragged.dataset.and));
  }
  function stays(gap) {  // a gap next to the dragged condition alone: it stays where it is
    if (dragged.dataset.and) { return false; }
    return gap === dragged.previousElementSibling || gap === dragged.nextElementSibling;
  }
  function light(rows, name) {
    unlight();
    rows.forEach(function (row) { row.classList.add(name); });
    lit = rows;
  }
  function unlight() {
    lit.forEach(function (row) { row.classList.remove("join-target", "gap-target"); });
    lit = [];
  }
  document.querySelectorAll("tr[data-condition-row][data-move]").forEach(function (row) {
    row.addEventListener("dragstart", function (event) {
      dragged = row;
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", row.dataset.conditionRow);
    });
    row.addEventListener("dragend", function () {
      dragged = null;
      unlight();
    });
  });
  // onto a condition, or onto an AND: join them
  document.querySelectorAll("tr[data-condition-row], tr[data-and-head]").forEach(function (row) {
    function over(event) {
      if (!dragged || together(row)) { return; }
      event.preventDefault();
      if (lit.indexOf(row) < 0) { light(rowsOf(row), "join-target"); }
    }
    row.addEventListener("dragenter", over);
    row.addEventListener("dragover", over);
    row.addEventListener("drop", function (event) {
      event.preventDefault();
      if (!dragged || together(row)) { return; }
      var to = row.dataset.conditionRow || row.dataset.joinTo;
      unlight();
      press(dragged.querySelector("button[data-join]"), {to: to});
    });
  });
  // between two conditions, or at the end of a section: move it there
  document.querySelectorAll("tr[data-gap]").forEach(function (gap) {
    function over(event) {
      if (!dragged || stays(gap)) { return; }
      event.preventDefault();
      if (lit.indexOf(gap) < 0) { light([gap], "gap-target"); }
    }
    gap.addEventListener("dragenter", over);
    gap.addEventListener("dragover", over);
    gap.addEventListener("drop", function (event) {
      event.preventDefault();
      if (!dragged || stays(gap)) { return; }
      var section = gap.closest("tbody[data-section]").dataset.section;
      unlight();
      var place = dragged.querySelector("button[data-place]");
      if (!press(place, {to: gap.dataset.before, section: section})) {
        window.location.href = dragged.dataset.move.replace(/&amp;/g, "&");
      }
    });
  });
  // the radio choice of an AND or an OR: the page shows it at once, by its button Change
  document.querySelectorAll("fieldset[data-operator]").forEach(function (choice) {
    var apply = choice.querySelector("button[data-operator-apply]");
    if (apply && apply.form && apply.form.requestSubmit) { apply.hidden = true; }
    choice.addEventListener("change", function () { press(apply); });
  });
  // leaving the table: nothing is highlighted
  document.querySelectorAll("table.filter-conditions").forEach(function (table) {
    table.addEventListener("dragleave", function (event) {
      if (!table.contains(event.relatedTarget)) { unlight(); }
    });
  });
}());
