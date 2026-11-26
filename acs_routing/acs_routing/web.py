"""Small browser interface for the existing weekly planner.

Run with ``python -m acs_routing.web``. Production deployments should use a
WSGI server and set ACS_WEB_PASSWORD and ACS_WEB_SECRET_KEY.
"""

from __future__ import annotations

import csv
import contextlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (
    Flask, abort, flash, g, redirect, render_template, request, Response,
    session, url_for,
)

from .config import DEFAULT_CONFIG
from .desktop_app import process_csv
from .families_loader import load_families
from .family_files import spreadsheet_rows
from .reports import weekly_report


SENTINEL_LABELS = {
    "bedridden": "Acamado", "physical_disability": "Deficiência física",
    "mental_disability": "Deficiência mental", "poor_sanitation": "Saneamento precário",
    "severe_malnutrition": "Desnutrição grave", "drug_addiction": "Drogadição",
    "unemployment": "Desemprego", "illiteracy": "Analfabetismo",
    "under_6_months": "Menor de 6 meses", "over_70_years": "Maior de 70 anos",
    "hypertension": "Hipertensão", "diabetes": "Diabetes",
}
WEEKDAYS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta")


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _init_db(path: Path) -> None:
    with contextlib.closing(_connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS families (
                id INTEGER PRIMARY KEY, data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, microarea TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monday TEXT NOT NULL, created_at TEXT NOT NULL,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS completed_visits (
                plan_id INTEGER NOT NULL REFERENCES plans(id),
                family_id INTEGER NOT NULL,
                visit_date TEXT NOT NULL,
                PRIMARY KEY (plan_id, family_id)
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
        """)
        db.execute("INSERT OR IGNORE INTO metadata VALUES ('dataset_id', ?)", (secrets.token_hex(16),))
        if not db.execute("SELECT 1 FROM agents LIMIT 1").fetchone():
            db.execute("INSERT INTO agents (name) VALUES (?)", ("Agente 1",))


def _rows(db: sqlite3.Connection) -> list[dict[str, str]]:
    return [json.loads(row["data"]) for row in db.execute("SELECT data FROM families ORDER BY id")]


def _csv_file(rows: list[dict[str, str]]) -> str:
    """Write planner input in a temporary CSV and return its filename."""
    headers = list(dict.fromkeys(key for row in rows for key in row))
    file = tempfile.NamedTemporaryFile("w", suffix=".csv", encoding="utf-8", newline="", delete=False)
    try:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        file.close()
    return file.name


def _validate(rows: list[dict[str, str]]) -> list:
    if not rows:
        raise ValueError("Informe ao menos uma família.")
    filename = _csv_file(rows)
    try:
        return load_families(filename, DEFAULT_CONFIG.initial_last_visit_date)
    finally:
        Path(filename).unlink(missing_ok=True)


def _family_view(rows: list[dict[str, str]]) -> list[dict]:
    families = _validate(rows) if rows else []
    by_id = {family.id: family for family in families}
    return [
        {
            "id": int(row["id"]),
            "name": row.get("name") or f"Família {row['id']}",
            "address": row.get("address") or f"{row['lat']}, {row['lon']}",
            "microarea": row.get("microarea") or "—",
            "priority": row.get("manual_priority") or "normal",
            "risk": by_id[int(row["id"])].risk_class,
            "lat": float(row["lat"]), "lon": float(row["lon"]),
        }
        for row in rows
    ]


def _plan(db: sqlite3.Connection, plan_id: int | None = None) -> tuple[sqlite3.Row | None, dict | None]:
    if plan_id is None:
        row = db.execute("SELECT * FROM plans ORDER BY id DESC LIMIT 1").fetchone()
    else:
        row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return (row, json.loads(row["data"])) if row else (None, None)


def create_app(database_path: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("ACS_WEB_SECRET_KEY") or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    )
    database = Path(database_path or os.environ.get("ACS_WEB_DATABASE")
                    or Path(app.instance_path) / "acs_web.sqlite3")
    database.parent.mkdir(parents=True, exist_ok=True)
    _init_db(database)
    password = os.environ.get("ACS_WEB_PASSWORD", "")

    @app.before_request
    def before_request() -> Response | None:
        g.db = _connect(database)
        if password and request.endpoint not in {"login", "static"} and not session.get("authenticated"):
            return redirect(url_for("login"))
        if request.method == "POST":
            sent = request.form.get("csrf_token", "")
            expected = session.get("csrf_token", "")
            if not expected or not hmac.compare_digest(sent, expected):
                abort(400, "Formulário expirado. Recarregue a página.")
        return None

    @app.teardown_request
    def teardown_request(_error: BaseException | None) -> None:
        db = getattr(g, "db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def context() -> dict:
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["csrf_token"], "weekdays": WEEKDAYS,
                "has_password": bool(password)}

    @app.get("/login")
    @app.post("/login")
    def login() -> Response | str:
        if not password:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            if hmac.compare_digest(request.form.get("password", ""), password):
                session.clear()
                session["authenticated"] = True
                return redirect(url_for("dashboard"))
            flash("Senha incorreta.", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout() -> Response:
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    def dashboard() -> str:
        db = g.db
        plan_row, plan = _plan(db)
        total = db.execute("SELECT COUNT(*) FROM families").fetchone()[0]
        active = db.execute("SELECT COUNT(*) FROM agents WHERE active = 1").fetchone()[0]
        completed = 0
        if plan_row:
            completed = db.execute(
                "SELECT COUNT(*) FROM completed_visits WHERE plan_id = ?", (plan_row["id"],)
            ).fetchone()[0]
        return render_template("dashboard.html", plan_row=plan_row, plan=plan,
                               family_count=total, agent_count=active, completed=completed)

    @app.get("/novo")
    def new_plan() -> str:
        rows = _rows(g.db)
        agents = g.db.execute("SELECT * FROM agents ORDER BY id").fetchall()
        return render_template("new_plan.html", families=_family_view(rows), agents=agents,
                               today=date.today().isoformat(), sentinels=SENTINEL_LABELS,
                               geocoder_url=os.environ.get("ACS_GEOCODER_URL", "https://nominatim.openstreetmap.org/search"))

    @app.post("/novo/iniciar")
    def start_new_plan() -> Response:
        with g.db:
            g.db.execute("DELETE FROM families")
            g.db.execute("UPDATE metadata SET value = ? WHERE key = 'dataset_id'",
                         (secrets.token_hex(16),))
        return redirect(url_for("new_plan"))

    @app.post("/familias/importar")
    def import_families() -> Response:
        upload = request.files.get("file")
        if not upload or not upload.filename:
            flash("Selecione um CSV ou XLSX.", "error")
            return redirect(url_for("new_plan"))
        suffix = Path(upload.filename).suffix.lower()
        try:
            if suffix == ".csv":
                content = upload.read().decode("utf-8-sig")
                rows = list(csv.DictReader(io.StringIO(content)))
            elif suffix == ".xlsx":
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as file:
                    file.write(upload.read())
                    filename = file.name
                try:
                    _, rows = spreadsheet_rows(filename)
                finally:
                    Path(filename).unlink(missing_ok=True)
            else:
                raise ValueError("Use um arquivo .csv ou .xlsx.")
            _validate(rows)
            with g.db:
                g.db.execute("DELETE FROM families")
                g.db.execute("UPDATE metadata SET value = ? WHERE key = 'dataset_id'",
                             (secrets.token_hex(16),))
                g.db.executemany(
                    "INSERT INTO families (id, data) VALUES (?, ?)",
                    [(int(row["id"]), json.dumps(row, ensure_ascii=False)) for row in rows],
                )
            flash(f"{len(rows)} famílias importadas.", "success")
        except (UnicodeError, ValueError, OSError, KeyError) as error:
            flash(f"Não foi possível importar: {error}", "error")
        return redirect(url_for("new_plan"))

    @app.post("/familias/adicionar")
    def add_family() -> Response:
        rows = _rows(g.db)
        new_id = max((int(row["id"]) for row in rows), default=0) + 1
        row = {key: "0" for key in SENTINEL_LABELS}
        row.update({key: request.form.get(key, "").strip() for key in (
            "lat", "lon", "name", "address", "microarea", "people_per_room", "last_visit_date",
        )})
        row.update({"id": str(new_id), "manual_priority": "normal"})
        for key in SENTINEL_LABELS:
            row[key] = "1" if request.form.get(key) == "1" else "0"
        if not row["people_per_room"]:
            row["people_per_room"] = "0"
        try:
            _validate(rows + [row])
            with g.db:
                g.db.execute("INSERT INTO families (id, data) VALUES (?, ?)",
                             (new_id, json.dumps(row, ensure_ascii=False)))
            flash(f"Família {new_id} cadastrada.", "success")
        except ValueError as error:
            flash(f"Revise o cadastro: {error}", "error")
        return redirect(url_for("new_plan"))

    @app.post("/familias/<int:family_id>/prioridade")
    def set_priority(family_id: int) -> Response:
        priority = request.form.get("priority", "")
        if priority not in {"baixa", "normal", "alta", "urgente"}:
            abort(400)
        row = g.db.execute("SELECT data FROM families WHERE id = ?", (family_id,)).fetchone()
        if not row:
            abort(404)
        data = json.loads(row["data"])
        data["manual_priority"] = priority
        with g.db:
            g.db.execute("UPDATE families SET data = ? WHERE id = ?",
                         (json.dumps(data, ensure_ascii=False), family_id))
        flash(f"Prioridade da família {family_id} atualizada.", "success")
        return redirect(url_for("new_plan"))

    @app.post("/agentes/adicionar")
    def add_agent() -> Response:
        name = request.form.get("name", "").strip()
        microarea = request.form.get("microarea", "").strip()
        if not name:
            flash("Informe o nome do agente.", "error")
        else:
            with g.db:
                g.db.execute("INSERT INTO agents (name, microarea) VALUES (?, ?)", (name, microarea))
            flash("Agente cadastrado.", "success")
        return redirect(url_for("new_plan"))

    @app.post("/agentes/<int:agent_id>/alternar")
    def toggle_agent(agent_id: int) -> Response:
        with g.db:
            changed = g.db.execute("UPDATE agents SET active = 1 - active WHERE id = ?", (agent_id,))
        if not changed.rowcount:
            abort(404)
        return redirect(url_for("new_plan"))

    @app.post("/planos")
    def generate_plan() -> Response:
        rows = _rows(g.db)
        agents = g.db.execute("SELECT * FROM agents WHERE active = 1 ORDER BY id").fetchall()
        try:
            if not agents:
                raise ValueError("Ative ao menos um agente.")
            if not rows:
                raise ValueError("Importe ou cadastre famílias antes de planejar.")
            shift = int(request.form.get("shift_minutes", "360"))
            if not 1 <= shift <= 1440:
                raise ValueError("O tempo em campo deve estar entre 1 e 1440 minutos.")
            selected_date = date.fromisoformat(request.form.get("planning_date", ""))
            config = replace(DEFAULT_CONFIG, initial_date=selected_date)
            filename = _csv_file(rows)
            try:
                families, state = process_csv(filename, len(agents), shift, config=config)
            finally:
                Path(filename).unlink(missing_ok=True)
            report = weekly_report(families, state, replace(config, agents_per_day=len(agents),
                                                           shift_minutes=shift))
            payload = {
                "monday": state.monday_date.isoformat(),
                "families": _family_view(rows),
                "agents": [{"name": a["name"], "microarea": a["microarea"]} for a in agents],
                "routes": [
                    {**asdict(route), "visit_date": (
                        state.monday_date + timedelta(days=route.day - 1)
                    ).isoformat()}
                    for route in state.routes
                ],
                "report": report,
                "shift_minutes": shift,
                "dataset_id": g.db.execute(
                    "SELECT value FROM metadata WHERE key = 'dataset_id'"
                ).fetchone()[0],
            }
            with g.db:
                cursor = g.db.execute(
                    "INSERT INTO plans (monday, created_at, data) VALUES (?, ?, ?)",
                    (payload["monday"], datetime.now().isoformat(timespec="seconds"),
                     json.dumps(payload, ensure_ascii=False)),
                )
            flash("Planejamento gerado. As visitas ainda não foram marcadas como realizadas.", "success")
            return redirect(url_for("agent_plans", plan_id=cursor.lastrowid))
        except (ValueError, OSError) as error:
            flash(f"Não foi possível gerar o plano: {error}", "error")
            return redirect(url_for("new_plan"))

    @app.get("/planos")
    @app.get("/planos/<int:plan_id>")
    def agent_plans(plan_id: int | None = None) -> str:
        row, plan = _plan(g.db, plan_id)
        if plan_id is not None and row is None:
            abort(404)
        history = g.db.execute("SELECT id, monday, created_at FROM plans ORDER BY id DESC LIMIT 20").fetchall()
        completed = {}
        if row:
            completed = {item["family_id"]: item["visit_date"] for item in g.db.execute(
                "SELECT family_id, visit_date FROM completed_visits WHERE plan_id = ?", (row["id"],)
            )}
        families_by_id = {family["id"]: family for family in plan["families"]} if plan else {}
        has_coordinates = bool(plan and plan["families"] and all(
            "lat" in family and "lon" in family for family in plan["families"]
        ))
        return render_template("agent_plans.html", plan_row=row, plan=plan,
                               history=history, completed=completed,
                               families_by_id=families_by_id, has_coordinates=has_coordinates,
                               osrm_url=os.environ.get("ACS_MAP_OSRM_URL", "https://router.project-osrm.org"))

    @app.post("/planos/<int:plan_id>/visitas/<int:family_id>")
    def complete_visit(plan_id: int, family_id: int) -> Response:
        row, plan = _plan(g.db, plan_id)
        if row is None or not any(family_id in route["sequence"][1:-1] for route in plan["routes"]):
            abort(404)
        try:
            visit_date = date.fromisoformat(request.form.get("visit_date", ""))
        except ValueError:
            abort(400, "Data da visita inválida.")
        if visit_date > date.today():
            abort(400, "Uma visita futura não pode ser registrada como realizada.")
        if g.db.execute("SELECT 1 FROM completed_visits WHERE plan_id = ? AND family_id = ?",
                        (plan_id, family_id)).fetchone():
            flash("Esta visita já foi registrada.", "error")
            return redirect(url_for("agent_plans", plan_id=plan_id))
        with g.db:
            g.db.execute("INSERT INTO completed_visits VALUES (?, ?, ?)",
                         (plan_id, family_id, visit_date.isoformat()))
            family = g.db.execute("SELECT data FROM families WHERE id = ?", (family_id,)).fetchone()
            current_dataset = g.db.execute(
                "SELECT value FROM metadata WHERE key = 'dataset_id'"
            ).fetchone()[0]
            if family and plan.get("dataset_id") == current_dataset:
                data = json.loads(family["data"])
                previous = data.get("last_visit_date")
                if not previous or visit_date >= date.fromisoformat(previous):
                    data["last_visit_date"] = visit_date.isoformat()
                    g.db.execute("UPDATE families SET data = ? WHERE id = ?",
                                 (json.dumps(data, ensure_ascii=False), family_id))
        flash(f"Visita à família {family_id} registrada.", "success")
        return redirect(url_for("agent_plans", plan_id=plan_id))

    @app.get("/planos/<int:plan_id>/csv")
    def download_plan(plan_id: int) -> Response:
        row, plan = _plan(g.db, plan_id)
        if row is None:
            abort(404)
        families = {item["id"]: item for item in plan["families"]}
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(("agente", "dia", "ordem", "familia_id", "responsavel", "endereco",
                         "microarea", "risco", "prioridade"))
        for route in plan["routes"]:
            agent = plan["agents"][route["agent"] - 1]
            for index, family_id in enumerate(route["sequence"][1:-1], 1):
                family = families[family_id]
                writer.writerow((agent["name"], WEEKDAYS[route["day"] - 1], index,
                                 family_id, family["name"], family["address"],
                                 family["microarea"], family["risk"], family["priority"]))
        return Response("\ufeff" + output.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=plano-{plan_id}.csv"})

    @app.get("/planos/<int:plan_id>/mapa")
    def route_map(plan_id: int) -> str:
        row, plan = _plan(g.db, plan_id)
        if row is None:
            abort(404)
        if any("lat" not in family or "lon" not in family for family in plan["families"]):
            return render_template("map.html", plan_row=row, plan=None)
        return render_template("map.html", plan_row=row, plan=plan)

    @app.get("/planos/<int:plan_id>/rotas/<int:agent>/<int:day>.gpx")
    def download_gpx(plan_id: int, agent: int, day: int) -> Response:
        row, plan = _plan(g.db, plan_id)
        if row is None:
            abort(404)
        route = next((r for r in plan["routes"] if r["agent"] == agent and r["day"] == day), None)
        if route is None:
            abort(404)
        families = {item["id"]: item for item in plan["families"]}
        if any("lat" not in f or "lon" not in f for f in families.values()):
            abort(409, "Este plano antigo não contém coordenadas; gere um novo planejamento.")
        root = ET.Element("gpx", {"version": "1.1", "creator": "ACS Routing", "xmlns": "http://www.topografix.com/GPX/1/1"})
        rte = ET.SubElement(root, "rte")
        ET.SubElement(rte, "name").text = f"Agente {agent} - {WEEKDAYS[day - 1]}"
        ET.SubElement(rte, "desc").text = "Pontos de visita em ordem; percurso aproximado por linhas retas."
        lat = sum(f["lat"] for f in families.values()) / len(families)
        lon = sum(f["lon"] for f in families.values()) / len(families)
        for family_id in route["sequence"]:
            f = families.get(family_id)
            point = ET.SubElement(rte, "rtept", {"lat": str(f["lat"] if f else lat), "lon": str(f["lon"] if f else lon)})
            ET.SubElement(point, "name").text = f"Família {family_id}" if f else "Ponto de partida aproximado"
        return Response(ET.tostring(root, encoding="utf-8", xml_declaration=True), mimetype="application/gpx+xml",
                        headers={"Content-Disposition": f"attachment; filename=plano-{plan_id}-agente-{agent}-dia-{day}.gpx"})

    @app.get("/ajuda")
    def help_page() -> str:
        return render_template("help.html")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8000)
