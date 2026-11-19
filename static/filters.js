// The tab Filters: the numbers of a filter are counted only when its details are opened, as a
// part of the page that the site renders. Without JavaScript, the details link that part.
(function () {
  "use strict";
  document.querySelectorAll("[data-filter-details]").forEach(function (details) {
    var loaded = false;
    details.addEventListener("toggle", function () {
      if (!details.open || loaded) { return; }
      loaded = true;
      var target = details.querySelector("[data-filter-counts]");
      fetch(details.dataset.counts, {credentials: "same-origin"})
        .then(function (answer) { return answer.ok ? answer.text() : Promise.reject(answer); })
        .then(function (html) { target.innerHTML = html; })  // rendered by the site
        .catch(function () { loaded = false; });
    });
  });
}());
