"""Student Performance Dashboard.

Teachers can add students, record subject marks, review grades, track
tests, and download a class report. Records live in students.json.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, Response, url_for

from calculations import (
    GRADE_BANDS,
    GRADE_ORDER,
    IMPROVEMENT_THRESHOLD,
    PASS_MARK,
    SUBJECTS,
    class_statistics,
    format_number,
    improvement_profile,
    with_performance,
)
from data_manager import DataSaveError, open_store

app = Flask(__name__)
app.secret_key = "student-performance-dashboard-local-demo"

MARK_FIELDS = {
    "Mathematics": "mark_mathematics",
    "Physics": "mark_physics",
    "Chemistry": "mark_chemistry",
    "Computer Science": "mark_computer_science",
    "English": "mark_english",
}

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'\-]{0,58}[A-Za-z.]$")
ROLL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-]{0,19}$")

NAV_ITEMS = [
    {"endpoint": "dashboard", "label": "Dashboard", "icon": "dashboard"},
    {"endpoint": "add_student", "label": "Add Student", "icon": "add"},
    {"endpoint": "students", "label": "Student Records", "icon": "records"},
    {"endpoint": "search", "label": "Search Student", "icon": "search"},
    {"endpoint": "reports", "label": "Performance Reports", "icon": "reports"},
    {"endpoint": "improvement", "label": "Improvement Required", "icon": "alert"},
    {"endpoint": "export_csv", "label": "Export CSV", "icon": "download"},
]
RECORD_ENDPOINTS = {"students", "student_details", "edit_student", "student_progress", "add_test"}


@app.template_filter("mark")
def mark_filter(value) -> str:
    try:
        return format_number(value)
    except (TypeError, ValueError):
        return "0"


@app.template_filter("pct")
def pct_filter(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


@app.template_filter("pretty_date")
def pretty_date_filter(value: str) -> str:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%d %b %Y")
    except (TypeError, ValueError):
        return str(value or "—")


@app.context_processor
def inject_globals():
    today = date.today()
    academic_year_start = today.year if today.month >= 4 else today.year - 1
    return {
        "subjects": SUBJECTS,
        "pass_mark": PASS_MARK,
        "improvement_threshold": IMPROVEMENT_THRESHOLD,
        "grade_bands": GRADE_BANDS,
        "nav_items": NAV_ITEMS,
        "record_endpoints": RECORD_ENDPOINTS,
        "mark_fields": MARK_FIELDS,
        "today_display": today.strftime("%d %b %Y"),
        "academic_year": f"{academic_year_start}–{str(academic_year_start + 1)[-2:]}",
    }


def load_records():
    """Open the JSON file and return raw rows plus calculated display rows."""
    store = open_store()
    if store.message:
        flash(store.message, "error")
    records = [with_performance(student) for student in store.students]
    records.sort(key=lambda student: student["roll_no"].lower())
    return store, records


def persist(store) -> bool:
    try:
        store.save()
        return True
    except DataSaveError as exc:
        flash(str(exc), "error")
    except OSError:
        flash("The student file could not be saved. Check that this folder is writable.", "error")
    return False


def find_student(students: list[dict], roll_no: str) -> dict | None:
    needle = str(roll_no).strip().lower()
    for student in students:
        if student["roll_no"].lower() == needle:
            return student
    return None


def empty_student_form() -> dict:
    return {
        "name": "",
        "roll_no": "",
        "marks": {subject: "" for subject in SUBJECTS},
    }


def form_from_request() -> dict:
    return {
        "name": request.form.get("name", ""),
        "roll_no": request.form.get("roll_no", ""),
        "marks": {
            subject: request.form.get(field, "")
            for subject, field in MARK_FIELDS.items()
        },
    }


def form_from_student(student: dict) -> dict:
    return {
        "name": student["name"],
        "roll_no": student["roll_no"],
        "marks": {subject: format_number(student["marks"][subject]) for subject in SUBJECTS},
    }


def parse_marks(source: dict) -> tuple[dict, list[str]]:
    marks = {}
    errors = []
    for subject in SUBJECTS:
        raw = str(source.get(subject, "")).strip()
        if raw == "":
            errors.append(f"{subject} marks are required.")
            continue
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"{subject} marks must be a number.")
            continue
        if value != value or value in (float("inf"), float("-inf")):
            errors.append(f"{subject} marks must be a number.")
            continue
        if value < 0 or value > 100:
            errors.append(f"{subject} marks must be between 0 and 100.")
            continue
        rounded = round(value, 2)
        marks[subject] = int(rounded) if rounded.is_integer() else rounded
    return marks, errors


def parse_name(raw: str) -> tuple[str, str | None]:
    name = " ".join(str(raw).split())
    if not name:
        return "", "Student name is required."
    if len(name) < 2 or len(name) > 60:
        return name, "Student name must be between 2 and 60 characters."
    if not NAME_PATTERN.match(name):
        return name, "Student name can contain only letters, spaces, apostrophes, periods, and hyphens."
    return name, None


def parse_roll(raw: str, students: list[dict], current_roll: str | None = None) -> tuple[str, str | None]:
    roll_no = str(raw).strip()
    if not roll_no:
        return "", "Roll number is required."
    if not ROLL_PATTERN.match(roll_no):
        return roll_no, "Roll number must be 1–20 letters, numbers, or hyphens."
    existing = find_student(students, roll_no)
    if existing and (current_roll is None or existing["roll_no"].lower() != current_roll.lower()):
        return roll_no, f"Roll number {existing['roll_no']} is already used by {existing['name']}."
    return roll_no, None


def chart_payload(records: list[dict], stats: dict) -> dict:
    ranked = sorted(records, key=lambda student: student["percentage"], reverse=True)
    return {
        "subjects": list(SUBJECTS),
        "averages": [stats["subject_averages"][subject] for subject in SUBJECTS],
        "grades": list(GRADE_ORDER),
        "grade_counts": [stats["grade_counts"][grade] for grade in GRADE_ORDER],
        "student_names": [student["name"] for student in ranked],
        "percentages": [student["percentage"] for student in ranked],
        "passed": [student["passed"] for student in ranked],
    }


def csv_safe(value) -> str:
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def build_csv(records: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Roll Number",
            "Student Name",
            *SUBJECTS,
            "Total Marks",
            "Maximum Marks",
            "Percentage",
            "Grade",
            "Status",
        ]
    )
    ordered = sorted(records, key=lambda student: student["roll_no"].lower())
    for student in ordered:
        writer.writerow(
            [
                csv_safe(student["roll_no"]),
                csv_safe(student["name"]),
                *[student["marks"][subject] for subject in SUBJECTS],
                student["total"],
                student["maximum"],
                f"{student['percentage']:.2f}",
                student["grade"],
                student["status"],
            ]
        )
    return buffer.getvalue()


def render_progress_page(roll_no: str, test_form: dict | None = None, errors: list | None = None):
    store, records = load_records()
    raw = find_student(store.students, roll_no)
    if raw is None:
        flash(f"No student found with roll number {roll_no}.", "error")
        return redirect(url_for("students"))
    student = with_performance(raw)
    if test_form is None:
        test_form = {
            "test_name": "",
            "test_date": date.today().isoformat(),
            "marks": {subject: "" for subject in SUBJECTS},
            "update_official": False,
        }
    chart = {
        "labels": [
            f"{test['test_name']} ({test['test_date']})" if test["test_date"] else test["test_name"]
            for test in student["tests"]
        ],
        "percentage": [test["percentage"] for test in student["tests"]],
        "subjects": {
            subject: [test["marks"][subject] for test in student["tests"]] for subject in SUBJECTS
        },
    }
    return render_template(
        "student_progress.html",
        student=student,
        test_form=test_form,
        errors=errors or [],
        chart_data=chart,
    )


@app.route("/")
def dashboard():
    _store, records = load_records()
    stats = class_statistics(records)
    ranking = sorted(records, key=lambda student: (-student["percentage"], student["name"].lower()))
    return render_template(
        "dashboard.html",
        stats=stats,
        ranking=ranking[:5],
        chart_data=chart_payload(records, stats),
        has_students=bool(records),
    )


@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    store, _records = load_records()
    form = empty_student_form()
    errors = []
    if request.method == "POST":
        form = form_from_request()
        name, name_error = parse_name(form["name"])
        roll_no, roll_error = parse_roll(form["roll_no"], store.students)
        marks, mark_errors = parse_marks(form["marks"])
        errors = [error for error in (name_error, roll_error) if error] + mark_errors
        form["name"] = name or form["name"]
        form["roll_no"] = roll_no or form["roll_no"]
        if not errors:
            today = date.today().isoformat()
            store.students.append(
                {
                    "roll_no": roll_no,
                    "name": name,
                    "marks": dict(marks),
                    "tests": [
                        {
                            "test_name": "Initial Record",
                            "test_date": today,
                            "marks": dict(marks),
                        }
                    ],
                }
            )
            if persist(store):
                flash(
                    f"{name} was added. The marks were also saved as a progress test named Initial Record.",
                    "success",
                )
                return redirect(url_for("student_details", roll_no=roll_no))
    return render_template("add_student.html", form=form, errors=errors)


@app.route("/students")
def students():
    _store, records = load_records()
    return render_template("students.html", records=records)


@app.route("/student/<roll_no>")
def student_details(roll_no):
    _store, records = load_records()
    student = find_student(records, roll_no)
    if student is None:
        flash(f"No student found with roll number {roll_no}.", "error")
        return redirect(url_for("students"))
    stats = class_statistics(records)
    chart = {
        "subjects": list(SUBJECTS),
        "marks": [student["marks"][subject] for subject in SUBJECTS],
        "averages": [stats["subject_averages"][subject] for subject in SUBJECTS],
    }
    return render_template("student_details.html", student=student, chart_data=chart)


@app.route("/edit_student/<roll_no>", methods=["GET", "POST"])
def edit_student(roll_no):
    store, records = load_records()
    raw = find_student(store.students, roll_no)
    if raw is None:
        flash(f"No student found with roll number {roll_no}.", "error")
        return redirect(url_for("students"))
    current = with_performance(raw)
    errors = []
    if request.method == "POST":
        form = form_from_request()
        form["roll_no"] = raw["roll_no"]
        name, name_error = parse_name(form["name"])
        marks, mark_errors = parse_marks(form["marks"])
        errors = ([name_error] if name_error else []) + mark_errors
        form["name"] = name or form["name"]
        if not errors:
            raw["name"] = name
            raw["marks"] = dict(marks)
            if persist(store):
                flash(f"{name}'s official marks were updated. Test history was left as it is.", "success")
                return redirect(url_for("student_details", roll_no=raw["roll_no"]))
    else:
        form = form_from_student(current)
    return render_template("edit_student.html", form=form, student=current, errors=errors)


@app.route("/delete_student/<roll_no>", methods=["GET", "POST"])
def delete_student(roll_no):
    if request.method != "POST":
        flash("Use the Delete button and confirm the message to remove a student.", "info")
        return redirect(url_for("student_details", roll_no=roll_no))

    store, _records = load_records()
    student = find_student(store.students, roll_no)
    if student is None:
        flash(f"No student found with roll number {roll_no}.", "error")
        return redirect(url_for("students"))

    store.students = [
        item for item in store.students if item["roll_no"].lower() != student["roll_no"].lower()
    ]
    if persist(store):
        flash(f"{student['name']} (Roll {student['roll_no']}) was deleted.", "success")
    return redirect(url_for("students"))


@app.route("/search")
def search():
    _store, records = load_records()
    query = request.args.get("q", "").strip()
    if len(query) > 80:
        query = query[:80]
    matches = []
    if query:
        needle = query.lower()
        matches = [
            student
            for student in records
            if needle in student["name"].lower() or needle in student["roll_no"].lower()
        ]
        matches.sort(key=lambda student: student["name"].lower())
    catalog = [
        {
            "name": student["name"],
            "roll_no": student["roll_no"],
            "percentage": student["percentage"],
            "grade": student["grade"],
            "status": student["status"],
            "url": url_for("student_details", roll_no=student["roll_no"]),
            "edit_url": url_for("edit_student", roll_no=student["roll_no"]),
            "delete_url": url_for("delete_student", roll_no=student["roll_no"]),
        }
        for student in records
    ]
    return render_template(
        "search.html",
        query=query,
        matches=matches,
        searched=bool(query),
        catalog=catalog,
    )


@app.route("/reports")
def reports():
    _store, records = load_records()
    stats = class_statistics(records)
    return render_template(
        "reports.html",
        stats=stats,
        records=records,
        chart_data=chart_payload(records, stats),
        has_students=bool(records),
    )


@app.route("/improvement")
def improvement():
    _store, records = load_records()
    rows = []
    for student in records:
        profile = improvement_profile(student)
        if profile:
            rows.append({**student, "improvement": profile})
    rows.sort(key=lambda student: (student["percentage"], student["name"].lower()))
    return render_template("improvement.html", rows=rows, total_students=len(records))


@app.route("/export_csv")
def export_csv():
    _store, records = load_records()
    payload = build_csv(records).encode("utf-8-sig")
    return Response(
        payload,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=class_performance_report.csv"},
    )


@app.route("/student_progress/<roll_no>")
def student_progress(roll_no):
    return render_progress_page(roll_no)


@app.route("/add_test/<roll_no>", methods=["GET", "POST"])
def add_test(roll_no):
    if request.method == "GET":
        return render_progress_page(roll_no)

    store, _records = load_records()
    raw = find_student(store.students, roll_no)
    if raw is None:
        flash(f"No student found with roll number {roll_no}.", "error")
        return redirect(url_for("students"))

    test_form = {
        "test_name": " ".join(request.form.get("test_name", "").split()),
        "test_date": request.form.get("test_date", "").strip(),
        "marks": {subject: request.form.get(MARK_FIELDS[subject], "") for subject in SUBJECTS},
        "update_official": request.form.get("update_official") == "yes",
    }
    errors = []
    if not test_form["test_name"]:
        errors.append("Test name is required.")
    elif len(test_form["test_name"]) > 40:
        errors.append("Test name must be 40 characters or fewer.")
    try:
        datetime.strptime(test_form["test_date"], "%Y-%m-%d")
    except ValueError:
        errors.append("Test date is required and must be a valid date.")
    marks, mark_errors = parse_marks(test_form["marks"])
    errors.extend(mark_errors)

    if errors:
        return render_progress_page(roll_no, test_form=test_form, errors=errors)

    raw.setdefault("tests", []).append(
        {
            "test_name": test_form["test_name"],
            "test_date": test_form["test_date"],
            "marks": dict(marks),
        }
    )
    if test_form["update_official"]:
        raw["marks"] = dict(marks)
    if persist(store):
        extra = " Official class marks were updated too." if test_form["update_official"] else ""
        flash(f"{test_form['test_name']} was saved for {raw['name']}.{extra}", "success")
    return redirect(url_for("student_progress", roll_no=raw["roll_no"]))


@app.errorhandler(404)
def page_not_found(_error):
    return render_template(
        "error.html",
        title="Page not found",
        message="That page does not exist. Use the sidebar to get back to the dashboard.",
    ), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template(
        "error.html",
        title="Something went wrong",
        message="An unexpected error occurred. Go back and try that action again.",
    ), 500


if __name__ == "__main__":
    app.run(debug=True)
