import csv
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

from acs_routing.family_files import (
    MANUAL_HEADERS, save_manual_family, set_family_priority,
    spreadsheet_rows, update_spreadsheet_dates,
)
from acs_routing.families_loader import load_families
from acs_routing.models import Route, WeekState
from acs_routing.reward import family_reward


class FamilyFilesTest(unittest.TestCase):
    def test_manual_file_is_reusable_and_rejects_duplicate_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "families.csv"
            row = {name: "0" for name in MANUAL_HEADERS}
            row.update(id="1", lat="-30.02", lon="-51.06", people_per_room="1")
            row["manual_priority"] = "normal"
            row["fixed_day"] = row["fixed_period_weeks"] = row["fixed_phase_weeks"] = ""
            row["last_visit_date"] = ""
            save_manual_family(path, row)
            self.assertEqual(load_families(path)[0].id, 1)
            with self.assertRaisesRegex(ValueError, "ID"):
                save_manual_family(path, row)
            set_family_priority(path, 1, "urgente")
            family = load_families(path)[0]
            self.assertEqual(family.manual_priority, "urgente")
            self.assertGreater(
                family_reward(family, 1, date(2026, 11, 9)),
                family_reward(replace(family, manual_priority="normal"), 1, date(2026, 11, 9)),
            )

    def test_manual_family_can_join_existing_csv_with_room_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "families.csv"
            headers = [name for name in MANUAL_HEADERS if name != "people_per_room"]
            headers.extend(["people_per_room_gt_1", "people_per_room_eq_1"])
            with path.open("w", newline="", encoding="utf-8") as file:
                csv.DictWriter(file, fieldnames=headers).writeheader()
            row = {name: "0" for name in MANUAL_HEADERS}
            row.update(id="2", lat="-30.02", lon="-51.06", people_per_room="2")
            row["manual_priority"] = "normal"
            row["fixed_day"] = row["fixed_period_weeks"] = row["fixed_phase_weeks"] = ""
            row["last_visit_date"] = ""
            save_manual_family(path, row)
            self.assertEqual(load_families(path)[0].id, 2)

    def test_excel_dates_and_visit_updates(self):
        from openpyxl import Workbook, load_workbook

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "families.xlsx"
            workbook = Workbook()
            workbook.active.append(["id", "last_visit_date"])
            workbook.active.append([1, datetime(2026, 1, 1)])
            workbook.save(path)
            headers, rows = spreadsheet_rows(path)
            self.assertEqual(headers, ["id", "last_visit_date"])
            self.assertEqual(rows[0]["last_visit_date"], "2026-01-01")
            state = WeekState([], [Route([0, 1, 0], day=2)], date(2026, 11, 9))
            update_spreadsheet_dates(path, state)
            self.assertEqual(load_workbook(path).active["B2"].value, "2026-11-10")
            set_family_priority(path, 1, "alta")
            self.assertEqual(load_workbook(path).active["C2"].value, "alta")
