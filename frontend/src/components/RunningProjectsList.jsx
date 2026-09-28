import { Activity, ExternalLink, RotateCw, Square } from "lucide-react";
import { duration } from "../services/api";
import { ProjectIcon } from "./ProjectCard";
import StatusBadge from "./StatusBadge";

export default function RunningProjectsList({
  projects,
  onAction,
  onDetails,
  busy,
}) {
  return (
    <section className="running-section">
      <div className="section-heading">
        <h2>
          <Activity size={18} />
          Running now <span className="count">{projects.length}</span>
        </h2>
        <span className="live-label">
          <i />
          LIVE · UPDATES EVERY 2S
        </span>
      </div>
      {projects.length ? (
        <div className="running-table">
          <div className="running-table-head">
            <span>PROJECT</span>
            <span>RUNTIME</span>
            <span>CPU</span>
            <span>MEMORY</span>
            <span>ACTIONS</span>
          </div>
          {projects.map((project) => (
            <div className="running-row" key={project.id}>
              <div className="running-project">
                <ProjectIcon project={project} />
                <div>
                  <button onClick={() => onDetails(project.id)}>
                    {project.name}
                  </button>
                  <span>
                    <StatusBadge status={project.session.status} />
                    <small>PID {project.session.pid}</small>
                    <small>
                      :{new URL(project.session.actual_url || project.url).port}
                    </small>
                  </span>
                </div>
              </div>
              <span className="tabular-nums runtime">
                {duration(project.session.runtime_seconds)}
              </span>
              <span className="metric">
                {project.session.cpu_percent?.toFixed(1) || "0.0"}
                <small>%</small>
              </span>
              <span className="metric">
                {project.session.ram_mb?.toFixed(0) || "0"}
                <small> MB</small>
              </span>
              <div className="row-actions">
                <a
                  className="icon-button"
                  href={project.session?.actual_url || project.url}
                  target="_blank"
                  rel="noreferrer"
                  title={`Open ${project.name}`}
                  aria-label={`Open ${project.name}`}
                >
                  <ExternalLink size={16} />
                </a>
                <button
                  className="icon-button"
                  disabled={busy[project.id]}
                  onClick={() => onAction("restart", project)}
                  title={`Restart ${project.name}`}
                  aria-label={`Restart ${project.name}`}
                >
                  <RotateCw size={16} />
                </button>
                <button
                  className="icon-button stop-icon"
                  disabled={busy[project.id]}
                  onClick={() => onAction("stop", project)}
                  title={`Stop ${project.name}`}
                  aria-label={`Stop ${project.name}`}
                >
                  <Square size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="running-empty">
          <span className="empty-activity">
            <Activity size={21} />
          </span>
          <div>
            <strong>A little quiet here</strong>
            <p>Launch a project below and watch its vitals here.</p>
          </div>
          <span className="ready-chip">Ready when you are</span>
        </div>
      )}
    </section>
  );
}
