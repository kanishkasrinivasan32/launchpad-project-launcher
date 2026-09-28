import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Edit3,
  Trash2,
  ExternalLink,
  Play,
  Square,
  RotateCw,
  Terminal,
} from "lucide-react";
import { api, duration, dateTime, isActive } from "../services/api";
import StatusBadge from "../components/StatusBadge";

export default function ProjectDetails({
  project,
  onBack,
  onEdit,
  onDelete,
  onAction,
  busy,
  revision,
}) {
  const [detail, setDetail] = useState(null);
  const [selected, setSelected] = useState("latest");
  const [logs, setLogs] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    let timer;
    const controller = new AbortController();
    async function load() {
      try {
        const data = await api(`/projects/${project.id}`, {
          signal: controller.signal,
        });
        const sessionId =
          selected === "latest" ? data.sessions[0]?.id : selected;
        const output = sessionId
          ? await api(`/monitoring/${sessionId}/logs`, {
              signal: controller.signal,
            })
          : null;
        if (!cancelled) {
          setDetail(data);
          setLogs(
            output?.content ||
              "No output yet. Launch the project to see its logs here.",
          );
          setError("");
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) timer = setTimeout(load, 2000);
      }
    }
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, [project.id, selected, revision]);
  const active = isActive(project.session);
  return (
    <>
      <button className="back-button" onClick={onBack}>
        <ArrowLeft size={16} />
        Back to workspace
      </button>
      <div className="detail-heading">
        <div>
          <p className="eyebrow">PROJECT DETAILS</p>
          <h1>{project.name}</h1>
          <p>
            {project.description ||
              "Your local project configuration and session activity."}
          </p>
        </div>
        <StatusBadge status={project.session?.status || "stopped"} />
      </div>
      <div className="detail-actions">
        <button
          className="button primary"
          disabled={busy}
          onClick={() => onAction(active ? "stop" : "launch", project)}
        >
          {active ? <Square size={15} /> : <Play size={15} />}
          {busy ? "Working…" : active ? "Stop project" : "Launch project"}
        </button>
        <button
          className="button secondary"
          disabled={busy}
          onClick={() => onAction("restart", project)}
        >
          <RotateCw size={15} />
          Restart
        </button>
        <a
          className="button secondary"
          href={project.session?.actual_url || project.url}
          target="_blank"
          rel="noreferrer"
        >
          <ExternalLink size={15} />
          Open app
        </a>
        <button
          className="button secondary"
          disabled={active || busy}
          onClick={() => onEdit(project)}
        >
          <Edit3 size={15} />
          Edit
        </button>
        <button
          className="button danger"
          disabled={active || busy}
          onClick={() => onDelete(project)}
        >
          <Trash2 size={15} />
          Delete
        </button>
      </div>
      {project.session?.error && (
        <p className="error-banner" role="alert">
          {project.session.error}
        </p>
      )}
      {project.session?.browser_warning && (
        <p className="warning-banner">{project.session.browser_warning}</p>
      )}
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}
      <div className="details-grid">
        <section className="panel">
          <h2>Configuration</h2>
          <dl className="config-list">
            <dt>Working directory</dt>
            <dd>{project.folder}</dd>
            <dt>Startup command</dt>
            <dd>
              <code>{project.startup_command}</code>
            </dd>
            <dt>Preferred URL · automatic port</dt>
            <dd>{project.url}</dd>
            {project.session?.actual_url && (
              <>
                <dt>Session URL</dt>
                <dd>{project.session.actual_url}</dd>
                <dt>Session command</dt>
                <dd>
                  <code>{project.session.actual_command}</code>
                </dd>
              </>
            )}
            <dt>Type</dt>
            <dd>{project.type}</dd>
          </dl>
        </section>
        <section className="panel">
          <h2>Current session</h2>
          <dl className="session-vitals">
            <div>
              <dt>Runtime</dt>
              <dd>
                {duration(
                  project.session?.runtime_seconds ??
                    project.session?.total_runtime,
                )}
              </dd>
            </div>
            <div>
              <dt>Process ID</dt>
              <dd>{project.session?.pid || "—"}</dd>
            </div>
            <div>
              <dt>CPU</dt>
              <dd>
                {project.session?.cpu_percent?.toFixed(1) || "0.0"}
                <small>%</small>
              </dd>
            </div>
            <div>
              <dt>Memory</dt>
              <dd>
                {project.session?.ram_mb?.toFixed(0) || "0"}
                <small> MB</small>
              </dd>
            </div>
          </dl>
        </section>
      </div>
      <section className="logs-panel">
        <div className="section-heading">
          <h2>
            <Terminal size={17} />
            Process output
          </h2>
          <select
            aria-label="Log session"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="latest">Latest session · live</option>
            {detail?.sessions.map((s) => (
              <option value={s.id} key={s.id}>
                #{s.id} · {dateTime(s.started_at)}
              </option>
            ))}
          </select>
        </div>
        <pre className="logs" aria-label="Process logs">
          {logs}
        </pre>
        <p className="log-note">
          stdout + stderr · latest 60 KB · updates every 2 seconds
        </p>
      </section>
      <section className="panel session-history">
        <h2>Recent sessions</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Started</th>
                <th>Status</th>
                <th>Runtime</th>
                <th>Avg. CPU</th>
                <th>Avg. RAM</th>
              </tr>
            </thead>
            <tbody>
              {detail?.sessions.map((s) => (
                <tr key={s.id}>
                  <td>{dateTime(s.started_at)}</td>
                  <td>
                    <StatusBadge status={s.status} />
                  </td>
                  <td>{duration(s.total_runtime)}</td>
                  <td>{s.avg_cpu.toFixed(1)}%</td>
                  <td>{s.avg_ram.toFixed(0)} MB</td>
                </tr>
              ))}
            </tbody>
          </table>
          {detail?.sessions.length === 0 && (
            <p className="table-empty">No sessions yet.</p>
          )}
        </div>
      </section>
    </>
  );
}
