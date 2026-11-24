# FRTMS — FastAPI edition

A FastAPI-based conversion of the supplied FRTMS Founder Time OS Streamlit application. The UI is served as HTML templates with a responsive CSS light theme; FastAPI handles page routes, form submissions, CSV export, and JSON API endpoints. SQLite remains the local database.

## Run on Windows
1. Extract this ZIP to a folder such as `C:\FRTMS_FastAPI`.
2. Install Python 3.10 or newer.
3. Double-click `run_windows.bat`.
4. Open **http://127.0.0.1:8000**.

## Run manually (PowerShell)
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

## Features
- Overview dashboard with task, project and time metrics
- Task create, status update and delete
- Project creation and listing
- Goal creation and progress updates
- Time logging and time-entry table
- Founder reports and CSV task export
- SQLite persistence in `frtms.db`
- Responsive light theme with readable contrast
- JSON read endpoints: `/api/health`, `/api/tasks`, `/api/projects`, `/api/goals`, `/api/time-logs`
- Interactive API documentation at `/docs`

## Existing database
The app creates `frtms.db` automatically in this folder. To retain existing data, copy your existing `frtms.db` into this folder before the first run. Back up the database before replacing or migrating anything.

## Note
This conversion keeps the original MVP scope. It does not yet add authentication, multi-user permissions, email notifications, cloud deployment or PostgreSQL. Do not expose it publicly until security and access controls are implemented.
