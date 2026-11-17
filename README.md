# Student Performance Dashboard

A local academic performance manager built with Flask, Jinja2, HTML, CSS, JavaScript, and JSON. It stores records in `students.json`, calculates grades and class statistics, tracks tests, and exports a CSV report. There is no database or paid API.

## Requirements

- Python 3.10 or later
- pip

## Install and run

Open a terminal in the project folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open the local address printed by Flask (normally http://127.0.0.1:5000). To stop the development server, press `Ctrl+C`.

The local `students.json` stores class records and is intentionally excluded from version control. If the file is absent, the application creates generic demonstration records the first time a page is opened. An empty JSON file is treated as an empty class. Malformed or unexpected data is left untouched and displayed with an error message rather than silently overwritten.

## Implemented features

- Dashboard cards for student count, subject count, class average, pass count, students needing improvement, topper, and lowest performer.
- Real-data Chart.js charts for subject averages, grade distribution, overall class percentages, student-versus-class marks, and test progress. Chart.js is bundled locally in `static/js/chart.umd.min.js`.
- Add, view, edit, and delete student records. Deletion requires a POST form and browser confirmation.
- Search by partial name or roll number, case-insensitive, with instant results in the browser and a regular GET search fallback.
- Automatic total, maximum, percentage, grade, and pass/fail calculations.
- Class report with highest/lowest results, topper, subject averages, grade counts, pass percentage, and failed-student details.
- Improvement list for students below 50% overall or below 40 in any subject, including tailored study suggestions.
- Multiple dated tests per student, a progress line chart, and an option to update the official class marks from a test.
- CSV download with marks, totals, percentages, grades, and status.
- Responsive sidebar, tables, forms, and chart layouts; accessible labels and status messages.

## Grade and pass rules

Grades use overall percentage: A+ (90–100), A (80–89), B (70–79), C (60–69), D (50–59), E (40–49), and F (below 40). A student passes only when every subject mark is at least 40. The improvement threshold is 50%.

## Project layout

```text
app.py                  Flask routes and input validation
calculations.py         Shared grade and statistics functions
data_manager.py         Safe JSON loading and atomic saving
students.json           Local demo and class data (not tracked by Git)
requirements.txt        Python dependency
templates/              Jinja2 pages and reusable macros
static/css/style.css    Responsive styling
static/js/charts.js     Chart.js initialization
static/js/chart.umd.min.js  Locally bundled Chart.js library
```

## Data format

The JSON document contains a top-level `students` array. Each student stores `roll_no`, `name`, subject `marks`, and a `tests` array. Totals and grades are calculated when records are read; they are not duplicated in the file. Saving uses a temporary file followed by an atomic replace to reduce the chance of a partial write.

The app is intended for local classroom demonstration. The built-in Flask development server and its demo secret key are not intended for public production deployment.
