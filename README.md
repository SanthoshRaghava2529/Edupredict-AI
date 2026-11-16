# AI-Powered Student Performance Prediction System

EduPredict AI is a complete desktop application for a college CSE AI/ML project. It stores student academic records in SQLite, visualizes them with Matplotlib, and predicts performance categories with a **Random Forest classifier** trained in Scikit-learn.

The interface is a professional Tkinter dashboard (navy and white), not a default-looking form demo. Statistics, charts and predictions are computed from real database values and a real trained model.

## Problem statement

Mentors often notice academic risk too late: attendance has already collapsed, internals are failing, or assignments are incomplete. Spreadsheets do not combine these signals or produce a consistent, explainable category for counselling.

This project provides a single desktop workspace where an administrator can manage records and an ML model can flag **Excellent**, **Good**, **Average** or **At Risk** students. A student login shows only that student's own information.

## Objectives

- Maintain validated student, attendance, marks and assignment records.
- Predict academic performance categories with a trained Random Forest model.
- Identify at-risk students using both the model and transparent thresholds.
- Generate PDF counselling reports.
- Enforce role-based access (admin vs student).

## Features

- Secure login with PBKDF2 password hashing and a forced default-admin password change.
- Admin dashboard with live totals, averages, well-performing / attention counts and charts.
- Full student CRUD, search and department/semester filters.
- Attendance entry, automatic percentage recalculation, configurable threshold (default 75%) and low-attendance alerts.
- Subject marks and assignment entry with maximum-score validation.
- Train / load Random Forest, predict one student or the full class, store results in SQLite.
- At-risk module with reasons, suggested actions and CSV export.
- Analytics: performance mix, attendance bands, subject averages, top students.
- Student portal limited to the signed-in student ID.
- Individual and class-level PDF reports (ReportLab).

## Technology stack

| Layer | Library |
| --- | --- |
| Language | Python 3.12 |
| GUI | Tkinter / ttk |
| Database | SQLite |
| Data | Pandas, NumPy |
| Machine learning | Scikit-learn, joblib |
| Charts | Matplotlib |
| Images | Pillow |
| PDF | ReportLab |
| Passwords | hashlib PBKDF2-HMAC-SHA256 |

Compatible versions are pinned in `requirements.txt`.

## Folder structure

```
AI_Student_Performance_System/   (this project root)
├── tkinter_app/          GUI (login, dashboard, students, analytics, prediction, …)
├── database/             SQLite helpers and password hashing
├── models/               Dataset, training, predictor
├── assets/               Images and icons
├── reports/              Generated PDFs and CSV exports
├── data/                 Sample + training CSV (created when the model is trained)
├── tests/                Automated tests
├── venv/                 Virtual environment (created locally)
├── config.py
├── requirements.txt
└── README.md
```

## Installation

Use **Python 3.12 or 3.13**. From the project root (the folder that contains `tkinter_app/`):

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If script execution is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional branding assets:

```powershell
python -m assets.create_branding
```

## Initialize the database

The database file is created automatically on first launch at `database/student_performance.db`.

First run also:

1. Creates tables with primary keys, foreign keys and checks.
2. Inserts the default admin account.
3. Seeds **synthetic demonstration students** (CSE23001, ECE23001, …). These are not real institutional records.

## Train the machine learning model

Predictions require a saved model file. Train it once (or any time from the app):

```powershell
python -m models.train_model
```

This writes:

- `data/training_student_performance.csv` — full synthetic training set
- `data/sample_student_performance.csv` — 200-row sample for inspection
- `models/artifacts/random_forest_model.joblib`
- `models/artifacts/metrics.json` — accuracy, precision, recall, F1, confusion matrix

You can also click **Train / retrain model** on the ML Predictions screen. If no model exists, the UI shows a clear error instead of inventing a category.

## How to run the application

Working directory must be the project root:

```powershell
python -m tkinter_app.main
```

On Windows you can also double-click `run.bat` after the virtual environment is created.

## Default login credentials

| Role | Username | Password | Notes |
| --- | --- | --- | --- |
| Administrator | `admin` | `Admin@123` | **Must be changed on first login.** |
| Demo student | `CSE23001` | `Student@123` | Sees only Aarav Sharma's record. |

Other seeded student usernames match their IDs (`CSE23004`, `ECE23003`, `CSE23007`, …) with password `Student@123`.

Passwords are stored only as salted PBKDF2 hashes.

## Database explanation

| Table | Purpose |
| --- | --- |
| `users` | Login accounts, role, `must_change_password` |
| `students` | Profile + rolled-up attendance / internals / assignments |
| `subjects` | Subject catalogue per department and semester |
| `attendance` | Daily present/absent rows (unique per student, subject, date) |
| `marks` | Examination scores vs maximum |
| `assignments` | Assignment scores vs maximum |
| `predictions` | Stored ML outputs and recommendations |
| `settings` | Attendance threshold and related configuration |

All SQL uses parameterized queries. Student deletion removes related rows (cascade).

## Machine learning methodology

1. **Dataset** — `models/dataset.py` generates a synthetic educational dataset. Every row is tagged `synthetic_demonstration`. A transparent heuristic labels **Excellent / Good / Average / At Risk** from attendance, internals, assignments, previous performance and study hours. A small amount of label noise is added so evaluation is honest.
2. **Cleaning** — Pandas drops incomplete rows and clips features to valid academic ranges.
3. **Split** — 80% train / 20% test, stratified.
4. **Model** — `RandomForestClassifier` (`n_estimators=220`, class-weight balanced).
5. **Evaluation** — accuracy, weighted precision, recall, F1, classification report, confusion matrix. Metrics are written to `metrics.json` from the **held-out test set**. They are not hardcoded in the UI.
6. **Persistence** — joblib saves the fitted model. `models/predictor.py` loads it and maps SQLite student features onto the same columns.
7. **Recommendations** — generated from the predicted class plus explicit threshold checks (for example attendance below 75%).

This is **not** a claim of production accuracy on a real university SIS. Demonstrate the pipeline, the stored metrics, and a few live predictions.

## Dataset description

Features used by the classifier:

- `attendance_percentage`
- `internal_examination_marks`
- `assignment_score`
- `previous_semester_performance`
- `study_hours`

Target: `performance_category`.

Inspect `data/sample_student_performance.csv` after training. Seeded SQLite students are a **separate demonstration roster** used by the GUI; they are not mixed into training unless you export them yourself.

## Model evaluation results

The values below were measured on a **held-out 20% split of the synthetic demonstration set** (2000 train / 500 test rows) and written to `models/artifacts/metrics.json`. Retrain before the viva if you change the dataset, then quote the new file.

| Metric | Value |
| --- | --- |
| Accuracy | 0.974 |
| Precision (weighted) | 0.974 |
| Recall (weighted) | 0.974 |
| F1 (weighted) | 0.974 |

Per-class F1 on that run: At Risk 0.98, Average 0.97, Excellent 0.96, Good 0.97. Feature importances were highest for internal marks and attendance. These numbers describe synthetic data. They are not a claim of production accuracy on real college records.

## Screenshots

Run the application and capture:

1. Login (admin and student roles).
2. Admin dashboard cards and charts.
3. Student management table.
4. Attendance alerts.
5. ML prediction for an excellent student (`CSE23001`) and an at-risk student (`CSE23004` or `CSE23007`).
6. Analytics page.
7. Student portal for `CSE23001`.
8. A generated PDF in `reports/`.

Place captures in `assets/images/` if you want them in a printed report.

## Limitations and future enhancements

- Training data is synthetic. A live college deployment would need consented historical results and a fairness review.
- Study hours are self-reported (or seeded) and should be treated as a weak feature.
- Tkinter resizing is practical, not pixel-perfect on every DPI setting.
- There is no multi-user network server; SQLite is local.

Possible extensions: XGBoost comparison, faculty role, SMS alerts, import from Excel, and an external REST API.

## How to demonstrate this to a professor

Suggested 8-minute path:

1. Show `README.md`, `requirements.txt` and `python -m tkinter_app.main`.
2. Sign in as `admin` / `Admin@123`, change the password, then open the dashboard and point at **live** totals.
3. Search/filter students; edit one mark and show the average update.
4. Open Attendance, show students below 75%, change the threshold, refresh.
5. Open ML Predictions. If needed, train the model. Predict `CSE23001` (strong) and `CSE23007` (at risk). Open `metrics.json` and read accuracy/F1 from disk.
6. Open At-risk students, export CSV.
7. Generate a PDF for `CSE23001` and open `reports/`.
8. Logout. Sign in as `CSE23001` / `Student@123` and show that only that profile is visible.

## Tests

```powershell
python -m unittest tests.test_system
```

Coverage includes login, CRUD, attendance calculation, marks validation, model training/prediction and PDF generation. The current suite (`python -m unittest tests.test_system`) reports 9 passing tests.

## Academic honesty note

Dashboard numbers are queried from SQLite. Predictions come from `joblib` + Scikit-learn. Do not describe this as a cloud AI product or as an officially approved university information system.
