/** Pyodide loader — engine Python asli di browser (Tahap 3–4). */
(function (global) {
  "use strict";

  var PYODIDE_VERSION = "0.26.4";
  var PYODIDE_BASE =
    "https://cdn.jsdelivr.net/pyodide/v" + PYODIDE_VERSION + "/full/";

  var ENGINE_FILES = [
    "__init__.py",
    "models.py",
    "registry.py",
    "generator.py",
    "generator_group.py",
    "generator_knockout.py",
    "generator_roundrobin.py",
    "fairness.py",
    "scheduler.py",
    "analysis.py",
    "bracket.py",
    "results.py",
    "manual.py",
    "comparison.py",
    "whatif.py",
    "cross_event.py",
    "multi.py",
    "probability.py",
  ];

  var BRIDGE = [
    "import json",
    "from tournament import (",
    "    Tournament, build_report, generate_scheme,",
    "    render_bracket, render_schedule, render_fairness,",
    "    analyze_existing,",
    "    advance_scheme, build_standings, clear_result, record_result, render_standings,",
    "    compare_reports, render_comparison, what_if,",
    "    detect_cross_event_conflicts, total_load_across_events,",
    "    optimize_multi_event,",
    "    equal_model, custom_model, percent_model, monte_carlo, render_probability,",
    "    exact_equal_title_probability,",
    "    is_placeholder,",
    "    set_walkover, swap_slots, move_match, replace_participant,",
    ")",
    "from tournament.models import (",
    "    Match, Scheme, ScheduledMatch, ByeDetail, Result,",
    ")",
    "",
    "def _scheduled_from_list(t, arr):",
    "    out = []",
    "    for s in arr or []:",
    "        m = s['match']",
    "        out.append(ScheduledMatch(",
    "            match=Match(",
    "                id=m['id'], tournament_id=t.id, round=m['round'],",
    "                stage=m['stage'], participant_a=m.get('participant_a'),",
    "                participant_b=m.get('participant_b'),",
    "                group=m.get('group') or '', status=m.get('status') or 'scheduled'),",
    "            scheduled_time=s['scheduled_time'], arena=int(s['arena']),",
    "            start_min=int(s.get('start_min') or 0)))",
    "    return out",
    "",
    "def _scheduled_to_list(scheduled):",
    "    return [{",
    "        'match': {",
    "            'id': s.match.id, 'round': s.match.round, 'stage': s.match.stage,",
    "            'participant_a': s.match.participant_a,",
    "            'participant_b': s.match.participant_b,",
    "            'group': s.match.group, 'status': s.match.status,",
    "        },",
    "        'scheduled_time': s.scheduled_time, 'arena': s.arena,",
    "        'start_min': s.start_min,",
    "    } for s in scheduled]",
    "",
    "def _scheme_from_dict(d, t):",
    "    matches = [Match(",
    "        id=m['id'], tournament_id=t.id, round=m['round'],",
    "        stage=m['stage'], participant_a=m.get('participant_a'),",
    "        participant_b=m.get('participant_b'),",
    "        group=m.get('group') or '', status=m.get('status') or 'scheduled')",
    "        for m in d.get('matches') or []]",
    "    byes = [ByeDetail(",
    "        participant=b['participant'], entry_round=b['entry_round'],",
    "        skipped_rounds=list(b.get('skipped_rounds') or []),",
    "        wins_needed=int(b['wins_needed']))",
    "        for b in d.get('bye_details') or []]",
    "    return Scheme(",
    "        tournament=t, participant_ids=list(d.get('participant_ids') or []),",
    "        matches=matches, notes=list(d.get('notes') or []), bye_details=byes)",
    "",
    "def _tournament_from_row(row):",
    "    return Tournament(",
    "        id=row['id'], name=row['name'], format=row['format'],",
    "        team_size=int(row.get('team_size') or 4),",
    "        winner_count=int(row.get('winner_count') or 1),",
    "        duration_min=int(row.get('duration_min') or 30),",
    "        minimum_rest_min=int(row.get('minimum_rest_min') or 10),",
    "        arena_count=int(row.get('arena_count') or 2),",
    "        date=row.get('date') or '',",
    "        start_time=row.get('start_time') or '08:00',",
    "        end_time=row.get('end_time') or '17:00',",
    "        qualify_per_group=int(row.get('qualify_per_group') or 1))",
    "",
    "def _results_from_list(arr):",
    "    out = {}",
    "    for r in arr or []:",
    "        mid = r.get('match_id') or r.get('id')",
    "        if not mid:",
    "            continue",
    "        out[mid] = Result(",
    "            match_id=mid,",
    "            winner=r.get('winner'),",
    "            score_a=int(r.get('score_a') or 0),",
    "            score_b=int(r.get('score_b') or 0))",
    "    return out",
    "",
    "def _results_to_list(results, tid):",
    "    return [{",
    "        'tournament_id': tid, 'match_id': mid,",
    "        'winner': res.winner, 'score_a': res.score_a, 'score_b': res.score_b,",
    "    } for mid, res in (results or {}).items()]",
    "",
    "def _report_dict(rep):",
    "    return {",
    "        'scheme': rep.scheme.to_dict(),",
    "        'scheduled': _scheduled_to_list(rep.scheduled),",
    "        'notes': list(rep.scheme.notes),",
    "        'sched_errors': list(rep.sched_errors),",
    "        'bracket': render_bracket(rep.scheme.matches),",
    "        'schedule': render_schedule(rep.scheduled),",
    "        'fairness': render_fairness(rep.fairness, rep.rest, rep.conflicts),",
    "        'summary': rep.summary_row(),",
    "        'conflicts': list(rep.conflicts),",
    "    }",
    "",
    "def create_report_json(row):",
    "    t = _tournament_from_row(row)",
    "    pids = list(row.get('participant_ids') or [])",
    "    ng = row.get('num_groups')",
    "    ng = int(ng) if ng is not None and ng != '' else None",
    "    rep = build_report(t, pids, ng)",
    "    return json.dumps(_report_dict(rep), ensure_ascii=False)",
    "",
    "def analyze_saved_json(row, scheme_d, scheduled_list):",
    "    t = _tournament_from_row(row)",
    "    scheme = _scheme_from_dict(scheme_d, t)",
    "    scheduled = _scheduled_from_list(t, scheduled_list) if scheduled_list else None",
    "    rep = analyze_existing(scheme, scheduled)",
    "    return json.dumps(_report_dict(rep), ensure_ascii=False)",
    "",
    "def standings_json(row, scheme_d, results_list):",
    "    t = _tournament_from_row(row)",
    "    scheme = _scheme_from_dict(scheme_d, t)",
    "    results = _results_from_list(results_list)",
    "    shown = advance_scheme(scheme, results) if results else scheme",
    "    tables = build_standings(scheme, results)",
    "    text = render_standings(tables, results)",
    "    matches = []",
    "    for m in shown.matches:",
    "        res = results.get(m.id)",
    "        ready = (",
    "            m.status != 'walkover'",
    "            and m.participant_a is not None and m.participant_b is not None",
    "            and not is_placeholder(m.participant_a)",
    "            and not is_placeholder(m.participant_b)",
    "        )",
    "        matches.append({",
    "            'id': m.id, 'round': m.round, 'stage': m.stage,",
    "            'status': m.status, 'group': m.group or '',",
    "            'participant_a': m.participant_a, 'participant_b': m.participant_b,",
    "            'ready': ready,",
    "            'score_a': res.score_a if res else None,",
    "            'score_b': res.score_b if res else None,",
    "            'has_result': res is not None,",
    "        })",
    "    return json.dumps({",
    "        'standings': text,",
    "        'matches': matches,",
    "        'score_count': len(results),",
    "    }, ensure_ascii=False)",
    "",
    "def record_score_json(row, scheme_d, results_list, match_id, sa, sb):",
    "    t = _tournament_from_row(row)",
    "    scheme = _scheme_from_dict(scheme_d, t)",
    "    results = _results_from_list(results_list)",
    "    try:",
    "        res = record_result(scheme, match_id, int(sa), int(sb), results=results)",
    "    except ValueError as e:",
    "        return json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False)",
    "    results[match_id] = res",
    "    return json.dumps({",
    "        'ok': True,",
    "        'results': _results_to_list(results, t.id),",
    "        'score_count': len(results),",
    "    }, ensure_ascii=False)",
    "",
    "def clear_score_json(row, scheme_d, results_list, match_id):",
    "    t = _tournament_from_row(row)",
    "    _scheme_from_dict(scheme_d, t)",
    "    results = _results_from_list(results_list)",
    "    try:",
    "        results = clear_result(results, match_id)",
    "    except ValueError as e:",
    "        return json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False)",
    "    return json.dumps({",
    "        'ok': True,",
    "        'results': _results_to_list(results, t.id),",
    "        'score_count': len(results),",
    "    }, ensure_ascii=False)",
    "",
    "def whatif_json(row, scheme_d, changes, num_groups=None):",
    "    t = _tournament_from_row(row)",
    "    pids = list(row.get('participant_ids') or [])",
    "    # before dari skema tersimpan bila ada",
    "    try:",
    "        before_scheme = _scheme_from_dict(scheme_d, t) if scheme_d else None",
    "    except Exception:",
    "        before_scheme = None",
    "    before, after = what_if(t, pids, dict(changes), num_groups)",
    "    if before_scheme is not None:",
    "        from tournament.analysis import analyze_existing",
    "        try:",
    "            before = analyze_existing(before_scheme, None)",
    "        except Exception:",
    "            pass",
    "    table = compare_reports([before, after], ['sebelum', 'sesudah'])",
    "    return json.dumps({",
    "        'comparison': render_comparison(['sebelum', 'sesudah'], table),",
    "        'before': before.summary_row(),",
    "        'after': after.summary_row(),",
    "        'scheme_after': after.scheme.to_dict(),",
    "        'notes': list(after.scheme.notes),",
    "        'after_pids': list(after.scheme.participant_ids),",
    "    }, ensure_ascii=False)",
    "",
    "def probability_json(row, scheme_d, mode, bobot, n, seed):",
    "    t = _tournament_from_row(row)",
    "    scheme = _scheme_from_dict(scheme_d, t)",
    "    pids = scheme.participant_ids",
    "    if mode == 'equal':",
    "        model = equal_model(pids)",
    "    elif mode == 'persen':",
    "        model = percent_model(bobot or {}, pids)",
    "    else:",
    "        model = custom_model(bobot or {}, pids)",
    "    n = int(n or 2000)",
    "    seed = int(seed) if seed is not None and seed != '' else None",
    "    mc = monte_carlo(scheme, model, n=n, seed=seed)",
    "    exact = None",
    "    if mode == 'equal':",
    "        try:",
    "            exact = exact_equal_title_probability(scheme)",
    "        except Exception:",
    "            exact = None",
    "    return json.dumps({",
    "        'render': render_probability(mc),",
    "        'exact': exact,",
    "        'n': mc.n,",
    "        'model_desc': mc.model_desc,",
    "    }, ensure_ascii=False)",
    "",
    "def banding_json(rows):",
    "    reps = []",
    "    labels = []",
    "    for row in rows:",
    "        t = _tournament_from_row(row)",
    "        pids = list(row.get('participant_ids') or [])",
    "        ng = row.get('num_groups')",
    "        ng = int(ng) if ng is not None and ng != '' else None",
    "        if row.get('manual_scheme'):",
    "            scheme = _scheme_from_dict(row['manual_scheme'], t)",
    "            scheduled = row.get('manual_scheduled')",
    "            rep = analyze_existing(",
    "                scheme,",
    "                _scheduled_from_list(t, scheduled) if scheduled else None,",
    "            )",
    "        else:",
    "            rep = build_report(t, pids, ng)",
    "        reps.append(rep)",
    "        labels.append(str(row.get('id') or t.id))",
    "    table = compare_reports(reps, labels)",
    "    return json.dumps({",
    "        'comparison': render_comparison(labels, table),",
    "        'labels': labels,",
    "        'summaries': [r.summary_row() for r in reps],",
    "    }, ensure_ascii=False)",
    "",
    "def lintas_json(rows):",
    "    reps = []",
    "    for row in rows:",
    "        t = _tournament_from_row(row)",
    "        if row.get('manual_scheme'):",
    "            scheme = _scheme_from_dict(row['manual_scheme'], t)",
    "            scheduled = row.get('manual_scheduled')",
    "            rep = analyze_existing(",
    "                scheme,",
    "                _scheduled_from_list(t, scheduled) if scheduled else None,",
    "            )",
    "        else:",
    "            rep = build_report(t, list(row.get('participant_ids') or []))",
    "        reps.append(rep)",
    "    findings = detect_cross_event_conflicts(reps)",
    "    total = total_load_across_events(reps)",
    "    load_txt = '\\n'.join(f'{k}: {v}' for k, v in total.items()) or '(kosong)'",
    "    return json.dumps({",
    "        'findings': findings,",
    "        'total_load': load_txt,",
    "        'total_map': total,",
    "    }, ensure_ascii=False)",
    "",
    "def optimasi_json(rows, max_shift_batches):",
    "    specs = []",
    "    labels = []",
    "    for row in rows:",
    "        t = _tournament_from_row(row)",
    "        pids = list(row.get('participant_ids') or [])",
    "        specs.append((t, pids))",
    "        labels.append(str(row.get('id') or t.id))",
    "    after, notes = optimize_multi_event(",
    "        specs, max_shift_batches=int(max_shift_batches or 12))",
    "    left = detect_cross_event_conflicts(after)",
    "    return json.dumps({",
    "        'notes': notes,",
    "        'left': left,",
    "        'labels': labels,",
    "        'summaries': [r.summary_row() for r in after],",
    "    }, ensure_ascii=False)",
    "",
    "def manual_json(op, row, scheme_d, scheduled_list, params):",
    "    t = _tournament_from_row(row)",
    "    scheme = _scheme_from_dict(scheme_d, t)",
    "    params = params or {}",
    "    clear_results = False",
    "    new_pids = list(scheme.participant_ids)",
    "    try:",
    "        if op == 'walkover':",
    "            scheme = set_walkover(",
    "                scheme, str(params['match_id']), str(params['winner_id']))",
    "            clear_results = True",
    "            scheduled = None",
    "        elif op == 'swap':",
    "            scheme = swap_slots(",
    "                scheme,",
    "                str(params['match_id_a']), str(params.get('slot_a') or 'a'),",
    "                str(params['match_id_b']), str(params.get('slot_b') or 'a'))",
    "            clear_results = True",
    "            scheduled = None",
    "        elif op == 'replace':",
    "            scheme = replace_participant(",
    "                scheme, str(params['old_id']), str(params['new_id']))",
    "            new_pids = list(scheme.participant_ids)",
    "            clear_results = True",
    "            scheduled = None",
    "        elif op == 'move':",
    "            base = _scheduled_from_list(t, scheduled_list) if scheduled_list else []",
    "            if not base:",
    "                raise ValueError('Jadwal kosong - muat ulang lomba dulu.')",
    "            scheduled = move_match(",
    "                base,",
    "                str(params['match_id']),",
    "                str(params['new_time']),",
    "                int(params.get('new_arena') or 1),",
    "                t,",
    "            )",
    "        else:",
    "            raise ValueError(f'Aksi manual tak dikenal: {op}')",
    "        if op != 'move':",
    "            scheduled = None",
    "        rep = analyze_existing(scheme, scheduled)",
    "        return json.dumps({",
    "            'ok': True,",
    "            'op': op,",
    "            'clear_results': clear_results,",
    "            'participant_ids': new_pids,",
    "            'scheme': rep.scheme.to_dict(),",
    "            'scheduled': _scheduled_to_list(rep.scheduled),",
    "            'report': _report_dict(rep),",
    "        }, ensure_ascii=False)",
    "    except ValueError as e:",
    "        return json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False)",
  ].join("\n");

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.onload = function () {
        resolve();
      };
      s.onerror = function () {
        reject(new Error("Gagal memuat " + src));
      };
      document.head.appendChild(s);
    });
  }

  var readyPromise = null;

  async function fetchEngineFiles(py) {
    py.FS.mkdirTree("/home/pyodide/tournament");
    for (var i = 0; i < ENGINE_FILES.length; i++) {
      var name = ENGINE_FILES[i];
      var res = await fetch("_engine/tournament/" + name);
      if (!res.ok) {
        throw new Error(
          "Engine file " +
            name +
            " gagal diunduh (" +
            res.status +
            "). Jalankan: python scripts/sync_engine_to_docs.py"
        );
      }
      py.FS.writeFile("/home/pyodide/tournament/" + name, await res.text());
    }
  }

  async function initPy() {
    if (!global.loadPyodide) {
      await loadScript(PYODIDE_BASE + "pyodide.js");
    }
    var py = await global.loadPyodide({ indexURL: PYODIDE_BASE });
    await fetchEngineFiles(py);
    py.runPython(
      "import sys\nif '/home/pyodide' not in sys.path:\n    sys.path.insert(0, '/home/pyodide')\n"
    );
    py.runPython(BRIDGE);
    return py;
  }

  function ensureReady() {
    if (!readyPromise) {
      readyPromise = initPy().catch(function (e) {
        readyPromise = null;
        throw e;
      });
    }
    return readyPromise;
  }

  function parsePythonError(e) {
    var msg = e && e.message ? e.message : String(e);
    var m = msg.match(
      /ValueError:.*|RuntimeError:.*|TypeError:.*|IndexError:.*/m
    );
    if (m) return m[0];
    var lines = msg.split("\n");
    for (var i = lines.length - 1; i >= 0; i--) {
      if (lines[i].indexOf("Error") >= 0) return lines[i].trim();
    }
    return msg;
  }

  async function callJson(fn, args) {
    var py = await ensureReady();
    var names = [];
    try {
      (args || []).forEach(function (v, i) {
        var name = "__t_a" + i;
        py.globals.set(name, JSON.stringify(v));
        names.push(name);
      });
      var expr = fn + "(" + names.map(function (n) {
        return "json.loads(" + n + ")";
      }).join(", ") + ")";
      // fungsi yang butuh int/str non-json dipecah terpisah di wrapper
      var raw = py.runPython(expr);
      return JSON.parse(raw);
    } catch (e) {
      throw new Error(parsePythonError(e));
    }
  }

  // --- wrappers spesifik (campur JSON + skalar) ---

  async function callRecordScore(row, scheme, results, matchId, sa, sb) {
    var py = await ensureReady();
    try {
      py.globals.set("__t_row", JSON.stringify(row));
      py.globals.set("__t_scheme", JSON.stringify(scheme));
      py.globals.set("__t_res", JSON.stringify(results || []));
      py.globals.set("__t_mid", String(matchId));
      py.globals.set("__t_sa", int(sa));
      py.globals.set("__t_sb", int(sb));
      return JSON.parse(
        py.runPython(
          "record_score_json(json.loads(__t_row), json.loads(__t_scheme), json.loads(__t_res), __t_mid, __t_sa, __t_sb)"
        )
      );
    } catch (e) {
      throw new Error(parsePythonError(e));
    }
  }

  async function callClearScore(row, scheme, results, matchId) {
    var py = await ensureReady();
    try {
      py.globals.set("__t_row", JSON.stringify(row));
      py.globals.set("__t_scheme", JSON.stringify(scheme));
      py.globals.set("__t_res", JSON.stringify(results || []));
      py.globals.set("__t_mid", String(matchId));
      return JSON.parse(
        py.runPython(
          "clear_score_json(json.loads(__t_row), json.loads(__t_scheme), json.loads(__t_res), __t_mid)"
        )
      );
    } catch (e) {
      throw new Error(parsePythonError(e));
    }
  }

  async function callProbability(row, scheme, mode, bobot, n, seed) {
    var py = await ensureReady();
    try {
      py.globals.set("__t_row", JSON.stringify(row));
      py.globals.set("__t_scheme", JSON.stringify(scheme));
      py.globals.set("__t_mode", String(mode || "equal"));
      py.globals.set("__t_bobot", JSON.stringify(bobot || {}));
      py.globals.set("__t_n", int(n));
      if (seed === null || seed === undefined || seed === "") {
        py.globals.set("__t_seed", null);
      } else {
        py.globals.set("__t_seed", int(seed));
      }
      return JSON.parse(
        py.runPython(
          "probability_json(json.loads(__t_row), json.loads(__t_scheme), __t_mode, json.loads(__t_bobot), __t_n, __t_seed)"
        )
      );
    } catch (e) {
      throw new Error(parsePythonError(e));
    }
  }

  async function callWhatif(row, scheme, changes, numGroups) {
    var py = await ensureReady();
    try {
      py.globals.set("__t_row", JSON.stringify(row));
      py.globals.set("__t_scheme", JSON.stringify(scheme || {}));
      py.globals.set("__t_ch", JSON.stringify(changes || {}));
      if (numGroups === null || numGroups === undefined || numGroups === "") {
        py.globals.set("__t_ng", null);
      } else {
        py.globals.set("__t_ng", int(numGroups));
      }
      return JSON.parse(
        py.runPython(
          "whatif_json(json.loads(__t_row), json.loads(__t_scheme), json.loads(__t_ch), __t_ng)"
        )
      );
    } catch (e) {
      throw new Error(parsePythonError(e));
    }
  }

  async function callOptimasi(rows, maxBatches) {
    var py = await ensureReady();
    try {
      py.globals.set("__t_rows", JSON.stringify(rows || []));
      py.globals.set("__t_max", int(maxBatches));
      return JSON.parse(
        py.runPython(
          "optimasi_json(json.loads(__t_rows), __t_max)"
        )
      );
    } catch (e) {
      throw new Error(parsePythonError(e));
    }
  }

  async function callManual(op, row, scheme, scheduled, params) {
    var py = await ensureReady();
    try {
      py.globals.set("__t_op", String(op));
      py.globals.set("__t_row", JSON.stringify(row));
      py.globals.set("__t_scheme", JSON.stringify(scheme || {}));
      py.globals.set("__t_sched", JSON.stringify(scheduled || []));
      py.globals.set("__t_params", JSON.stringify(params || {}));
      return JSON.parse(
        py.runPython(
          "manual_json(__t_op, json.loads(__t_row), json.loads(__t_scheme), json.loads(__t_sched), json.loads(__t_params))"
        )
      );
    } catch (e) {
      throw new Error(parsePythonError(e));
    }
  }

  function int(v) {
    var n = parseInt(v, 10);
    if (isNaN(n)) throw new Error("Nilai bilangan bulat tidak valid: " + v);
    return n;
  }

  global.TEngine = {
    ensureReady: ensureReady,
    isReady: function () {
      return !!readyPromise;
    },
    createReport: function (row) {
      return callJson("create_report_json", [row]);
    },
    analyzeSaved: function (row, scheme, scheduled) {
      return callJson("analyze_saved_json", [row, scheme, scheduled || []]);
    },
    standings: function (row, scheme, results) {
      return callJson("standings_json", [row, scheme, results || []]);
    },
    recordScore: callRecordScore,
    clearScore: callClearScore,
    whatif: callWhatif,
    probability: callProbability,
    banding: function (rows) {
      return callJson("banding_json", [rows]);
    },
    lintas: function (rows) {
      return callJson("lintas_json", [rows]);
    },
    optimasi: callOptimasi,
    manual: callManual,
    walkover: function (row, scheme, scheduled, matchId, winnerId) {
      return callManual("walkover", row, scheme, scheduled, {
        match_id: matchId,
        winner_id: winnerId,
      });
    },
    swap: function (row, scheme, scheduled, a, sa, b, sb) {
      return callManual("swap", row, scheme, scheduled, {
        match_id_a: a,
        slot_a: sa || "a",
        match_id_b: b,
        slot_b: sb || "a",
      });
    },
    move: function (row, scheme, scheduled, matchId, newTime, newArena) {
      return callManual("move", row, scheme, scheduled, {
        match_id: matchId,
        new_time: newTime,
        new_arena: newArena,
      });
    },
    replaceParticipant: function (row, scheme, scheduled, oldId, newId) {
      return callManual("replace", row, scheme, scheduled, {
        old_id: oldId,
        new_id: newId,
      });
    },
  };
})(window);
