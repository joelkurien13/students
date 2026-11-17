"""Load and save student records in students.json.

Initial demonstration records are created when the file is missing.
Corrupt data is reported and left on disk so a later save cannot wipe
it by accident.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from calculations import SUBJECTS

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "students.json"


class DataSaveError(Exception):
    """Raised when saving would risk overwriting unreadable data."""


def _reject_json_constant(value: str):
    raise ValueError(f"{value} is not a valid JSON number.")


def _marks(maths, physics, chemistry, computer, english) -> dict:
    return {
        "Mathematics": maths,
        "Physics": physics,
        "Chemistry": chemistry,
        "Computer Science": computer,
        "English": english,
    }


def _test(name: str, test_date: str, marks: dict) -> dict:
    return {"test_name": name, "test_date": test_date, "marks": marks}


def _student(roll_no: str, name: str, tests: list[dict]) -> dict:
    return {
        "roll_no": roll_no,
        "name": name,
        "marks": dict(tests[-1]["marks"]),
        "tests": tests,
    }


def initial_students() -> list[dict]:
    """Return the initial demonstration records for a new installation."""
    return [
        _student(
            "S101",
            "Student 101",
            [
                _test("Unit Test 1", "2026-07-18", _marks(82, 80, 84, 88, 78)),
                _test("Mid Term", "2026-09-12", _marks(90, 88, 89, 94, 86)),
                _test("Final Term", "2026-11-08", _marks(95, 92, 94, 98, 90)),
            ],
        ),
        _student(
            "S102",
            "Student 102",
            [
                _test("Unit Test 1", "2026-07-18", _marks(74, 76, 78, 80, 72)),
                _test("Final Term", "2026-11-08", _marks(85, 82, 88, 84, 80)),
            ],
        ),
        _student(
            "S103",
            "Student 103",
            [
                _test("Unit Test 1", "2026-07-18", _marks(68, 66, 70, 74, 65)),
                _test("Final Term", "2026-11-08", _marks(76, 72, 74, 80, 70)),
            ],
        ),
        _student(
            "S104",
            "Student 104",
            [
                _test("Unit Test 1", "2026-07-18", _marks(58, 60, 55, 64, 59)),
                _test("Final Term", "2026-11-08", _marks(65, 68, 62, 70, 64)),
            ],
        ),
        _student(
            "S105",
            "Student 105",
            [
                _test("Unit Test 1", "2026-07-18", _marks(48, 50, 46, 55, 49)),
                _test("Final Term", "2026-11-08", _marks(55, 58, 52, 60, 54)),
            ],
        ),
        _student(
            "S106",
            "Student 106",
            [
                _test("Unit Test 1", "2026-07-18", _marks(36, 40, 38, 44, 41)),
                _test("Final Term", "2026-11-08", _marks(42, 45, 40, 48, 44)),
            ],
        ),
        _student(
            "S107",
            "Student 107",
            [
                _test("Unit Test 1", "2026-07-18", _marks(44, 42, 40, 46, 43)),
                _test("Final Term", "2026-11-08", _marks(48, 46, 44, 50, 47)),
            ],
        ),
        _student(
            "S108",
            "Student 108",
            [
                _test("Unit Test 1", "2026-07-18", _marks(30, 38, 28, 48, 36)),
                _test("Final Term", "2026-11-08", _marks(38, 42, 35, 55, 40)),
            ],
        ),
        _student(
            "S109",
            "Student 109",
            [
                _test("Unit Test 1", "2026-07-18", _marks(40, 42, 38, 50, 44)),
                _test("Mid Term", "2026-09-12", _marks(35, 36, 32, 48, 40)),
                _test("Final Term", "2026-11-08", _marks(28, 33, 30, 45, 36)),
            ],
        ),
        _student(
            "S110",
            "Student 110",
            [
                _test("Unit Test 1", "2026-07-18", _marks(80, 75, 78, 88, 40)),
                _test("Mid Term", "2026-09-12", _marks(86, 82, 84, 92, 36)),
                _test("Final Term", "2026-11-08", _marks(91, 86, 88, 96, 32)),
            ],
        ),
        _student(
            "S111",
            "Student 111",
            [
                _test("Unit Test 1", "2026-07-18", _marks(84, 86, 85, 88, 82)),
                _test("Final Term", "2026-11-08", _marks(90, 91, 90, 93, 90)),
            ],
        ),
        _student(
            "S112",
            "Student 112",
            [
                _test("Unit Test 1", "2026-07-18", _marks(62, 64, 66, 60, 63)),
                _test("Final Term", "2026-11-08", _marks(70, 69, 71, 68, 72)),
            ],
        ),
    ]


def _clean_marks(raw_marks) -> dict:
    cleaned = {}
    source = raw_marks if isinstance(raw_marks, dict) else {}
    for subject in SUBJECTS:
        try:
            cleaned[subject] = round(float(source.get(subject, 0)), 2)
        except (TypeError, ValueError):
            cleaned[subject] = 0.0
    return cleaned


def _clean_tests(raw_tests) -> list[dict]:
    tests = []
    if not isinstance(raw_tests, list):
        return tests
    for item in raw_tests:
        if not isinstance(item, dict):
            continue
        name = str(item.get("test_name") or "").strip()
        test_date = str(item.get("test_date") or "").strip()
        if not name:
            continue
        tests.append(
            {
                "test_name": name,
                "test_date": test_date,
                "marks": _clean_marks(item.get("marks")),
            }
        )
    return tests


def _clean_student(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    roll_no = str(raw.get("roll_no") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not roll_no or not name:
        return None
    return {
        "roll_no": roll_no,
        "name": name,
        "marks": _clean_marks(raw.get("marks")),
        "tests": _clean_tests(raw.get("tests")),
    }


def to_storage(student: dict) -> dict:
    """Keep the JSON file limited to stored fields, never calculated ones."""
    return {
        "roll_no": student["roll_no"],
        "name": student["name"],
        "marks": _clean_marks(student.get("marks")),
        "tests": _clean_tests(student.get("tests")),
    }


def _atomic_write(students: list[dict]) -> None:
    payload = {"students": [to_storage(student) for student in students]}
    directory = str(DATA_FILE.parent)
    fd, temp_path = tempfile.mkstemp(prefix="students-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_path, DATA_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


class StudentStore:
    """In-memory records for one request, plus a safe save back to disk."""

    def __init__(self, students: list[dict], writable: bool, message: str = ""):
        self.students = students
        self.writable = writable
        self.message = message

    def save(self) -> None:
        if not self.writable:
            raise DataSaveError(
                self.message
                or "Student data was not saved because students.json could not be read safely."
            )
        _atomic_write(self.students)


def open_store() -> StudentStore:
    """Read students.json, creating initial demo records when it is missing."""
    if not DATA_FILE.exists():
        students = initial_students()
        try:
            _atomic_write(students)
        except OSError as exc:
            return StudentStore(
                [],
                False,
                f"Could not create students.json ({exc}).",
            )
        return StudentStore(students, True, "")

    try:
        content = DATA_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        return StudentStore([], False, f"Could not read students.json ({exc}).")

    if not content.strip():
        return StudentStore([], True, "")

    try:
        data = json.loads(content, parse_constant=_reject_json_constant)
    except ValueError:
        return StudentStore(
            [],
            False,
            "students.json is corrupted, so it was left unchanged. "
            "Fix or replace the file before adding or editing students.",
        )

    if isinstance(data, dict) and isinstance(data.get("students"), list):
        raw_students = data["students"]
    elif isinstance(data, list):
        raw_students = data
    else:
        return StudentStore(
            [],
            False,
            "students.json has an unexpected structure, so it was left unchanged.",
        )

    cleaned = []
    for item in raw_students:
        student = _clean_student(item)
        if student is None:
            return StudentStore(
                [],
                False,
                "students.json contains a record without a name or roll number, "
                "so nothing was overwritten. Correct the file and reload the page.",
            )
        cleaned.append(student)
    return StudentStore(cleaned, True, "")
