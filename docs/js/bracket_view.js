/** Bagan knockout horizontal dua sisi + tengah (ala bagan turnamen cetak).
 *  Murni string HTML — bisa diuji di Node (stub window dulu).
 *  Dipakai lomba_detail.js (tab Ringkasan).
 */
(function (global) {
  "use strict";

  var ORDER = ["P", "R1", "R2", "R3", "R4", "R5", "R6", "SF", "F3", "F"];
  var BOX_W = 150;
  var BOX_H = 56;
  var COL_W = 180;
  var SLOT = 66;
  var MIN_H = 240;
  var CENTER_W = 210;
  var AW_H = 92; /* tinggi blok 2 label+nilai juara */

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function rank(lbl) {
    var i = ORDER.indexOf(lbl);
    if (i >= 0) return i;
    var m = /^R(\d+)$/.exec(lbl);
    if (m) return 10 + parseInt(m[1], 10);
    return 100;
  }

  function sortLabels(labels) {
    return labels.slice().sort(function (a, b) {
      var d = rank(a) - rank(b);
      if (d) return d;
      return a < b ? -1 : a > b ? 1 : 0;
    });
  }

  function isReal(pid) {
    return (
      !!pid &&
      pid !== "TBD" &&
      !/^(TBD|Juara |Kalah |Peringkat )/.test(pid)
    );
  }

  function lnH(x, y, w) {
    if (w <= 0) w = 1;
    return (
      '<div class="ln h" style="left:' + x + "px;top:" + y + "px;width:" + w + 'px"></div>'
    );
  }

  function lnV(x, y, h) {
    if (h <= 0) h = 1;
    return (
      '<div class="ln v" style="left:' + x + "px;top:" + y + "px;height:" + h + 'px"></div>'
    );
  }

  /** Garis siku antar dua kotak (ya/yb = titik tengah vertikal box). */
  function conn(out, ya, ea, yb, eb) {
    var mid = (ea + eb) / 2;
    out.push(lnH(Math.min(ea, mid), ya, Math.abs(mid - ea)));
    out.push(lnV(mid, Math.min(ya, yb), Math.abs(yb - ya)));
    out.push(lnH(Math.min(mid, eb), yb, Math.abs(eb - mid)));
  }

  function boxHtml(m, x, yTop, ctx) {
    var res = ctx.res[m.id] || {};
    var winner = res.winner || null;

    function p(pid) {
      var shown = pid == null || pid === "" ? "TBD" : pid;
      var cls = "bm-p";
      if (winner && shown === winner) cls += " win";
      else if (winner && isReal(shown)) cls += " lose";
      var g = ctx.groups[shown]
        ? ' <span class="grp">(' + esc(ctx.groups[shown]) + ")</span>"
        : "";
      return '<div class="' + cls + '">' + esc(shown) + g + "</div>";
    }

    return (
      '<div class="bm" style="left:' + x + "px;top:" + yTop + 'px">' +
      '<div class="bm-h"><span>' +
      esc(m.id) +
      "</span><span>" +
      esc(m.round) +
      (m.status === "walkover" ? " WO" : "") +
      "</span></div>" +
      p(m.participant_a) +
      p(m.participant_b) +
      "</div>"
    );
  }

  function winnerOf(res, m) {
    if (!m) return null;
    var r = res[m.id];
    return (r && r.winner) || null;
  }

  function otherOf(m, winner) {
    if (!m || !winner) return null;
    if (m.participant_a === winner) return m.participant_b;
    if (m.participant_b === winner) return m.participant_a;
    return null;
  }

  function awardsHtml(f, f3, res, cx, top, bot) {
    var fw = winnerOf(res, f);
    var f3w = winnerOf(res, f3);
    var p1 = fw || "TBD";
    var p2 = otherOf(f, fw) || "TBD";
    var html =
      '<div class="awards" style="left:' + cx + "px;top:" + top + "px;width:" + CENTER_W + 'px">' +
      '<div class="lbl">JUARA PERTAMA</div><div class="val">' + esc(p1) + "</div>" +
      '<div class="lbl">JUARA KEDUA</div><div class="val">' + esc(p2) + "</div>" +
      "</div>";
    if (f3) {
      var p3 = f3w || "TBD";
      var p4 = otherOf(f3, f3w) || "TBD";
      html +=
        '<div class="awards" style="left:' + cx + "px;top:" + bot + "px;width:" + CENTER_W + 'px">' +
        '<div class="lbl">JUARA KETIGA</div><div class="val">' + esc(p3) + "</div>" +
        '<div class="lbl">JUARA KE EMPAT</div><div class="val">' + esc(p4) + "</div>" +
        "</div>";
    }
    return html;
  }

  function build(matches, results, title) {
    matches = matches || [];
    var f = null;
    var f3 = null;
    var ko = [];
    var groups = {};
    matches.forEach(function (m) {
      if (m.stage === "group") {
        if (m.group) {
          if (m.participant_a) groups[m.participant_a] = m.group;
          if (m.participant_b) groups[m.participant_b] = m.group;
        }
        return;
      }
      if (m.round === "F3") {
        f3 = m;
        return;
      }
      if (m.round === "F") {
        if (!f) f = m;
        return;
      }
      ko.push(m);
    });
    if (!f && !ko.length) return "";

    var res = {};
    (results || []).forEach(function (r) {
      if (r && r.match_id) res[r.match_id] = r;
    });

    var by = {};
    ko.forEach(function (m) {
      (by[m.round] = by[m.round] || []).push(m);
    });
    var labels = sortLabels(Object.keys(by));
    var T = labels.length;
    var sides = labels.map(function (lbl) {
      var ms = by[lbl];
      var cut = Math.ceil(ms.length / 2);
      return { left: ms.slice(0, cut), right: ms.slice(cut) };
    });

    var L0 = sides.length ? sides[0].left.length : 0;
    var R0 = sides.length ? sides[0].right.length : 0;
    var topH = AW_H + BOX_H / 2;
    var botH =
      BOX_H / 2 + (f3 ? 24 + BOX_H + 8 : 0) + (f3 ? AW_H : 24);
    var H = Math.max(MIN_H, L0 * SLOT, R0 * SLOT, 2 * topH, 2 * botH);
    var Hc = H / 2;

    var yC = sides.map(function () {
      return { left: [], right: [] };
    });
    sides.forEach(function (sd, t) {
      sd.left.forEach(function (m, i) {
        yC[t].left[i] = ((i + 0.5) * H) / (L0 || 1);
      });
      sd.right.forEach(function (m, j) {
        yC[t].right[j] = ((j + 0.5) * H) / (R0 || 1);
      });
    });
    for (var t = 1; t < T; t++) {
      ["left", "right"].forEach(function (side) {
        var prev = sides[t - 1][side];
        var cur = sides[t][side];
        var yp = yC[t - 1][side];
        var yc = yC[t][side];
        var m = prev.length;
        var k = cur.length;
        if (!m || !k) return;
        cur.forEach(function (_, j) {
          var s = Math.floor((j * m) / k);
          var e = Math.floor(((j + 1) * m) / k);
          if (e <= s) e = s + 1;
          if (e > m) e = m;
          var sum = 0;
          for (var q = s; q < e; q++) sum += yp[q];
          yc[j] = sum / (e - s);
        });
      });
    }

    var cx = T * COL_W;
    var fX = cx + Math.round((CENTER_W - BOX_W) / 2);
    var rx = cx + CENTER_W;

    function xL(t) {
      return t * COL_W;
    }
    function xR(t) {
      return rx + (T - 1 - t) * COL_W;
    }
    var W = rx + T * COL_W;

    var ctx = { res: res, groups: groups };
    var out = [];

    sides.forEach(function (sd, t) {
      sd.left.forEach(function (m, i) {
        out.push(boxHtml(m, xL(t), yC[t].left[i] - BOX_H / 2, ctx));
      });
      sd.right.forEach(function (m, j) {
        out.push(boxHtml(m, xR(t), yC[t].right[j] - BOX_H / 2, ctx));
      });
    });

    for (var r0 = 0; r0 + 1 < T; r0++) {
      (function (t, tn) {
        ["left", "right"].forEach(function (side) {
          var cur = sides[t][side];
          var nxt = sides[tn][side];
          var m = cur.length;
          var k = nxt.length;
          if (!m || !k) return;
          cur.forEach(function (_, i) {
            var j = Math.min(k - 1, Math.floor((i * k) / m));
            if (side === "left") {
              conn(
                out,
                yC[t].left[i],
                xL(t) + BOX_W,
                yC[tn].left[j],
                xL(tn)
              );
            } else {
              conn(out, yC[t].right[i], xR(t), yC[tn].right[j], xR(tn) + BOX_W);
            }
          });
        });
      })(r0, r0 + 1);
    }

    if (f && T > 0) {
      var last = T - 1;
      sides[last].left.forEach(function (m, i) {
        conn(out, yC[last].left[i], xL(last) + BOX_W, Hc, fX);
      });
      sides[last].right.forEach(function (m, j) {
        conn(out, yC[last].right[j], xR(last), Hc, fX + BOX_W);
      });
    }

    var fTop = Hc - BOX_H / 2;
    if (f) {
      out.push(boxHtml(f, fX, fTop, ctx));
    }
    var f3Top = fTop + BOX_H + 24;
    if (f3) {
      out.push(boxHtml(f3, fX, f3Top, ctx));
    }
    var awTop = fTop - AW_H;
    var awBot = f3 ? f3Top + BOX_H + 8 : fTop + BOX_H + 24;
    out.push(awardsHtml(f, f3, res, cx, awTop, awBot));

    return (
      '<div class="brk-wrap"><div class="brk-title">BAGAN PERTANDINGAN — ' +
      esc(title || "") +
      '</div><div class="brk" style="width:' +
      W +
      "px;height:" +
      H +
      'px">' +
      out.join("") +
      "</div></div>"
    );
  }

  function render(host, matches, results, title) {
    if (!host) return false;
    var html = build(matches, results, title);
    host.innerHTML = html;
    return !!html;
  }

  global.TBracket = { build: build, render: render };
})(window);
