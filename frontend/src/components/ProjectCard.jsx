import {
  ArrowUpRight,
  Play,
  Square,
  Terminal,
  Folder,
  ChevronRight,
  Code2,
  Globe,
  Box,
  LoaderCircle,
} from "lucide-react";
import StatusBadge from "./StatusBadge";
import { isActive } from "../services/api";

export function ProjectIcon({ project }) {
  const type = (project.type || "").toLowerCase();
  const Icon = /react|vite|web|next/.test(type)
    ? Globe
    : /python|api|fast/.test(type)
      ? Code2
      : Box;
  return (
    <span
      className={`project-icon ${/python|api|fast/.test(type) ? "blue" : /react|vite|web|next/.test(type) ? "purple" : "amber"}`}
    >
      <Icon size={23} strokeWidth={1.7} />
    </span>
  );
}

export default function ProjectCard({ project, onAction, onDetails, busy }) {
  const active = isActive(project.session);
  return (
    <article className="project-card">
      <div className="project-top">
        <ProjectIcon project={project} />
        <StatusBadge status={project.session?.status || "stopped"} />
      </div>
      <button className="project-name" onClick={() => onDetails(project.id)}>
        {project.name}
        <ArrowUpRight size={16} />
      </button>
      <p className="project-description">
        {project.description || "Your next idea, ready to launch."}
      </p>
      <div className="tags">
        <span>{project.type || "Application"}</span>
        {project.technologies
          .split(",")
          .filter(Boolean)
          .slice(0, 2)
          .map((t, i) => (
            <span key={i}>{t.trim()}</span>
          ))}
      </div>
      <div className="command" title={project.startup_command}>
        <Terminal size={14} />
        <code>{project.startup_command}</code>
      </div>
      <div className="project-folder" title={project.folder}>
        <Folder size={13} />
        <span>{project.folder}</span>
      </div>
      {active && project.session?.actual_url && (
        <a
          className="project-endpoint"
          href={project.session.actual_url}
          target="_blank"
          rel="noreferrer"
        >
          {project.session.actual_url}
          <ArrowUpRight size={13} />
        </a>
      )}
      {project.session?.error && (
        <p className="card-error" title={project.session.error}>
          {project.session.error}
        </p>
      )}
      <div className="project-footer">
        <button
          className={`button ${active ? "stop-button" : "launch-button"}`}
          disabled={busy}
          onClick={() => onAction(active ? "stop" : "launch", project)}
        >
          {busy ? (
            <LoaderCircle size={14} />
          ) : active ? (
            <Square size={13} />
          ) : (
            <Play size={14} fill="currentColor" />
          )}
          {busy ? "Working…" : active ? "Stop project" : "Launch project"}
        </button>
        <button
          className="details-button"
          onClick={() => onDetails(project.id)}
        >
          Details
          <ChevronRight size={15} />
        </button>
      </div>
    </article>
  );
}
