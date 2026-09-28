# Launchpad — Windows Project Launcher

A local dashboard for launching development projects, opening Chrome when their HTTP server is ready, and tracking the entire process tree. Built with **FastAPI, React, Vite, Tailwind CSS, SQLite, SQLAlchemy, and psutil**.

## Public sharing and security

Share this repository's GitHub link. Each person clones it and runs their own local dashboard; your saved projects, private project source code, `.env`, database, logs, and credentials are not part of the repository. Do not publish or tunnel the running launcher API—it can execute commands with your Windows permissions. See [SECURITY.md](SECURITY.md) for the trust boundary and private vulnerability reporting.

GitHub Actions runs Windows integration tests, Chrome end-to-end tests, a frontend build, and dependency audits. Dependabot checks for dependency updates weekly. Security checks reduce risk; this is not a security certification or a multi-user hosted service.

## Installation

Install **Python 3.11+** (enable **Add Python to PATH**), **Node.js 22.12+ LTS**, and Google Chrome. The implementation was tested with Python 3.13 and Node.js 24 on Windows; see [validation notes](#validation).

Clone or copy this folder to a local directory, such as `D:\project_dashboard`. Each project must already have its own dependencies installed.

### Quick start / Windows launch instructions

Double-click **`launcher.bat`**. On first run it:

1. Creates `.venv` and installs backend dependencies.
2. Installs the locked frontend dependencies with `npm ci`.
3. Copies `.env.example` to `.env` if needed.
4. Starts the backend and Vite as hidden background processes.
5. Checks bindable IPv4/IPv6 loopback ports, starts each server on a free port, and opens Chrome at the selected dashboard URL (normally **http://localhost:5173**).

Later launches reuse the recorded server PIDs and selected URLs, even when the default ports are occupied. The launcher does **not** treat unrelated `python.exe` processes as the backend. Chosen endpoints are saved in `data/dashboard-processes.json`; the Vite API proxy and backend allowed origins follow these ports. Initial dependency installation needs an internet connection; the dashboard itself works locally. Optional Google Fonts fall back to installed fonts offline.

Double-click **`stop-dashboard.bat`** to save active project sessions and stop the dashboard servers started by this launcher. PID creation times are checked before stopping any recorded server. Closing the browser tab does **not** stop projects.

If dependencies change after an update, run the manual install commands below again. The automatic launcher's dependency marker is `.venv\launcher-deps.ready`.

### Manual installation

From PowerShell in the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env  # first setup only; preserve an existing .env
cd frontend
npm.cmd ci
```

No virtualenv activation or PowerShell execution-policy change is necessary.

## Running the application

In one PowerShell terminal, from the root:

```powershell
.\.venv\Scripts\python.exe -m backend.main
```

In a second terminal:

```powershell
cd frontend
npm.cmd run dev
```

Open http://localhost:5173. API documentation is at http://127.0.0.1:8000/docs.

Use **one backend process, one worker, and no automatic reload**: it owns the live project processes. A file lock prevents two backends from managing the same database. Graceful backend shutdown stops managed projects and saves sessions. The default servers bind to loopback.

Tables are created automatically. To initialize the database without starting the dashboard:

```powershell
.\.venv\Scripts\python.exe -m backend.database.db
```

## Adding projects

Click **Add project** and enter:

| Field | Meaning | Example |
|---|---|---|
| Name | Display name | Expense tracker |
| Folder | Existing absolute working directory | `D:\Projects\expense-tracker` |
| Startup command | Command to execute in that folder | `npm run dev -- --port 3000 --strictPort` |
| Localhost URL | Optional preferred address; its port is selected automatically | `http://localhost:3000` |
| Type | Manual label | React |
| Description | Optional short description | Personal expense tracking |
| Technologies | Optional comma-separated labels | React, TypeScript |

**Ports are automatic.** At every launch, the dashboard checks the preferred port and searches for a free one if it is occupied, reserved by another starting project, or unavailable for binding. It passes the selected port to recognized commands, waits for an HTTP listener belonging to that project's process tree, and opens the actual URL. Cards, Open buttons, details, and saved sessions use the chosen session URL. Your saved command and preferred URL are preserved.

Supported command adapters include Vite, Next.js, Uvicorn, Flask, Streamlit, Python `http.server`, and simple npm scripts that invoke Vite/Next.js. Create React App uses `PORT`. Custom applications receive `PORT` and `LAUNCHPAD_PORT`; they must actually read one of these, or use **`{port}`** in their command, for example `python server.py --listen {port}`. Arbitrary scripts with hard-coded ports cannot be moved just by changing a browser URL. Shell pipelines are left intact except for explicit `{port}` substitutions.

Project files are never rewritten by automatic launches. Keep servers inside the managed process tree. The bind check is released just before startup so the application can bind it; if an unrelated application wins that short race, readiness will not mistake it for your project. Strict-port mode is enabled for Vite.

Use **Launch project** to start it. The API returns immediately with a `starting` session; the dashboard polls every two seconds. Chrome opens after the endpoint responds. HTTP responses below 500 (including authentication and missing-root responses) count as ready. A startup timeout stops the tree and records a readable failure. Install dependencies before launching so installation doesn't consume the startup timeout.

**Details** shows configuration, captured stdout/stderr, live vitals, and previous sessions. Use **Stop project** to stop the entire process tree or **Restart** to record a new session. Stop a project before editing or deleting its configuration. Deletion removes its database usage history; it never deletes the project folder.

### Common Windows commands

| Project | Startup command | URL |
|---|---|---|
| Vite | `npm run dev -- --host 127.0.0.1 --port 3000 --strictPort` | `http://localhost:3000` |
| Next.js | `npm run dev -- --port 3001` | `http://localhost:3001` |
| FastAPI | `.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001` | `http://localhost:8001/docs` |
| Streamlit | `.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.headless true` | `http://localhost:8501` |
| Static folder | `python -u -m http.server 8080 --bind 127.0.0.1` | `http://localhost:8080` |

Use each Python project's own virtualenv executable. Quote paths containing spaces, e.g. `"C:\My Python\python.exe" -u app.py`. Python output is unbuffered automatically; other tools may need their own unbuffered logging option.

## Project configuration format

Example `POST /api/projects` JSON:

```json
{
  "name": "Expense tracker",
  "description": "Personal expense tracking",
  "folder": "D:\\Projects\\expense-tracker",
  "startup_command": "npm run dev -- --port 3000 --strictPort",
  "url": "http://localhost:3000",
  "type": "React",
  "technologies": "React, TypeScript"
}
```

Only `http://` or `https://` URLs on `localhost`, `127.0.0.1`, or `::1` are accepted. Omit `url` to use `http://localhost:3000` as the preferred address. Missing folders, blank names, invalid URLs, and duplicate launches receive clear validation messages. API validation errors use 422; state conflicts use 409; missing resources use 404. Occupied ports automatically fall back to a free port. Sessions expose `actual_url` and `actual_command`.

## Settings

Edit the root `.env`, then stop and restart the dashboard:

```dotenv
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
AUTO_OPEN_BROWSER=true
STARTUP_TIMEOUT=30
MONITOR_INTERVAL=2
DATA_DIR=data
```

`CHROME_PATH` is optional: common Windows installation paths are checked first, followed by the default browser. Browser failure does not stop a healthy project; a warning is shown in its details. `AUTO_OPEN_BROWSER=false` disables automatic browser opening for both the launcher and projects. **Open app** uses the browser displaying the dashboard.

`MONITOR_INTERVAL` controls stored process samples; frontend polling remains at two seconds for the MVP. `STARTUP_TIMEOUT` can be increased up to 300 seconds. `BACKEND_PORT` and `FRONTEND_URL` are preferred dashboard ports; `launcher.bat` selects alternatives when necessary and passes the actual values to both servers without modifying `.env`. Manual server commands continue to use their configured ports. Relative `DATA_DIR` values resolve from the repository root. The Settings page displays the effective settings; in-app editing is deferred.

## Monitoring, storage, and process ownership

- SQLite lives at `data/launcher.db`, with a bounded SQLAlchemy connection pool, WAL mode, foreign keys, and connection timeouts.
- Projects, sessions, metric samples, and settings tables are initialized automatically. Timestamps are ISO 8601 UTC strings.
- Runtime uses a monotonic clock while active and is stored in whole seconds. The UI displays `HH:MM:SS`. Startup time is included.
- CPU aggregates the managed process tree and divides by logical core count (whole-machine percentage). The first sample is normally zero. RAM is the sum of resident memory, in MB; shared pages can be counted by more than one process.
- Session averages are sample means. “Most used” is the project with the greatest total session duration. “Runtime today” sums each session's overlap with local midnight to now; simultaneous projects add together.
- Separate readers continuously drain stdout and stderr so a full pipe cannot freeze a project. `data/logs/<session_id>.log` rotates at 2 MB with one backup; the UI shows the latest 60 KB of the current file. Deleting a project leaves these diagnostic files on disk for manual cleanup.
- Each Windows launch is assigned a Job Object with kill-on-close, alongside psutil recursive child tracking. Stop terminates descendants, waits briefly, and kills remaining job processes. On Windows, normal psutil termination is forceful; use the project's own shutdown mechanism first if it must flush unsaved application data.
- Shutdown saves sessions and stops children. After an unexpected exit, unfinished sessions become `interrupted`, ending at their last recorded runtime. Reattaching processes and full crash recovery are intentionally outside this MVP. Stored PIDs are never blindly reused to kill a project.
- The application runs commands with your Windows user permissions. Use trusted local commands. Origin/Host checks and loopback binding restrict the local API; there is no multi-user or remote deployment mode.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET / POST | `/api/projects` | List / create projects |
| GET / PUT / DELETE | `/api/projects/{id}` | Details / update / delete |
| POST | `/api/launcher/launch/{project_id}` | Start asynchronously; 202 response |
| POST | `/api/launcher/stop/{session_id}` | Stop and finalize session |
| POST | `/api/launcher/restart/{project_id}` | Stop and create a fresh session |
| GET | `/api/launcher/status/{session_id}` | Session state |
| GET | `/api/monitoring/{session_id}` | Runtime, CPU, RAM, PID |
| GET | `/api/monitoring/{session_id}/logs` | Captured logs |
| GET | `/api/summary` | Counts, runtime, most used, active metrics, system usage |
| GET | `/api/history` | Most recent 200 sessions |
| GET | `/api/settings` | Effective configuration |
| GET | `/api/health` | Dashboard-specific health check |

The frontend fetches projects and summary every two seconds; summary includes all active sessions' metrics in one response. Project details separately poll logs. Launch/stop/restart work runs off the API event loop.

POST, PUT, and DELETE API calls require **`X-Launchpad-Request: 1`**. The frontend and shutdown script send it automatically. This anti-CSRF marker is not an authentication token. Requests from untrusted browser origins or with cross-site Fetch Metadata are rejected. Command-line clients must include the header, for example:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/launcher/launch/1 -Headers @{ 'X-Launchpad-Request' = '1' }
```

Existing databases are migrated additively on startup to store the actual command and URL per session; saved projects and history are retained. Windows PowerShell launches rebuild their native module path rather than inheriting incompatible PowerShell 7 paths.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Backend offline | Start `launcher.bat`; inspect `data/launcher.log`, `data/launcher-servers.log`, and `data/dashboard.log`. |
| Preferred port already in use | The launcher picks another free port and records its actual URL. Unrelated servers are left running. Custom scripts must consume `PORT`/`LAUNCHPAD_PORT` or `{port}`. |
| Folder missing | Edit the project with an existing absolute path. Moving a folder doesn't update its saved configuration. |
| Command exits immediately | Open Details → Process output. Verify installed tools, project dependencies, quoting, and virtualenv paths. |
| No response within 30 seconds | Check the selected URL and logs. A custom script may ignore its assigned port. Use `{port}` or `PORT`, or increase `STARTUP_TIMEOUT` for a slower startup. |
| HTTPS never becomes ready | Local certificates must be trusted by Python. Prefer HTTP for local development if appropriate. |
| Chrome doesn't open | Set `CHROME_PATH`; check `AUTO_OPEN_BROWSER`. Chrome failure appears as a session warning. |
| Windows process job cannot attach | Check permissions and restrictive parent job policies. Launch normally as your user. Unsupported process ownership fails safely. |
| Changes to `.env` aren't applied | Stop both dashboard servers and relaunch; Vite reads the same root `.env`. |
| Second backend refuses to start | Reuse the existing dashboard or stop it. Don't use `--reload` or multiple Uvicorn workers. |
| npm is blocked in PowerShell | Run `npm.cmd` as shown above. |

Do not expose this command-running API to a network. For a data backup, stop the dashboard first, then copy the data directory.

## Validation

Run backend integration tests from the root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests use a temporary SQLite database, real subprocesses, and real loopback HTTP servers. They cover launch/readiness/browser invocation, metrics/logs/history persistence, process-tree cleanup (including an orphaned server), port conflicts without killing unrelated servers, concurrent duplicate starts, timeout, immediate stop, restart, CRUD, failed commands, and local Origin/Host checks. Browser opening is replaced with a spy during these tests.

Build and test the frontend:

```powershell
cd frontend
npm.cmd run build
npm.cmd run test:e2e
```

Playwright uses installed Google Chrome in headless mode and starts isolated backend/frontend servers on ports **8019/5179** with a separate test database. It performs real add → launch → logs → restart → stop → edit → reload → history → delete flows and checks mobile overflow and friendly form errors. Screenshots are written to `test-results` in the repository root. Browser auto-open is disabled during these tests.

Windows 11 was exercised in this workspace. Windows 10 is an intended target but requires separate machine validation. npm/Vite/Streamlit commands depend on the respective project's installed dependencies; no project packages are installed automatically by the dashboard.

## Structure

```text
backend/
  main.py, config.py, requirements.txt
  database/       # SQLite engine, project/session/metric/settings models
  routers/        # projects, launcher, monitoring APIs
  services/       # process manager, Windows jobs, monitoring, browser, validation
  tests/          # Windows subprocess integration tests
frontend/
  src/components/ # sidebar, header, cards, running list, project form
  src/pages/      # overview, details/logs, history, settings
  src/services/   # API client and formatting
  tests/          # Chrome end-to-end tests
scripts/launcher.py
launcher.bat
stop-dashboard.bat
.env.example
```

## Feature roadmap

**Delivered:** project CRUD, launch/stop/restart, HTTP readiness and Chrome opening, process-tree CPU/RAM/PID/runtime, persistent usage history, logs, dashboard summary, search, status/error feedback, settings display, responsive layout, Windows launcher.

**Phase 2:** automatic framework/command detection, coordinated backend/frontend command groups, simple usage charts, saved filters, editable browser/theme/refresh preferences.

**Phase 3:** custom project icons, filtered log viewer, additional startup diagnostics, packaged Windows shortcut/installer.

Excluded: multi-user access, Docker/deployment, advanced analytics, notifications, and crash recovery.

Implementation references: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [psutil process API](https://psutil.readthedocs.io/stable/), [Vite setup](https://vite.dev/guide/).
