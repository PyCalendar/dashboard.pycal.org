// Proposes people while a GitHub handle is typed, the same in every field of GitHub handles
// (input[data-complete-people], the address of /people/complete/ with the project or
// signed_in=1): their avatar, GitHub handle and GitHub name. Without JavaScript, the field
// takes the GitHub handle as typed. A field of several handles separated by commas
// (data-complete-list) proposes for the last one.
(function () {
  "use strict";
  var count = 0;
  function connect(input) {
    var list = document.createElement("ul");
    var timer = null;
    var active = -1;
    count += 1;
    list.id = "people-choices-" + count;
    list.className = "completion";
    list.setAttribute("role", "listbox");
    list.hidden = true;
    input.after(list);
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-controls", list.id);
    input.setAttribute("aria-expanded", "false");

    function close() {
      list.hidden = true;
      active = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    var several = input.hasAttribute("data-complete-list");
    function typed() {  // the name that is typed: the last one of a list
      return several ? input.value.split(",").pop().trim() : input.value.trim();
    }
    function choose(item) {
      if (several) {
        var names = input.value.split(",").map(function (name) { return name.trim(); });
        names[names.length - 1] = item.dataset.login;
        input.value = names.filter(Boolean).join(", ") + ", ";
      } else {
        input.value = item.dataset.login;
      }
      input.dispatchEvent(new Event("input", {bubbles: true}));  // such as to save it
      close();
    }
    function mark(index) {
      var items = list.children;
      if (!items.length) { return; }
      active = (index + items.length) % items.length;
      Array.prototype.forEach.call(items, function (item, number) {
        item.setAttribute("aria-selected", number === active ? "true" : "false");
      });
      input.setAttribute("aria-activedescendant", items[active].id);
    }
    function show(people) {
      list.replaceChildren.apply(list, people.map(function (person, number) {
        var item = document.createElement("li");
        var avatar = document.createElement("img");
        var login = document.createElement("span");
        item.id = list.id + "-" + number;
        item.setAttribute("role", "option");
        item.dataset.login = person.login;
        avatar.className = "avatar";
        avatar.src = person.avatar;
        avatar.alt = "";
        avatar.width = avatar.height = 20;
        avatar.referrerPolicy = "no-referrer";
        login.textContent = "@" + person.login;
        item.append(avatar, " ", login);
        if (person.name) {
          var name = document.createElement("span");
          name.className = "muted";
          name.textContent = person.name;
          item.append(" ", name);
        }
        item.addEventListener("mousedown", function (event) {
          event.preventDefault();
          choose(item);
        });
        return item;
      }));
      if (people.length) {
        list.hidden = false;
        input.setAttribute("aria-expanded", "true");
      } else {
        close();
      }
    }
    function propose() {
      clearTimeout(timer);
      var text = typed();
      if (!text) { close(); return; }
      timer = setTimeout(function () {
        var address = input.dataset.completePeople;
        address += (address.indexOf("?") < 0 ? "?" : "&") + "q=" + encodeURIComponent(text);
        fetch(address, {credentials: "same-origin"})
          .then(function (answer) { return answer.ok ? answer.json() : {people: []}; })
          .then(function (data) { if (typed() === text) { show(data.people); } })
          .catch(function () {});
      }, 200);
    }
    input.addEventListener("input", propose);
    input.addEventListener("keydown", function (event) {
      if (list.hidden) { return; }
      if (event.key === "ArrowDown") { mark(active + 1); event.preventDefault(); }
      else if (event.key === "ArrowUp") { mark(active - 1); event.preventDefault(); }
      else if (event.key === "Enter" && active >= 0) { choose(list.children[active]); event.preventDefault(); }
      else if (event.key === "Escape") { close(); }
    });
    input.addEventListener("blur", close);
    input.dataset.completeConnected = "";  // ready: what was typed before is proposed now
    if (input.value.trim() && !several) { propose(); }
  }
  document.querySelectorAll("input[data-complete-people]").forEach(connect);
}());
