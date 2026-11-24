from pathlib import Path
from datetime import date, timedelta
import csv, io, sqlite3
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "frtms.db"
app = FastAPI(title="FRTMS | Founder Time OS", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
PAGES = [("overview", "Overview"), ("tasks", "My tasks"), ("projects", "Projects"), ("goals", "Goals"), ("time-tracker", "Time tracker"), ("reports", "Reports")]


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, project TEXT, owner TEXT, priority TEXT, status TEXT, due TEXT);
        CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, owner TEXT, status TEXT, target TEXT, description TEXT);
        CREATE TABLE IF NOT EXISTS goals(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, area TEXT, target TEXT, progress INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS time_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, activity TEXT NOT NULL, project TEXT, owner TEXT, minutes INTEGER, workday TEXT, notes TEXT);
        """)
        if con.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
            con.executemany("INSERT INTO projects(name,owner,status,target,description) VALUES(?,?,?,?,?)", [
                ("Brand growth", "Founder", "Active", (date.today()+timedelta(days=30)).isoformat(), "Growth initiatives and partnerships"),
                ("Operations reset", "Founder", "Active", (date.today()+timedelta(days=14)).isoformat(), "Build repeatable operating systems"),
                ("Product launch", "Team", "Planning", (date.today()+timedelta(days=45)).isoformat(), "Prepare the next launch milestone")])
        if con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
            con.executemany("INSERT INTO tasks(title,project,owner,priority,status,due) VALUES(?,?,?,?,?,?)", [
                ("Set the top 3 priorities for this week", "Brand growth", "Founder", "High", "In progress", date.today().isoformat()),
                ("Review project timelines", "Operations reset", "Founder", "Medium", "To do", (date.today()+timedelta(days=1)).isoformat()),
                ("Prepare launch action plan", "Product launch", "Team", "High", "To do", (date.today()+timedelta(days=4)).isoformat())])


@app.on_event("startup")
def startup():
    init_db()


def rows(sql, params=()):
    with db() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def execute(sql, params=()):
    with db() as con:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid


def page(request: Request, active: str, title: str, **context):
    return templates.TemplateResponse("page.html", {"request": request, "active": active, "nav": PAGES, "title": title, "today": date.today().strftime("%A, %d %B %Y"), "today_iso": date.today().isoformat(), **context})


@app.get("/", response_class=HTMLResponse)
@app.get("/overview", response_class=HTMLResponse)
def overview(request: Request):
    tasks = rows("SELECT * FROM tasks ORDER BY id DESC")
    projects = rows("SELECT * FROM projects ORDER BY id DESC")
    logs = rows("SELECT * FROM time_logs ORDER BY workday DESC,id DESC")
    today_minutes = sum(x["minutes"] or 0 for x in logs if x["workday"] == date.today().isoformat())
    status_counts = {}
    for t in tasks: status_counts[t["status"]] = status_counts.get(t["status"], 0) + 1
    return page(request, "overview", "Overview", tasks=tasks, projects=projects, logs=logs,
        open_tasks=sum(t["status"] != "Done" for t in tasks), completed=sum(t["status"] == "Done" for t in tasks),
        active_projects=sum(p["status"] == "Active" for p in projects), today_hours=f"{today_minutes/60:.1f}",
        priorities=[t for t in tasks if t["status"] != "Done"][:6], status_counts=status_counts)


@app.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request):
    return page(request, "tasks", "My tasks", tasks=rows("SELECT * FROM tasks ORDER BY id DESC"), projects=rows("SELECT name FROM projects ORDER BY name"))


@app.post("/tasks")
def create_task(title: str = Form(...), project: str = Form(""), owner: str = Form("Founder"), priority: str = Form("Medium"), status: str = Form("To do"), due: str = Form("")):
    if not title.strip(): raise HTTPException(400, "Task name is required")
    execute("INSERT INTO tasks(title,project,owner,priority,status,due) VALUES(?,?,?,?,?,?)", (title.strip(), project, owner, priority, status, due))
    return RedirectResponse("/tasks", status_code=303)


@app.post("/tasks/{task_id}/status")
def update_task(task_id: int, status: str = Form(...)):
    if status not in ["To do", "In progress", "Done"]: raise HTTPException(400, "Invalid status")
    execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    return RedirectResponse("/tasks", status_code=303)


@app.post("/tasks/{task_id}/delete")
def delete_task(task_id: int):
    execute("DELETE FROM tasks WHERE id=?", (task_id,))
    return RedirectResponse("/tasks", status_code=303)


@app.get("/projects", response_class=HTMLResponse)
def projects_page(request: Request):
    return page(request, "projects", "Projects", projects=rows("SELECT * FROM projects ORDER BY id DESC"))


@app.post("/projects")
def create_project(name: str = Form(...), description: str = Form(""), owner: str = Form("Founder"), target: str = Form(""), status: str = Form("Planning")):
    if not name.strip(): raise HTTPException(400, "Project name is required")
    execute("INSERT INTO projects(name,owner,status,target,description) VALUES(?,?,?,?,?)", (name.strip(), owner, status, target, description))
    return RedirectResponse("/projects", status_code=303)


@app.get("/goals", response_class=HTMLResponse)
def goals_page(request: Request):
    return page(request, "goals", "Goals & milestones", goals=rows("SELECT * FROM goals ORDER BY id DESC"))


@app.post("/goals")
def create_goal(title: str = Form(...), area: str = Form("Business"), target: str = Form(""), progress: int = Form(0)):
    if not title.strip(): raise HTTPException(400, "Goal is required")
    execute("INSERT INTO goals(title,area,target,progress) VALUES(?,?,?,?)", (title.strip(), area, target, max(0,min(100,progress))))
    return RedirectResponse("/goals", status_code=303)


@app.post("/goals/{goal_id}/progress")
def update_goal(goal_id: int, progress: int = Form(...)):
    execute("UPDATE goals SET progress=? WHERE id=?", (max(0,min(100,progress)), goal_id))
    return RedirectResponse("/goals", status_code=303)


@app.get("/time-tracker", response_class=HTMLResponse)
def time_page(request: Request):
    logs = rows("SELECT * FROM time_logs ORDER BY workday DESC,id DESC")
    total = sum(x["minutes"] or 0 for x in logs)
    return page(request, "time-tracker", "Time tracker", logs=logs, projects=rows("SELECT name FROM projects ORDER BY name"), total_hours=f"{total/60:.1f}")


@app.post("/time-tracker")
def create_log(activity: str = Form(...), project: str = Form(""), owner: str = Form("Founder"), minutes: int = Form(60), workday: str = Form(""), notes: str = Form("")):
    if not activity.strip(): raise HTTPException(400, "Activity is required")
    execute("INSERT INTO time_logs(activity,project,owner,minutes,workday,notes) VALUES(?,?,?,?,?,?)", (activity.strip(), project, owner, max(1,min(1440,minutes)), workday or date.today().isoformat(), notes))
    return RedirectResponse("/time-tracker", status_code=303)


@app.get("/reports", response_class=HTMLResponse)
def reports(request: Request):
    tasks = rows("SELECT * FROM tasks")
    goals = rows("SELECT * FROM goals")
    logs = rows("SELECT * FROM time_logs")
    done = sum(t["status"] == "Done" for t in tasks)
    completion = round(done/len(tasks)*100) if tasks else 0
    project_hours = {}
    for log in logs: project_hours[log["project"] or "No project"] = project_hours.get(log["project"] or "No project", 0) + (log["minutes"] or 0)
    return page(request, "reports", "Founder reports", tasks=tasks, goals=goals, logs=logs, completion=completion, hours=f"{sum(x['minutes'] or 0 for x in logs)/60:.1f}", project_hours=project_hours)


@app.get("/reports/tasks.csv")
def export_tasks():
    data = rows("SELECT * FROM tasks ORDER BY id")
    output = io.StringIO()
    fields = ["id", "title", "project", "owner", "priority", "status", "due"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader(); writer.writerows(data)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=frtms_tasks_{date.today().isoformat()}.csv"})


# JSON API endpoints for integrations/mobile clients.
@app.get("/api/health")
def health(): return {"status": "ok", "app": "FRTMS"}
@app.get("/api/tasks")
def api_tasks(): return rows("SELECT * FROM tasks ORDER BY id DESC")
@app.get("/api/projects")
def api_projects(): return rows("SELECT * FROM projects ORDER BY id DESC")
@app.get("/api/goals")
def api_goals(): return rows("SELECT * FROM goals ORDER BY id DESC")
@app.get("/api/time-logs")
def api_time_logs(): return rows("SELECT * FROM time_logs ORDER BY workday DESC,id DESC")
