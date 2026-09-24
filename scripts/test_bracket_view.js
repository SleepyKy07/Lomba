/* Uji bracket_view.build tanpa browser: node scripts/test_bracket_view.js */
const fs = require("fs");
const path = require("path");

global.window = globalThis;
const src = fs.readFileSync(
  path.join(__dirname, "..", "docs", "js", "bracket_view.js"),
  "utf8"
);
eval(src);

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL", msg);
    process.exitCode = 1;
  } else {
    console.log("OK ", msg);
  }
}

function count(html, needle) {
  return html.split(needle).length - 1;
}

function noBad(html) {
  return !/NaN|undefined|Infinity/.test(html);
}

/* 8 peserta knockout + F3 (winner_count>1) */
const m8 = [
  ["L1-M01", "R1", "A", "B"],
  ["L1-M02", "R1", "C", "D"],
  ["L1-M03", "R1", "E", "F"],
  ["L1-M04", "R1", "G", "H"],
  ["L1-M05", "SF", null, null],
  ["L1-M06", "SF", null, null],
  ["L1-M07", "F3", "Kalah SF-1", "Kalah SF-2"],
  ["L1-M08", "F", null, null],
].map(([id, round, a, b]) => ({
  id,
  round,
  stage: "knockout",
  participant_a: a,
  participant_b: b,
  group: "",
  status: "scheduled",
}));

const html8 = TBracket.build(m8, [], "Futsal Cup");
assert(!!html8, "build 8-team menghasilkan HTML");
assert(count(html8, 'class="bm"') === 8, "8 kotak match (4+2+F3+F)");
assert(count(html8, "JUARA PERTAMA") === 1, "label JUARA PERTAMA");
assert(count(html8, "JUARA KE EMPAT") === 1, "label JUARA KE EMPAT");
assert(count(html8, 'class="ln ') >= 7, "ada garis penghubung");
assert(noBad(html8), "tanpa NaN/undefined");
assert(html8.indexOf("BAGAN PERTANDINGAN") > -1, "judul bagan");

/* winner highlight + asal grup (dari match fase grup) */
const m8w = JSON.parse(JSON.stringify(m8));
m8w[4].participant_a = "A";
m8w[4].participant_b = "C";
m8w.push({
  id: "L1-G01",
  round: "GA",
  stage: "group",
  participant_a: "A",
  participant_b: "B",
  group: "A",
  status: "scheduled",
});
const res = [{ match_id: "L1-M01", winner: "A", score_a: 2, score_b: 1 }];
const htmlW = TBracket.build(m8w, res, "Cup");
assert(htmlW.indexOf('bm-p win') > -1, "pemenang di-highlight");
assert(htmlW.indexOf('grp">(A)</span>') > -1, "label asal grup (A)");
assert(htmlW.indexOf("JUARA PERTAMA") > -1, "awards tetap ada");

/* bye: R1 cuma 2 match -> R2 2 match (n=6) */
const m6 = [
  ["X-M01", "R1", "A", "B"],
  ["X-M02", "R1", "C", "D"],
  ["X-M03", "R2", "E", null],
  ["X-M04", "R2", "F", null],
  ["X-M05", "SF", null, null],
  ["X-M06", "SF", null, null],
  ["X-M07", "F", null, null],
].map(([id, round, a, b]) => ({
  id,
  round,
  stage: "knockout",
  participant_a: a,
  participant_b: b,
  group: "",
  status: "scheduled",
}));
const html6 = TBracket.build(m6, [], "Bye Cup");
assert(count(html6, 'class="bm"') === 7, "n=6: 7 kotak");
assert(noBad(html6), "n=6 tanpa NaN");

/* 16 peserta (dua sisi penuh) */
const rounds = [
  ["R1", 8],
  ["R2", 4],
  ["SF", 2],
  ["F", 1],
];
let n = 0;
const m16 = [];
rounds.forEach(([lbl, cnt]) => {
  for (let i = 1; i <= cnt; i++) {
    n++;
    const id = "T-M" + String(n).padStart(2, "0");
    if (lbl === "F") {
      m16.push({
        id,
        round: lbl,
        stage: "knockout",
        participant_a: null,
        participant_b: null,
        group: "",
        status: "scheduled",
      });
    } else {
      m16.push({
        id,
        round: lbl,
        stage: "knockout",
        participant_a: null,
        participant_b: null,
        group: "",
        status: "scheduled",
      });
    }
  }
});
const html16 = TBracket.build(m16, [], "16 Tim");
assert(count(html16, 'class="bm"') === 15, "16 tim: 15 kotak (8+4+2+F)");
assert(noBad(html16), "16 tim tanpa NaN");

/* round-robin murni: tanpa knockout -> string kosong */
const rr = [
  {
    id: "G-A-1",
    round: "GA",
    stage: "group",
    participant_a: "A",
    participant_b: "B",
    group: "A",
    status: "scheduled",
  },
];
assert(TBracket.build(rr, [], "RR") === "", "round-robin -> kosong");

/* grup + knockout (group_knockout) */
const gk = [
  ...rr,
  {
    id: "K-M01",
    round: "SF",
    stage: "knockout",
    participant_a: "Juara Grup A",
    participant_b: "Juara Grup B",
    group: "",
    status: "scheduled",
  },
  {
    id: "K-M02",
    round: "SF",
    stage: "knockout",
    participant_a: "Juara Grup C",
    participant_b: "Juara Grup D",
    group: "",
    status: "scheduled",
  },
  {
    id: "K-M03",
    round: "F",
    stage: "knockout",
    participant_a: null,
    participant_b: null,
    group: "",
    status: "scheduled",
  },
];
const htmlGK = TBracket.build(gk, [], "Grup KO");
assert(count(htmlGK, 'class="bm"') === 3, "group_knockout: 3 kotak KO");
assert(htmlGK.indexOf("Juara Grup A") > -1, "slot qualifier tampil");
assert(noBad(htmlGK), "group_knockout tanpa NaN");

console.log(process.exitCode ? "TEST_FAIL" : "BRACKET_VIEW_OK");
