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
]


def save_manual_family(path: str | Path, row: dict[str, str]) -> None:
    path = Path(path)
    exists = path.exists()
    if exists:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames or [])
            records = list(reader)
        required = set(MANUAL_HEADERS) - {"people_per_room", "last_visit_date"}
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
