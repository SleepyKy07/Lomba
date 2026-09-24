/** REST client Supabase (PostgREST) — anon key + Bearer JWT sesi login. */
(function (global) {
  "use strict";

  function cfg() {
    var c = global.APP_CONFIG || {};
    return {
      url: String(c.SUPABASE_URL || "").replace(/\/$/, ""),
      key: String(c.SUPABASE_ANON_KEY || ""),
    };
  }

  function isConfigured() {
    var c = cfg();
    return (
      c.url &&
      c.key &&
      c.url.indexOf("YOUR_PROJECT_REF") === -1 &&
      c.key.indexOf("YOUR_ANON_PUBLIC_KEY") === -1 &&
      /^https?:\/\//.test(c.url)
    );
  }

  function looksLikeServiceRole(key) {
    return /service_role|sb_secret_/i.test(String(key || ""));
  }

  function bearer() {
    var token =
      global.TAuth && TAuth.getAccessToken ? TAuth.getAccessToken() : null;
    return token || cfg().key;
  }

  function headers(extra) {
    var c = cfg();
    var h = {
      apikey: c.key,
      Authorization: "Bearer " + bearer(),
      "Content-Type": "application/json",
    };
    if (extra) {
      Object.keys(extra).forEach(function (k) {
        h[k] = extra[k];
      });
    }
    return h;
  }

  async function request(method, path, body, extraHeaders) {
    if (looksLikeServiceRole(cfg().key)) {
      throw new Error(
        "Konfigurasi tidak aman: terdeteksi service_role/secret di config.js. Ganti dengan anon public key."
      );
    }
    if (!isConfigured()) {
      throw new Error(
        "Supabase belum dikonfigurasi. Isi docs/js/config.js (Project URL + anon public key)."
      );
    }
    var res = await fetch(cfg().url + path, {
      method: method,
      headers: headers(extraHeaders),
      body: body === undefined || body === null ? undefined : JSON.stringify(body),
    });
    var text = await res.text();
    var data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (e) {
        data = text;
      }
    }
    if (!res.ok) {
      var msg =
        (data && data.message) ||
        (data && data.error_description) ||
        (data && data.error) ||
        ("HTTP " + res.status);
      var err = new Error(msg);
      err.status = res.status;
      err.data = data;
      if (res.status === 401 || res.status === 403) {
        err.needAuth = true;
      }
      throw err;
    }
    return data;
  }

  var api = {
    isConfigured: isConfigured,
    looksLikeServiceRole: looksLikeServiceRole,
    request: request,

    listClasses: function () {
      return request("GET", "/rest/v1/classes?select=*&order=id.asc");
    },

    addClass: function (row) {
      var payload = {
        id: row.id,
        name: row.name || row.id,
        tingkat: row.tingkat || "",
        jurusan: row.jurusan || "",
      };
      if (global.TAuth && TAuth.getUser && TAuth.getUser()) {
        payload.owner_id = TAuth.getUser().id;
      }
      return request("POST", "/rest/v1/classes", payload, {
        Prefer: "return=representation",
      });
    },

    deleteClass: function (id) {
      return request(
        "DELETE",
        "/rest/v1/classes?id=eq." + encodeURIComponent(id),
        null,
        { Prefer: "return=representation" }
      );
    },

    getMeta: function () {
      return request("GET", "/rest/v1/meta?select=key,value");
    },

    listTournaments: function () {
      return request(
        "GET",
        "/rest/v1/tournaments?select=id,name,format,participant_ids,owner_id,created_at&order=id.asc"
      );
    },

    getTournament: function (id) {
      return request(
        "GET",
        "/rest/v1/tournaments?id=eq." + encodeURIComponent(id) + "&limit=1"
      );
    },

    createTournament: function (row) {
      if (global.TAuth && TAuth.getUser && TAuth.getUser()) {
        row = Object.assign({}, row, { owner_id: TAuth.getUser().id });
      }
      return request("POST", "/rest/v1/tournaments", row, {
        Prefer: "return=representation",
      });
    },

    updateTournament: function (id, patch) {
      return request(
        "PATCH",
        "/rest/v1/tournaments?id=eq." + encodeURIComponent(id),
        patch,
        { Prefer: "return=representation" }
      );
    },

    deleteTournament: function (id) {
      return request(
        "DELETE",
        "/rest/v1/tournaments?id=eq." + encodeURIComponent(id),
        null,
        { Prefer: "return=representation" }
      );
    },

    getMetaKey: async function (key) {
      var rows = await request(
        "GET",
        "/rest/v1/meta?key=eq." + encodeURIComponent(key) + "&select=key,value"
      );
      return rows && rows[0] ? rows[0].value : null;
    },

    setMetaKey: function (key, value) {
      return request(
        "POST",
        "/rest/v1/meta",
        { key: key, value: String(value) },
        { Prefer: "resolution=merge-duplicates,return=representation" }
      );
    },

    nextLombaId: async function () {
      var cur = await api.getMetaKey("seq");
      var n = (parseInt(cur, 10) || 0) + 1;
      await api.setMetaKey("seq", n);
      return "L" + n;
    },

    listResults: function (tournamentId) {
      return request(
        "GET",
        "/rest/v1/results?tournament_id=eq." +
          encodeURIComponent(tournamentId) +
          "&select=match_id,winner,score_a,score_b"
      );
    },

    upsertResults: function (tournamentId, rows) {
      var payload = (rows || []).map(function (r) {
        var body = {
          tournament_id: tournamentId,
          match_id: r.match_id,
          winner: r.winner == null ? null : r.winner,
          score_a: r.score_a | 0,
          score_b: r.score_b | 0,
        };
        if (global.TAuth && TAuth.getUser && TAuth.getUser()) {
          body.owner_id = TAuth.getUser().id;
        }
        return body;
      });
      if (!payload.length) return Promise.resolve([]);
      return request("POST", "/rest/v1/results", payload, {
        Prefer: "resolution=merge-duplicates,return=representation",
      });
    },

    deleteResult: function (tournamentId, matchId) {
      return request(
        "DELETE",
        "/rest/v1/results?tournament_id=eq." +
          encodeURIComponent(tournamentId) +
          "&match_id=eq." +
          encodeURIComponent(matchId)
      );
    },

    deleteResultsForTournament: function (tournamentId) {
      return request(
        "DELETE",
        "/rest/v1/results?tournament_id=eq." + encodeURIComponent(tournamentId)
      );
    },
  };

  global.TApi = api;
})(window);
