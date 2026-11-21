// The page of a person in a project: the switches of the kinds of reviews behind the gear count
// again at once when one changes. Without JavaScript, Apply does it.
(function () {
  "use strict";
  var form = document.querySelector("form[data-kinds-form]");
  if (!form) { return; }
  var apply = form.querySelector("[data-kinds-apply]");
  if (apply) { apply.hidden = true; }
  form.addEventListener("change", function () {
    if (!form.querySelector("input[name=kinds]:checked")) { return; }  // at least one kind
    form.requestSubmit();
  });
}());
