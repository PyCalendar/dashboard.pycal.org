// Proposes repositories while a person types into a field with data-complete: those the site
// knows and those of GitHub. Without JavaScript, the field proposes the repositories the site
// knows, and the search below it finds the others.
(function () {
  "use strict";
  function connect(input) {
    var list = document.getElementById(input.getAttribute("list"));
    var timer = null;
    var asked = "";
    function propose() {
      clearTimeout(timer);
      var text = input.value.trim();
      if (text.length < 2 || text === asked) { return; }
      timer = setTimeout(function () {
        asked = text;
        fetch(input.dataset.complete + "?q=" + encodeURIComponent(text), {credentials: "same-origin"})
          .then(function (answer) { return answer.ok ? answer.json() : {repositories: []}; })
          .then(function (data) {
            if (input.value.trim() !== text) { return; }
            list.replaceChildren.apply(list, data.repositories.map(function (name) {
              var option = document.createElement("option");
              option.value = name;
              return option;
            }));
          })
          .catch(function () {});
      }, 250);
    }
    input.addEventListener("input", propose);
    input.dataset.completeConnected = "";  // ready: what was typed before is proposed now
    if (input.value.trim()) { propose(); }
  }
  document.querySelectorAll("input[data-complete]").forEach(connect);
}());
