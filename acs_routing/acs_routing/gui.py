"""Small local Tkinter interface for multi-agent family planning."""

from __future__ import annotations

import threading
import time
import tkinter as tk
import importlib.util
import webbrowser
import csv
import tempfile
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .desktop_app import (
    _virtual_ubs,
    format_plan,
    process_csv,
    update_csv_last_visit_dates,
)
from .models import Family, WeekState
from .config import DEFAULT_CONFIG
from .state import save_state
from .family_files import (
    MANUAL_HEADERS, family_priorities, save_manual_family, set_family_priority,
    spreadsheet_rows, update_spreadsheet_dates,
)
from .families_loader import load_families


OSRM_URL = "https://router.project-osrm.org"
OSRM_PROFILE = "driving"
BG = "#f4f7f6"
SURFACE = "#ffffff"
INK = "#18332e"
MUTED = "#526761"
ACCENT = "#176b58"


def _style(root: tk.Tk) -> None:
    """Apply a small, consistent visual system using native ttk widgets."""
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(background=BG)
    style.configure("App.TFrame", background=BG)
    style.configure("Card.TFrame", background=SURFACE)
    style.configure("Card.TLabel", background=SURFACE, foreground=INK, font=("TkDefaultFont", 10))
    style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=("TkDefaultFont", 9))
    style.configure("Heading.TLabel", background=BG, foreground=INK, font=("TkDefaultFont", 18, "bold"))
    style.configure("Intro.TLabel", background=BG, foreground=MUTED, font=("TkDefaultFont", 10))
    style.configure("Section.TLabel", background=SURFACE, foreground=INK, font=("TkDefaultFont", 11, "bold"))
    style.configure("Accent.TButton", background=ACCENT, foreground="white", padding=(16, 10), font=("TkDefaultFont", 10, "bold"))
    style.map("Accent.TButton", background=[("active", "#115341"), ("disabled", "#a5b9b3")])
    style.configure("TButton", padding=(12, 7))
    style.configure("TEntry", padding=6)
    style.configure("TSpinbox", padding=5)
    style.configure("Card.TCheckbutton", background=SURFACE, foreground=INK)
    style.map("Card.TCheckbutton", background=[("active", SURFACE)])


class RoutingApp:
    """Present CSV selection, agent count, and formatted route results."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Planejamento de visitas — ACS")
        self.root.geometry("960x650")
        self.root.minsize(760, 600)
        _style(root)

        self.csv_path = tk.StringVar()
        self.agents = tk.StringVar(value="1")
        self.shift_minutes = tk.StringVar(value="360")
        self.weeks_ahead = tk.StringVar(value="0")
        self.importance = {
            key: tk.DoubleVar(value=1.0)
            for key in (
                "risk_importance", "delay_importance", "ideal_day_importance",
                "fixed_day_importance", "travel_importance",
            )
        }
        self.status = tk.StringVar(value="Selecione um arquivo ou cadastre uma família para começar.")
        self.map_path: Path | None = None
        self._families: list[Family] | None = None
        self._state: WeekState | None = None

        page = ttk.Frame(root, style="App.TFrame", padding=14)
        page.pack(fill="both", expand=True)
        ttk.Label(page, text="Planejamento de visitas", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(page, text="Organize as famílias e gere as rotas da semana.", style="Intro.TLabel").pack(anchor="w", pady=(0, 8))

        source = ttk.Frame(page, style="Card.TFrame", padding=10)
        source.pack(fill="x", pady=(0, 8))
        source.columnconfigure(0, weight=1)
        ttk.Label(source, text="1  Famílias", style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 5))
        ttk.Entry(source, textvariable=self.csv_path, state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(source, text="Escolher arquivo", command=self.choose_csv).grid(row=1, column=1, padx=(0, 8))
        ttk.Button(source, text="Cadastrar família", command=self.add_family).grid(row=1, column=2, padx=(0, 8))
        ttk.Button(source, text="Definir prioridade", command=self.edit_family_priority).grid(row=1, column=3)

        settings = ttk.Frame(page, style="Card.TFrame", padding=10)
        settings.pack(fill="x", pady=(0, 8))
        for column in range(3):
            settings.columnconfigure(column, weight=1)
        ttk.Label(settings, text="2  Como planejar", style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        inputs = (
            ("Agentes por dia", self.agents, 1, 100, 1),
            ("Minutos por agente", self.shift_minutes, 1, 1440, 30),
            ("Semanas à frente", self.weeks_ahead, 0, 520, 1),
        )
        for column, (label, variable, minimum, maximum, step) in enumerate(inputs):
            ttk.Label(settings, text=label, style="Card.TLabel").grid(row=1, column=column, sticky="w", padx=(0, 12))
            ttk.Spinbox(settings, from_=minimum, to=maximum, increment=step, textvariable=variable, width=13).grid(
                row=2, column=column, sticky="ew", padx=(0, 12), pady=(3, 0),
            )
        ttk.Button(settings, text="Ajustar prioridades gerais", command=self.open_priorities).grid(row=3, column=0, sticky="w", pady=(6, 0))

        actions = ttk.Frame(page, style="App.TFrame")
        actions.pack(fill="x", pady=(0, 6))
        self.process_button = ttk.Button(actions, text="Gerar rotas", style="Accent.TButton", command=self.start_processing)
        self.process_button.pack(side="left")
        self.map_button = ttk.Button(actions, text="Abrir mapa das rotas", command=self.open_map, state=tk.DISABLED)
        self.map_button.pack(side="left", padx=10)
        ttk.Label(page, textvariable=self.status, style="Intro.TLabel", wraplength=850).pack(anchor="w", pady=(0, 6))

        results = ttk.Frame(page, style="Card.TFrame", padding=10)
        results.pack(fill="both", expand=True)
        ttk.Label(results, text="Resultado", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self.output = ScrolledText(results, wrap=tk.WORD, font=("DejaVu Sans Mono", 10),
                                   relief="flat", borderwidth=0, background="#f8faf9",
                                   foreground=INK, padx=12, pady=10)
        self.output.pack(fill="both", expand=True)

    def open_priorities(self) -> None:
        """Explain and adjust the weights used to choose visits."""
        window = tk.Toplevel(self.root)
        window.title("Prioridades do planejamento")
        window.geometry("650x610")
        window.minsize(610, 570)
        window.configure(background=BG)
        window.transient(self.root)
        window.grab_set()
        body = ttk.Frame(window, style="App.TFrame", padding=20)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            body,
            text="O que deve pesar mais na escolha das visitas?",
            style="Heading.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            body,
            text="Arraste para a esquerda para reduzir ou desligar; para a direita para aumentar.\n"
                 "O padrão fica no meio. Os limites de tempo e dias fixos continuam sendo respeitados.",
            wraplength=570,
            style="Intro.TLabel",
        ).pack(anchor="w", pady=(5, 12))
        options = (
            ("risk_importance", "Risco da família", "Dá preferência a famílias com maior risco de saúde."),
            ("delay_importance", "Atraso da visita", "Aumenta a prioridade de visitas que já passaram do prazo."),
            ("ideal_day_importance", "Dia ideal", "Prefere agendar cada visita perto do dia recomendado."),
            ("fixed_day_importance", "Visitas com dia marcado", "Dá prioridade às famílias que precisam de um dia específico."),
            ("travel_importance", "Deslocamento curto", "Favorece visitas próximas da posição atual do agente."),
        )
        for key, title, description in options:
            section = ttk.Frame(body, style="Card.TFrame", padding=(12, 6))
            section.pack(fill="x", pady=3)
            ttk.Label(section, text=title, style="Section.TLabel").pack(anchor="w")
            ttk.Label(section, text=description, wraplength=570, style="Muted.TLabel").pack(anchor="w")
            row = ttk.Frame(section, style="Card.TFrame")
            row.pack(fill="x")
            ttk.Label(row, text="Desligado", style="Muted.TLabel").pack(side="left")
            tk.Scale(
                row, from_=0, to=2, resolution=0.25, orient="horizontal",
                variable=self.importance[key], showvalue=False, background=SURFACE,
                highlightthickness=0, troughcolor="#d9e7e2", activebackground=ACCENT,
            ).pack(side="left", fill="x", expand=True)
            ttk.Label(row, text="Mais importante", style="Muted.TLabel").pack(side="left")
        actions = ttk.Frame(body, style="App.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(
            actions, text="Restaurar padrão",
            command=lambda: [value.set(1.0) for value in self.importance.values()],
        ).pack(side="left")
        ttk.Button(actions, text="Concluído", style="Accent.TButton", command=window.destroy).pack(side="right")

    def choose_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione as famílias",
            filetypes=[("CSV ou Excel", "*.csv *.xlsx"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.csv_path.set(path)
            self.status.set(f"Selecionado: {Path(path).name}")

    def edit_family_priority(self) -> None:
        path = self.csv_path.get()
        if not path:
            messagebox.showinfo("Selecione as famílias", "Escolha um CSV ou Excel primeiro.")
            return
        try:
            current = family_priorities(path)
            if not current:
                raise ValueError("O arquivo não tem famílias cadastradas.")
        except (ValueError, OSError, KeyError) as error:
            messagebox.showerror("Não foi possível abrir as famílias", str(error))
            return
        window = tk.Toplevel(self.root)
        window.title("Prioridade de uma família")
        window.geometry("440x300")
        window.configure(background=BG)
        window.transient(self.root)
        window.grab_set()
        body = ttk.Frame(window, style="App.TFrame", padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Prioridade de uma família", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(body, text="A prioridade altera a ordem de escolha, sem mudar o risco calculado ou as regras de horário.",
                  style="Intro.TLabel", wraplength=390).pack(anchor="w", pady=(6, 18))
        ttk.Label(body, text="Número da família", style="Intro.TLabel").pack(anchor="w")
        family_id = tk.StringVar(value=str(next(iter(current))))
        ttk.Combobox(body, textvariable=family_id,
                     values=[str(item) for item in sorted(current)]).pack(fill="x", pady=(3, 12))
        ttk.Label(body, text="Prioridade", style="Intro.TLabel").pack(anchor="w")
        priority = tk.StringVar(value=current[int(family_id.get())])
        family_id.trace_add("write", lambda *_: priority.set(
            current.get(int(family_id.get()), "normal") if family_id.get().isdigit() else "normal"
        ))
        ttk.Combobox(body, textvariable=priority, values=("baixa", "normal", "alta", "urgente"),
                     state="readonly").pack(fill="x", pady=(3, 12))

        def save() -> None:
            try:
                set_family_priority(path, int(family_id.get()), priority.get())
            except (ValueError, OSError) as error:
                messagebox.showerror("Não foi possível salvar", str(error), parent=window)
                return
            self.status.set(f"Prioridade da família {family_id.get()} definida como {priority.get()}.")
            window.destroy()

        ttk.Button(body, text="Salvar prioridade", style="Accent.TButton", command=save).pack(anchor="e")

    def add_family(self) -> None:
        path = self.csv_path.get()
        if not path or Path(path).suffix.lower() != ".csv":
            path = filedialog.asksaveasfilename(
                title="Escolha um CSV para guardar os cadastros",
                defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            )
            if not path:
                return
        window = tk.Toplevel(self.root)
        window.title("Cadastrar família")
        window.geometry("700x740")
        window.minsize(650, 700)
        window.configure(background=BG)
        window.transient(self.root)
        window.grab_set()
        outer = ttk.Frame(window, style="App.TFrame", padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Cadastrar família", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Preencha os dados básicos e marque as condições presentes no domicílio.", style="Intro.TLabel").pack(anchor="w", pady=(2, 12))
        fields = {}
        labels = (
            ("id", "Número da família"), ("lat", "Latitude"), ("lon", "Longitude"),
            ("people_per_room", "Pessoas por cômodo"),
            ("last_visit_date", "Última visita (AAAA-MM-DD; opcional)"),
            ("fixed_day", "Dia fixo (1=segunda a 5=sexta; opcional)"),
            ("fixed_period_weeks", "Repetir a cada N semanas (se dia fixo)"),
            ("fixed_phase_weeks", "Fase da semana (0 para semanal)"),
        )
        grid = ttk.Frame(outer, style="Card.TFrame", padding=14)
        grid.pack(fill="x", pady=8)
        grid.columnconfigure(1, weight=1)
        for index, (key, label) in enumerate(labels):
            ttk.Label(grid, text=label, style="Card.TLabel").grid(row=index, column=0, sticky="w", pady=3)
            variable = tk.StringVar(value="0" if key == "fixed_phase_weeks" else "")
            fields[key] = variable
            ttk.Entry(grid, textvariable=variable).grid(row=index, column=1, sticky="ew", padx=8, pady=3)
        ttk.Label(grid, text="Prioridade escolhida", style="Card.TLabel").grid(row=len(labels), column=0, sticky="w", pady=3)
        fields["manual_priority"] = tk.StringVar(value="normal")
        ttk.Combobox(grid, textvariable=fields["manual_priority"],
                     values=("baixa", "normal", "alta", "urgente"), state="readonly").grid(
            row=len(labels), column=1, sticky="ew", padx=8, pady=3,
        )
        ttk.Label(outer, text="Condições de saúde e do domicílio", style="Intro.TLabel").pack(anchor="w", pady=(8, 0))
        condition_labels = {
            "bedridden": "Pessoa acamada", "physical_disability": "Deficiência física",
            "mental_disability": "Deficiência mental", "poor_sanitation": "Saneamento precário",
            "severe_malnutrition": "Desnutrição grave", "drug_addiction": "Dependência de drogas",
            "unemployment": "Desemprego", "illiteracy": "Analfabetismo",
            "under_6_months": "Criança com menos de 6 meses",
            "over_70_years": "Pessoa com mais de 70 anos",
            "hypertension": "Hipertensão", "diabetes": "Diabetes",
        }
        checks = ttk.Frame(outer, style="Card.TFrame", padding=12)
        checks.pack(fill="x", pady=8)
        for index, (key, label) in enumerate(condition_labels.items()):
            variable = tk.BooleanVar(value=False)
            fields[key] = variable
            ttk.Checkbutton(checks, text=label, variable=variable, style="Card.TCheckbutton").grid(
                row=index // 2, column=index % 2, sticky="w", padx=8, pady=3,
            )

        def save() -> None:
            row = {key: str(int(value.get())) if isinstance(value, tk.BooleanVar)
                   else value.get().strip() for key, value in fields.items()}
            if not row["fixed_day"]:
                row["fixed_period_weeks"] = ""
                row["fixed_phase_weeks"] = ""
            elif not row["fixed_period_weeks"]:
                row["fixed_period_weeks"] = "1"
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", newline="", encoding="utf-8") as temp:
                    writer = csv.DictWriter(temp, fieldnames=MANUAL_HEADERS)
                    writer.writeheader()
                    writer.writerow(row)
                    temp.flush()
                    load_families(temp.name)
                save_manual_family(path, row)
            except (ValueError, OSError) as error:
                messagebox.showerror("Revise o cadastro", str(error), parent=window)
                return
            self.csv_path.set(path)
            self.status.set(f"Família {row['id']} cadastrada em {Path(path).name}.")
            window.destroy()

        ttk.Button(outer, text="Salvar família", style="Accent.TButton", command=save).pack(fill="x", pady=10)

    def start_processing(self) -> None:
        path = self.csv_path.get()
        if not path:
            messagebox.showwarning("Famílias obrigatórias", "Selecione um arquivo ou cadastre uma família.")
            return
        try:
            agents = int(self.agents.get())
            shift_minutes = int(self.shift_minutes.get())
            weeks_ahead = int(self.weeks_ahead.get())
            if agents <= 0 or weeks_ahead < 0:
                raise ValueError
            if shift_minutes <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Valor inválido",
                "Informe agentes e tempo ativo maiores que zero, "
                "e semanas de simulação maiores ou iguais a zero.",
            )
            return
        self.process_button.configure(state=tk.DISABLED)
        self.status.set("Processando famílias e calculando rotas...")
        self.output.delete("1.0", tk.END)
        self.map_path = None
        self._families = None
        self._state = None
        self.map_button.configure(state=tk.DISABLED)
        threading.Thread(
            target=self._process,
            args=(path, agents, shift_minutes, weeks_ahead,
                  {key: value.get() for key, value in self.importance.items()}),
            daemon=True,
        ).start()

    def _process(
        self,
        path: str,
        agents: int,
        shift_minutes: int,
        weeks_ahead: int,
        importance: dict[str, float],
    ) -> None:
        try:
            solver_started_at = time.perf_counter()
            if Path(path).suffix.lower() == ".xlsx":
                headers, rows = spreadsheet_rows(path)
                with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", newline="", encoding="utf-8") as temp:
                    writer = csv.DictWriter(temp, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(rows)
                    temp.flush()
                    families, state = process_csv(
                        temp.name, agents, shift_minutes, weeks_ahead=weeks_ahead,
                        config=replace(DEFAULT_CONFIG, **importance),
                    )
                update_spreadsheet_dates(path, state)
            else:
                families, state = process_csv(
                    path, agents, shift_minutes, weeks_ahead=weeks_ahead,
                    config=replace(DEFAULT_CONFIG, **importance),
                )
                update_csv_last_visit_dates(path, state)
            solver_seconds = time.perf_counter() - solver_started_at
            result = format_plan(
                families,
                state,
                agents,
                execution_seconds=solver_seconds,
            )
        except Exception as error:  # surfaced in the UI with the original message
            self.root.after(0, self._show_error, str(error))
            return
        self.root.after(0, self._show_result, result, families, state)

    def _show_result(
        self, result: str, families: list[Family], state: WeekState
    ) -> None:
        self.output.insert("1.0", result)
        self._families = families
        self._state = state
        self.status.set("Rotas geradas com sucesso.")
        self.process_button.configure(state=tk.NORMAL)
        self.map_button.configure(state=tk.NORMAL)

    def _render_map(self, families: list[Family], state: WeekState) -> Path:
        """Render the plan with real road geometries from OSRM."""
        output_dir = Path.home() / ".acs-routing" / "gui"
        output_dir.mkdir(parents=True, exist_ok=True)
        state_path = output_dir / "state.json"
        map_path = output_dir / "routes.html"
        save_state(state, state_path)
        renderer_path = Path(__file__).resolve().parents[1] / "scripts" / "render_routes_map.py"
        spec = importlib.util.spec_from_file_location("acs_route_map_renderer", renderer_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"não foi possível carregar o renderizador: {renderer_path}")
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        family_coordinates = {
            family.id: (family.lat, family.lon) for family in families
        }
        routes = [
            {
                "day": route.day,
                "agent": route.agent,
                "sequence": route.sequence,
            }
            for route in state.routes
        ]
        document = renderer.render_map_html(
            family_coordinates,
            routes,
            _virtual_ubs(families),
            osrm_url=OSRM_URL,
            osrm_profile=OSRM_PROFILE,
        )
        map_path.write_text(document, encoding="utf-8")
        return map_path

    def open_map(self) -> None:
        """Render with OSRM and open the latest plan in the default browser."""
        if self._families is None or self._state is None:
            return
        self.map_button.configure(state=tk.DISABLED)
        self.status.set("Consultando o OSRM e desenhando as rotas reais...")
        threading.Thread(target=self._generate_map, daemon=True).start()

    def _generate_map(self) -> None:
        if self._families is None or self._state is None:
            return
        try:
            self.map_path = self._render_map(self._families, self._state)
        except Exception as error:
            self.root.after(0, self._show_map_error, str(error))
            return
        self.root.after(0, self._open_rendered_map)

    def _open_rendered_map(self) -> None:
        if self.map_path is None:
            return
        self.status.set("Mapa com rotas reais do OSRM gerado.")
        self.map_button.configure(state=tk.NORMAL)
        webbrowser.open(self.map_path.resolve().as_uri())

    def _show_map_error(self, message: str) -> None:
        self.status.set("Rotas geradas; mapa aguardando o OSRM.")
        self.map_button.configure(state=tk.NORMAL)
        messagebox.showerror(
            "OSRM indisponível",
            "Não foi possível obter as rotas reais do OSRM.\n\n"
            f"{message}\n\n"
            "Verifique sua conexão com a internet e tente abrir o mapa novamente.",
        )

    def _show_error(self, message: str) -> None:
        self.status.set("Não foi possível gerar as rotas.")
        self.process_button.configure(state=tk.NORMAL)
        messagebox.showerror("Erro no processamento", message)


def main() -> None:
    """Start the local desktop application."""
    root = tk.Tk()
    RoutingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
