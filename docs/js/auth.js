/** Supabase Auth (GoTrue REST) — email + password. Token disimpan di sessionStorage. */
(function (global) {
  "use strict";

  var KEY = "t_sim_auth";

  function cfg() {
    var c = global.APP_CONFIG || {};
    return {
      url: String(c.SUPABASE_URL || "").replace(/\/$/, ""),
      key: String(c.SUPABASE_ANON_KEY || ""),
    };
  }

  function authHeaders(extra) {
    var c = cfg();
    var h = {
      apikey: c.key,
      "Content-Type": "application/json",
    };
    if (extra) {
      Object.keys(extra).forEach(function (k) {
        h[k] = extra[k];
      });
    }
    return h;
  }

  function loadSession() {
    try {
      var raw = sessionStorage.getItem(KEY);
      if (!raw) return null;
      var s = JSON.parse(raw);
      if (!s || !s.access_token) return null;
      if (s.expires_at && Date.now() / 1000 > s.expires_at - 30) {
        return null;
      }
      return s;
    } catch (e) {
      return null;
    }
  }

  function saveSession(s) {
    if (!s || !s.access_token) {
      sessionStorage.removeItem(KEY);
      return null;
    }
    sessionStorage.setItem(KEY, JSON.stringify(s));
    return s;
  }

  function clearSession() {
    sessionStorage.removeItem(KEY);
  }

  function getSession() {
    return loadSession();
  }

  function getAccessToken() {
    var s = loadSession();
    return s ? s.access_token : null;
  }

  function getUser() {
    var s = loadSession();
    if (!s) return null;
    return s.user || null;
  }

  function isLoggedIn() {
    return !!getAccessToken();
  }

  async function parseError(res) {
    var text = await res.text();
    var data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (e) {
        data = text;
      }
    }
    var msg =
      (data && data.error_description) ||
      (data && data.msg) ||
      (data && data.message) ||
      (data && data.error) ||
      "HTTP " + res.status;
    var err = new Error(msg);
    err.status = res.status;
    err.data = data;
    return err;
  }

  async function signUp(email, password) {
    if (!global.TApi || !global.TApi.isConfigured()) {
      throw new Error("Supabase belum dikonfigurasi di docs/js/config.js.");
    }
    var c = cfg();
    var res = await fetch(c.url + "/auth/v1/signup", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ email: email, password: password }),
    });
    if (!res.ok) throw await parseError(res);
    var data = await res.json();
    if (data && data.access_token) {
      saveSession(data);
    }
    return data;
  }

  async function signIn(email, password) {
    if (!global.TApi || !global.TApi.isConfigured()) {
      throw new Error("Supabase belum dikonfigurasi di docs/js/config.js.");
    }
    var c = cfg();
    var res = await fetch(c.url + "/auth/v1/token?grant_type=password", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ email: email, password: password }),
    });
    if (!res.ok) throw await parseError(res);
    var data = await res.json();
    saveSession(data);
    return data;
  }

  async function signOut() {
    var token = getAccessToken();
    clearSession();
    if (!token) return;
    try {
      var c = cfg();
      await fetch(c.url + "/auth/v1/logout", {
        method: "POST",
        headers: authHeaders({ Authorization: "Bearer " + token }),
      });
    } catch (e) {
      /* session lokal sudah dibersihkan */
    }
  }

  function requireLogin(redirect) {
    if (isLoggedIn()) return true;
    var next = redirect || global.location.pathname.split("/").pop() || "index.html";
    global.location.href = "login.html?next=" + encodeURIComponent(next);
    return false;
  }

  global.TAuth = {
    getSession: getSession,
    getAccessToken: getAccessToken,
    getUser: getUser,
    isLoggedIn: isLoggedIn,
    signUp: signUp,
    signIn: signIn,
    signOut: signOut,
    requireLogin: requireLogin,
    clearSession: clearSession,
  };
})(window);
