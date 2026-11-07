/* Apply the saved archive focus mode before the page paints. */
(function () {
  "use strict";

  var root = document.documentElement;

  try {
    var saved = window.localStorage.getItem("archive-focus-mode");
    if (saved === "green") {
      root.classList.add("green-mode");
    } else if (saved === "red") {
      root.classList.remove("green-mode");
    }
  } catch (error) {
    /* Storage can be unavailable in strict privacy modes. */
  }

  root.classList.remove("no-js");
  root.classList.add("js");
})();
