"""Grade rules, student results, and class statistics.

Every route uses these functions so totals, grades, and pass/fail
decisions stay consistent across the dashboard, reports, and CSV export.
"""

from __future__ import annotations

SUBJECTS = [
    "Mathematics",
    "Physics",
    "Chemistry",
    "Computer Science",
    "English",
]

# Official class record: each subject is marked out of 100.
MAX_MARK_PER_SUBJECT = 100
PASS_MARK = 40
IMPROVEMENT_THRESHOLD = 50

GRADE_ORDER = ["A+", "A", "B", "C", "D", "E", "F"]

# Shown on the add-student and report pages.
GRADE_BANDS = [
    ("90–100", "A+"),
    ("80–89", "A"),
    ("70–79", "B"),
    ("60–69", "C"),
    ("50–59", "D"),
    ("40–49", "E"),
    ("Below 40", "F"),
]


def format_number(value: float) -> str:
    """Show whole marks as integers and everything else to two decimals."""
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"


def maximum_marks(subject_count: int | None = None) -> int:
    count = len(SUBJECTS) if subject_count is None else subject_count
    return count * MAX_MARK_PER_SUBJECT


def calculate_total(marks: dict) -> float:
    return round(sum(float(marks.get(subject, 0)) for subject in SUBJECTS), 2)


def calculate_percentage(total: float, maximum: int | None = None) -> float:
    cap = maximum_marks() if maximum is None else maximum
    if cap <= 0:
        return 0.0
    return round((float(total) / cap) * 100, 2)


def assign_grade(percentage: float) -> str:
    """Map an overall percentage to the project grade scale."""
    if percentage >= 90:
        return "A+"
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B"
    if percentage >= 60:
        return "C"
    if percentage >= 50:
        return "D"
    if percentage >= 40:
        return "E"
    return "F"


def is_passed(marks: dict) -> bool:
    """A student passes only with at least 40 in every subject."""
    return all(float(marks.get(subject, 0)) >= PASS_MARK for subject in SUBJECTS)


def build_result(marks: dict) -> dict:
    """Attach total, percentage, grade, and pass/fail to one mark sheet."""
    cleaned = {}
    for subject in SUBJECTS:
        try:
            cleaned[subject] = round(float(marks.get(subject, 0)), 2)
        except (TypeError, ValueError):
            cleaned[subject] = 0.0
    total = calculate_total(cleaned)
    maximum = maximum_marks()
    percentage = calculate_percentage(total, maximum)
    passed = is_passed(cleaned)
    return {
        "marks": cleaned,
        "total": total,
        "maximum": maximum,
        "percentage": percentage,
        "grade": assign_grade(percentage),
        "passed": passed,
        "status": "Pass" if passed else "Fail",
    }


def with_performance(student: dict) -> dict:
    """Return a display copy of a student, including each saved test."""
    result = build_result(student.get("marks") or {})
    tests = []
    for test in student.get("tests") or []:
        test_result = build_result(test.get("marks") or {})
        tests.append(
            {
                "test_name": test.get("test_name") or "Test",
                "test_date": test.get("test_date") or "",
                **test_result,
            }
        )
    tests.sort(key=lambda item: (item["test_date"] or "9999-99-99", item["test_name"]))
    return {
        "roll_no": student.get("roll_no", ""),
        "name": student.get("name", ""),
        "tests": tests,
        **result,
    }


def subjects_below_pass(student: dict) -> list[dict]:
    return [
        {"subject": subject, "marks": student["marks"][subject]}
        for subject in SUBJECTS
        if float(student["marks"][subject]) < PASS_MARK
    ]


def needs_improvement(student: dict, threshold: float = IMPROVEMENT_THRESHOLD) -> bool:
    if float(student["percentage"]) < threshold:
        return True
    return any(float(student["marks"][subject]) < PASS_MARK for subject in SUBJECTS)


def improvement_profile(student: dict, threshold: float = IMPROVEMENT_THRESHOLD) -> dict | None:
    """Explain why a student needs attention, or return None."""
    if not needs_improvement(student, threshold):
        return None

    low = subjects_below_pass(student)
    reasons = []
    if low:
        listed = ", ".join(
            f"{item['subject']} ({format_number(item['marks'])})" for item in low
        )
        reasons.append(f"Scored below {PASS_MARK} in {listed}.")
    if float(student["percentage"]) < threshold:
        reasons.append(
            f"Overall percentage is {student['percentage']:.2f}%, which is below {threshold:.0f}%."
        )

    if low:
        focus = ", ".join(item["subject"] for item in low)
        message = (
            f"Priority: raise {focus} to at least {PASS_MARK}. "
            "Revise those topics, practice past questions, and sit a short retest "
            f"before aiming for an overall percentage of {threshold:.0f}% or higher."
        )
        low_subjects = low
    else:
        weakest = min(SUBJECTS, key=lambda subject: (student["marks"][subject], subject))
        message = (
            f"Every subject is at least {PASS_MARK}, so this student has passed. "
            f"The overall percentage is still under {threshold:.0f}%. "
            f"The weakest subject is {weakest} "
            f"({format_number(student['marks'][weakest])}). "
            "A focused revision plan there should lift the grade."
        )
        low_subjects = [
            {"subject": weakest, "marks": student["marks"][weakest], "weakest": True}
        ]

    return {
        "low_subjects": low_subjects,
        "reasons": reasons,
        "message": message,
    }


def subject_averages(students: list[dict]) -> dict:
    averages = {}
    count = len(students)
    for subject in SUBJECTS:
        if count == 0:
            averages[subject] = 0.0
        else:
            total = sum(float(student["marks"][subject]) for student in students)
            averages[subject] = round(total / count, 2)
    return averages


def grade_distribution(students: list[dict]) -> dict:
    counts = {grade: 0 for grade in GRADE_ORDER}
    for student in students:
        grade = student.get("grade", "F")
        if grade not in counts:
            grade = "F"
        counts[grade] += 1
    return counts


def find_topper(students: list[dict]) -> dict | None:
    if not students:
        return None
    return max(students, key=lambda student: (student["percentage"], student["total"], student["name"].lower()))


def find_lowest(students: list[dict]) -> dict | None:
    if not students:
        return None
    return min(students, key=lambda student: (student["percentage"], student["total"], student["name"].lower()))


def class_statistics(students: list[dict]) -> dict:
    """Summaries used by the dashboard and the class report."""
    total_students = len(students)
    averages = subject_averages(students)
    grades = grade_distribution(students)
    passed = [student for student in students if student["passed"]]
    failed = [student for student in students if not student["passed"]]
    improvement = [student for student in students if needs_improvement(student)]
    topper = find_topper(students)
    lowest = find_lowest(students)

    if total_students:
        class_average = round(sum(student["percentage"] for student in students) / total_students, 2)
        pass_percentage = round(len(passed) / total_students * 100, 2)
    else:
        class_average = 0.0
        pass_percentage = 0.0

    failed_sorted = sorted(failed, key=lambda student: (student["percentage"], student["name"].lower()))
    return {
        "total_students": total_students,
        "total_subjects": len(SUBJECTS),
        "class_average": class_average,
        "passed_count": len(passed),
        "failed_count": len(failed),
        "improvement_count": len(improvement),
        "topper": topper,
        "lowest": lowest,
        "highest_percentage": topper["percentage"] if topper else 0.0,
        "lowest_percentage": lowest["percentage"] if lowest else 0.0,
        "pass_percentage": pass_percentage,
        "subject_averages": averages,
        "grade_counts": grades,
        "failed_students": failed_sorted,
    }
