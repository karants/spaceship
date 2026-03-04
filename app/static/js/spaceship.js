/* ============================================================
   SPACESHIP — Core JavaScript
   Star field · Navigation · Photo protection
   ============================================================ */

(function () {
  "use strict";

  // ---- Star field ----
  var starContainer = document.getElementById("stars");
  if (starContainer) {
    var count = Math.min(120, Math.floor(window.innerWidth * window.innerHeight / 8000));
    for (var i = 0; i < count; i++) {
      var s = document.createElement("div");
      s.className = "star";
      var big = Math.random() > 0.85;
      s.style.cssText =
        "left:" + (Math.random() * 100) + "%;" +
        "top:" + (Math.random() * 100) + "%;" +
        "--d:" + (3 + Math.random() * 5) + "s;" +
        "--o:" + (0.2 + Math.random() * 0.5) + ";" +
        "width:" + (big ? 2 : 1) + "px;" +
        "height:" + (big ? 2 : 1) + "px;" +
        "animation-delay:" + (Math.random() * 6) + "s;";
      starContainer.appendChild(s);
    }
  }

  // ---- Burger navigation ----
  var btn = document.getElementById("burgerBtn");
  var drawer = document.getElementById("navDrawer");

  if (btn && drawer) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var isOpen = btn.classList.toggle("open");
      drawer.classList.toggle("open");
      btn.setAttribute("aria-expanded", isOpen);
    });

    document.addEventListener("click", function (e) {
      if (!drawer.contains(e.target) && !btn.contains(e.target)) {
        btn.classList.remove("open");
        drawer.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        btn.classList.remove("open");
        drawer.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  // ---- Photo protection ----
  // Block right-click on images and their wrappers
  document.addEventListener("contextmenu", function (e) {
    if (e.target.tagName === "IMG" ||
        e.target.closest(".gallery-img-wrap") ||
        e.target.closest(".mission-photo-wrap")) {
      e.preventDefault();
    }
  });

  // Block image drag
  document.addEventListener("dragstart", function (e) {
    if (e.target.tagName === "IMG") {
      e.preventDefault();
    }
  });

  // Mild PrintScreen deterrent — briefly blank the page
  document.addEventListener("keyup", function (e) {
    if (e.key === "PrintScreen") {
      document.body.style.opacity = "0";
      setTimeout(function () {
        document.body.style.opacity = "1";
      }, 200);
    }
  });

  // Block Ctrl+S (save page)
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
    }
  });

})();
