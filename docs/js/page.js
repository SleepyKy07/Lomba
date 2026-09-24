/** Subnav lomba + util engine status (shared detail pages). */
(function (global) {
  "use strict";

  function lombaSubnav(active) {
    var id = TUI.qs("id") || "";
    var base = "lomba_detail.html?id=" + encodeURIComponent(id);
    var tabs = [
      ["ringkasan", base, "Ringkasan"],
      ["hasil", base + "&tab=hasil", "Hasil & klasemen"],
      ["manual", base + "&tab=manual", "Manual & WO"],
      ["whatif", base + "&tab=whatif", "What-if"],
      ["prob", base + "&tab=prob", "Probabilitas"],
    ];
    var nav = document.createElement("nav");
    nav.className = "subnav";
    tabs.forEach(function (t) {
      var a = document.createElement("a");
      a.href = t[1];
      a.textContent = t[2];
      if (t[0] === active) a.className = "primary";
      nav.appendChild(a);
    });
    var host = document.getElementById("subnav");
    if (host) {
      host.innerHTML = "";
      host.appendChild(nav);
      host.hidden = false;
    }
  }

  function showEngine(msg, isErr) {
    var el = document.getElementById("engine-status");
    if (!el) return;
    if (!msg) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    el.textContent = msg;
    el.style.background = isErr ? "#fef2f2" : "#eff6ff";
    el.style.borderColor = isErr ? "#fca5a5" : "#bfdbfe";
    el.style.color = isErr ? "#991b1b" : "#1e40af";
  }

  function showLoginCta(msg, next) {
    var cta = document.getElementById("login-cta");
    if (!cta) return;
    cta.hidden = true;
    cta.innerHTML = "";
  }

  function guardOrCta(msg) {
    return true;
  }

  global.TPage = {
    lombaSubnav: lombaSubnav,
    showEngine: showEngine,
    showLoginCta: showLoginCta,
    guardOrCta: guardOrCta,
  };
})(window);
