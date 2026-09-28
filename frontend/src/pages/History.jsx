import { useEffect, useState } from "react";
import { History as HistoryIcon } from "lucide-react";
import { api, duration, dateTime } from "../services/api";
import StatusBadge from "../components/StatusBadge";

export default function History({ revision, search, onDetails }) {
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    let timer;
    const controller = new AbortController();
    async function load() {
      try {
        const data = await api("/history", { signal: controller.signal });
        if (!cancelled) {
          setSessions(data);
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
  }, [revision]);
  const filtered = sessions.filter((s) =>
    s.project_name.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">A LITTLE PROGRESS, EVERY DAY</p>
          <h1>
            Session history<span className="heading-dot">.</span>
          </h1>
          <p>Your latest 200 sessions. Every launch is part of the story.</p>
        </div>
      </div>
      {error && <p className="error-banner">{error}</p>}
      <section className="panel">
        <div className="section-heading">
          <h2>
            <HistoryIcon size={18} />
            Recent activity
          </h2>
          <span className="count">{filtered.length}</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Started</th>
                <th>Status</th>
                <th>Runtime</th>
                <th>Avg. CPU</th>
                <th>Avg. RAM</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td>
                    <button
                      className="table-link"
                      onClick={() => onDetails(s.project_id)}
                    >
                      {s.project_name}
                    </button>
                  </td>
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
          {!filtered.length && (
            <div className="empty-state">
              <HistoryIcon size={30} />
              <h3>A fresh start</h3>
              <p>Your project sessions will appear here.</p>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
