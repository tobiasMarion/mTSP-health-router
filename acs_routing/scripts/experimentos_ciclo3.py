"""Experimentos do relatório técnico do ciclo 3 (modo offline da GUI e da web).

Uso: python scripts/experimentos_ciclo3.py <pasta_com_datasetN.csv> <saida.json>

E1: escala e tempo; E2: prioridade manual; E3: controles de importância;
E4: número de iterações do GRASP. Usa as bases originais do ciclo 2
(commit 9e2076f), pois os CSVs versionados tiveram datas sobrescritas.
"""
import copy, csv, json, random, statistics, sys, tempfile, time
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from acs_routing.config import DEFAULT_CONFIG
from acs_routing.desktop_app import _fill_unused_capacity, _virtual_ubs, CAR_SPEED_KMH
from acs_routing.families_loader import load_families
from acs_routing.models import build_family_index
from acs_routing.reports import weekly_report
from acs_routing.reward import is_fixed_active
from acs_routing.risk import service_time
from acs_routing.travel_matrix import TravelMatrix
from acs_routing.weekly_planner import plan_week

DATA = Path(sys.argv[1])
OUT = Path(sys.argv[2])
MONDAY = date(2026, 10, 12)
SHIFT = 240
SCEN = [(100, 1), (300, 2), (600, 3), (900, 4)]


def rows_of(n):
    with open(DATA / f"dataset{n}.csv", newline="") as f:
        return list(csv.DictReader(f))


def write_tmp(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", newline="", delete=False)
    w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
    w.writeheader(); w.writerows(rows); f.close()
    return f.name


def metrics(fams, state, cfg):
    st = {f.id: service_time(f.risk_class, cfg) for f in fams}
    visited = [fid for r in state.routes for fid in r.sequence[1:-1]]
    assert len(visited) == len(set(visited)), "família repetida"
    assert all(r.total_time <= cfg.shift_minutes + 1e-6 for r in state.routes), "turno excedido"
    byid = {f.id: f for f in fams}
    for r in state.routes:
        for fid in r.sequence[1:-1]:
            f = byid[fid]
            if is_fixed_active(f, state.monday_date):
                assert r.day == f.fixed_day, "dia fixo violado"
    travel = sum(r.total_time - sum(st[i] for i in r.sequence[1:-1]) for r in state.routes)
    rep = weekly_report(fams, state, cfg)
    tot = rep["risk_family_totals"]; vis = rep["risk_family_visited"]
    return {
        "visits": len(visited),
        "cov": {k: 100 * vis.get(k, 0) / tot[k] for k in sorted(tot)},
        "ideal": rep["ideal_day_percentage"],
        "fixed_not_served": rep["active_fixed_not_served"],
        "travel_per_visit": travel / max(1, len(visited)),
        "used_time_pct": 100 * sum(r.total_time for r in state.routes) / (cfg.shift_minutes * len(state.routes)),
        "visited": set(visited),
    }


def run(rows, agents, cfg_over=None):
    cfg = replace(DEFAULT_CONFIG, agents_per_day=agents, shift_minutes=SHIFT,
                  initial_date=MONDAY, **(cfg_over or {}))
    path = write_tmp(rows)
    try:
        t0 = time.perf_counter()
        fams = load_families(path, cfg.initial_last_visit_date)
        coords = [_virtual_ubs(fams)] + [(f.lat, f.lon) for f in fams]
        matrix = TravelMatrix.from_coordinates(coords, speed_kmh=CAR_SPEED_KMH)
        idx = build_family_index(fams)
        t1 = time.perf_counter()
        state = plan_week(fams, matrix, MONDAY, cfg, idx)
        t2 = time.perf_counter()
        grasp_state = copy.deepcopy(state)
        _fill_unused_capacity(fams, state, matrix, cfg, MONDAY, idx)
        t3 = time.perf_counter()
    finally:
        Path(path).unlink()
    return {"t_prep": t1 - t0, "t_grasp": t2 - t1, "t_fill": t3 - t2, "t_total": t3 - t0,
            "grasp": metrics(fams, grasp_state, cfg), "final": metrics(fams, state, cfg),
            "fams": fams}


def strip(m):
    return {k: v for k, v in m.items() if k != "visited"}


results = {}

# E1: escala e tempo
e1 = []
for n, a in SCEN:
    rows = rows_of(n)
    reps = [run(rows, a) for _ in range(5)]
    t = [r["t_total"] for r in reps]
    e1.append({"n": n, "agents": a, "t_mean": statistics.mean(t), "t_sd": statistics.stdev(t),
               "t_grasp": statistics.mean(r["t_grasp"] for r in reps),
               "t_fill": statistics.mean(r["t_fill"] for r in reps),
               "grasp": strip(reps[0]["grasp"]), "final": strip(reps[0]["final"]),
               "deterministic": len({frozenset(r["final"]["visited"]) for r in reps}) == 1})
    print("E1", e1[-1], flush=True)
results["E1"] = e1

# E2: prioridade manual (900 famílias, 4 agentes)
rows900 = rows_of(900)
base = run(rows900, 4)
fams = {f.id: f for f in base["fams"]}
unsched = [fid for fid, f in fams.items() if fid not in base["final"]["visited"] and f.fixed_day is None]
sched_r3 = [fid for fid, f in fams.items() if fid in base["final"]["visited"] and f.risk_class == "R3" and f.fixed_day is None]
e2 = []
for label, pool, prio in [("urgente", unsched, "urgente"), ("alta", unsched, "alta"), ("baixa", sched_r3, "baixa")]:
    for s in range(5):
        sample = set(random.Random(s).sample(pool, 30))
        mod = [dict(r, manual_priority=prio) if int(r["id"]) in sample else r for r in rows900]
        res = run(mod, 4)
        byclass = {}
        for fid in sample:
            c = fams[fid].risk_class
            byclass.setdefault(c, [0, 0])
            byclass[c][1] += 1
            byclass[c][0] += fid in res["final"]["visited"]
        e2.append({"prio": label, "seed": s,
                   "in_grasp": sum(fid in res["grasp"]["visited"] for fid in sample),
                   "in_final": sum(fid in res["final"]["visited"] for fid in sample),
                   "byclass": byclass,
                   "r3_cov": res["final"]["cov"]["R3"], "visits": res["final"]["visits"]})
        print("E2", e2[-1], flush=True)
results["E2"] = e2
results["E2_pool"] = {"unsched": len(unsched), "sched_r3": len(sched_r3),
                      "unsched_by_class": {c: sum(fams[i].risk_class == c for i in unsched) for c in ("R0", "R1", "R2", "R3")}}

# E3: controles de importância (600 famílias, 3 agentes)
rows600 = rows_of(600)
e3 = []
for knob in ["risk_importance", "delay_importance", "ideal_day_importance",
             "fixed_day_importance", "travel_importance"]:
    for v in [0.0, 0.5, 1.0, 1.5, 2.0]:
        res = run(rows600, 3, {knob: v})
        e3.append({"knob": knob, "value": v, "grasp": strip(res["grasp"]), "final": strip(res["final"])})
        print("E3", knob, v, e3[-1]["grasp"], flush=True)
results["E3"] = e3

# E4: iterações do GRASP (900 famílias, 4 agentes)
e4 = []
for k in [1, 5, 10, 20, 50]:
    res = run(rows900, 4, {"n_iter": k})
    e4.append({"n_iter": k, "t_total": res["t_total"], "final": strip(res["final"]),
               "same_as_50": None})
    e4[-1]["_visited"] = sorted(res["final"]["visited"])
    print("E4", k, e4[-1]["t_total"], flush=True)
ref = e4[-1]["_visited"]
for item in e4:
    item["same_as_50"] = item.pop("_visited") == ref
results["E4"] = e4

OUT.write_text(json.dumps(results, indent=1, ensure_ascii=False))
