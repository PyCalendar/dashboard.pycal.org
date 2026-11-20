// The tab Filters: the table of the conditions of a filter is on the page; its numbers are
// counted only when the filter is opened, and filled in. Without JavaScript, each number links
// the page that counts them.
(function () {
  "use strict";
  document.querySelectorAll("[data-filter-details]").forEach(function (details) {
    var loaded = false;
    details.addEventListener("toggle", function () {
      if (!details.open || loaded) { return; }
      loaded = true;
      details.querySelectorAll("[data-count-of]").forEach(function (cell) {
        var spinner = document.createElement("span");
        spinner.className = "loading";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-label", details.dataset.loadingText || "");
        spinner.title = details.dataset.loadingText || "";
        cell.replaceChildren(spinner);
      });
      fetch(details.dataset.numbers, {credentials: "same-origin"})
        .then(function (answer) { return answer.ok ? answer.json() : Promise.reject(answer); })
        .then(function (numbers) {
          details.querySelectorAll("[data-count-of]").forEach(function (cell) {
            var found = numbers.conditions[cell.dataset.countOf];
            cell.textContent = found === undefined ? "–" : found;
          });
          var total = details.querySelector("[data-filter-total]");
          total.textContent = (details.dataset.totalText || "").replace("%(count)s", numbers.count);
        })
        .catch(function () {
          loaded = false;  // the links to count stay usable: open it again to retry
          details.querySelectorAll("[data-count-of]").forEach(function (cell) {
            var link = document.createElement("a");
            link.href = details.dataset.numbers.replace("?numbers=1", "");
            link.className = "muted";
            link.textContent = "–";
            cell.replaceChildren(link);
          });
        });
    });
  });
}());
