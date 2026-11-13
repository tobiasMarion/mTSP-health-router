"""Spreadsheet import and date updates for the desktop interface."""

import csv
from datetime import date, datetime
from datetime import timedelta
from pathlib import Path

from .models import WeekState


def _openpyxl():
    try:
        import openpyxl
    except ImportError as error:
        raise RuntimeError("Para usar planilhas Excel, instale: pip install -e '.[gui]'") from error
    return openpyxl


def spreadsheet_rows(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    workbook = _openpyxl().load_workbook(path, read_only=True, data_only=True)
    try:
        rows = workbook.active.iter_rows(values_only=True)
        headers = [str(value).strip() if value is not None else "" for value in next(rows)]
        if not headers or len(set(headers)) != len(headers):
            raise ValueError("A planilha precisa ter cabeçalhos únicos na primeira linha.")
        records = [
            {header: value.date().isoformat() if isinstance(value, datetime)
             else value.isoformat() if isinstance(value, date)
             else str(value) if value is not None else ""
             for header, value in zip(headers, row)}
            for row in rows if any(value is not None for value in row)
        ]
        return headers, records
    finally:
        workbook.close()


def update_spreadsheet_dates(path: str | Path, state: WeekState) -> None:
    workbook = _openpyxl().load_workbook(path)
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    if "id" not in headers:
        raise ValueError("A planilha precisa da coluna id.")
    if "last_visit_date" not in headers:
        headers.append("last_visit_date")
        sheet.cell(1, len(headers), "last_visit_date")
    id_column = headers.index("id") + 1
    date_column = headers.index("last_visit_date") + 1
    visits = {
        family_id: (state.monday_date + timedelta(days=route.day - 1)).isoformat()
        for route in state.routes for family_id in route.sequence[1:-1]
    }
    for row in range(2, sheet.max_row + 1):
        value = sheet.cell(row, id_column).value
        if value is not None and int(value) in visits:
            sheet.cell(row, date_column, visits[int(value)])
    workbook.save(path)


MANUAL_HEADERS = [
    "id", "lat", "lon", "bedridden", "physical_disability", "mental_disability",
    "poor_sanitation", "severe_malnutrition", "drug_addiction", "unemployment",
    "illiteracy", "under_6_months", "over_70_years", "hypertension", "diabetes",
    "people_per_room", "fixed_day", "fixed_period_weeks", "fixed_phase_weeks",
    "last_visit_date",
    "manual_priority",
]


def family_priorities(path: str | Path) -> dict[int, str]:
    """List IDs and current manual priorities for the selection dialog."""
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        _, rows = spreadsheet_rows(path)
    else:
        with path.open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
    return {int(row["id"]): row.get("manual_priority") or "normal" for row in rows}


def set_family_priority(path: str | Path, family_id: int, priority: str) -> None:
    """Persist one family's priority in its CSV or Excel source."""
    from .families_loader import MANUAL_PRIORITY_WEIGHTS

    if priority not in MANUAL_PRIORITY_WEIGHTS:
        raise ValueError("Prioridade inválida.")
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        workbook = _openpyxl().load_workbook(path)
        sheet = workbook.active
        headers = [cell.value for cell in sheet[1]]
        if "id" not in headers:
            raise ValueError("A planilha precisa da coluna id.")
        id_column = headers.index("id") + 1
        matches = [row for row in range(2, sheet.max_row + 1)
                   if sheet.cell(row, id_column).value is not None
                   and int(sheet.cell(row, id_column).value) == family_id]
        if len(matches) != 1:
            raise ValueError("Família não encontrada ou ID repetido.")
        if "manual_priority" not in headers:
            headers.append("manual_priority")
            sheet.cell(1, len(headers), "manual_priority")
        sheet.cell(matches[0], headers.index("manual_priority") + 1, priority)
        workbook.save(path)
    else:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames or [])
            rows = list(reader)
        matches = [row for row in rows if int(row["id"]) == family_id]
        if len(matches) != 1:
            raise ValueError("Família não encontrada ou ID repetido.")
        if "manual_priority" not in headers:
            headers.append("manual_priority")
        matches[0]["manual_priority"] = priority
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)


def save_manual_family(path: str | Path, row: dict[str, str]) -> None:
    path = Path(path)
    exists = path.exists()
    if exists:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames or [])
            records = list(reader)
        required = set(MANUAL_HEADERS) - {"people_per_room", "last_visit_date", "manual_priority"}
        required -= {"fixed_day", "fixed_period_weeks", "fixed_phase_weeks"}
        if not required <= set(headers) or not (
            "people_per_room" in headers or
            {"people_per_room_gt_1", "people_per_room_eq_1"} <= set(headers)
        ):
            raise ValueError("O CSV selecionado não tem as colunas necessárias para o cadastro.")
        if any(item["id"] == row["id"] for item in records):
            raise ValueError("Já existe uma família com esse ID.")
        if "last_visit_date" not in headers:
            headers.append("last_visit_date")
        if "manual_priority" not in headers:
            headers.append("manual_priority")
        for name in ("fixed_day", "fixed_period_weeks", "fixed_phase_weeks"):
            if name not in headers and row.get(name):
                headers.append(name)
        if "people_per_room_gt_1" in headers:
            row["people_per_room_gt_1"] = str(int(float(row["people_per_room"]) > 1))
            row["people_per_room_eq_1"] = str(int(float(row["people_per_room"]) == 1))
        if headers != list(reader.fieldnames or []):
            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(records)
    else:
        headers = MANUAL_HEADERS
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        if not exists:
            writer.writeheader()
        writer.writerow({header: row.get(header, "") for header in headers})
