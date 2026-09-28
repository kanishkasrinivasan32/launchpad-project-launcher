import {
  Activity,
  Clock3,
  FolderKanban,
  Trophy,
  Plus,
  ArrowUpRight,
  LayoutGrid,
} from "lucide-react";
import SummaryCard from "../components/SummaryCard";
import RunningProjectsList from "../components/RunningProjectsList";
import ProjectCard from "../components/ProjectCard";
import { isActive, shortDuration } from "../services/api";

export default function Dashboard({
  page,
  projects,
  summary,
  onAction,
  onDetails,
  busy,
  onAdd,
  search,
}) {
  const running = projects.filter((p) => isActive(p.session));
  const filtered = projects.filter((p) =>
    `${p.name} ${p.description} ${p.type} ${p.technologies}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">YOUR IDEAS. ONE WORKSPACE.</p>
          <h1>
            {page === "dashboard"
              ? "Workspace overview"
              : page === "running"
                ? "Running projects"
                : "Your projects"}
            <span className="heading-dot">.</span>
          </h1>
          <p>
            Less setup. More building. Everything you’re working on, right here.
          </p>
        </div>
        <span className="local-badge">
          <span />
          LOCAL ENVIRONMENT
        </span>
      </div>
      {page === "dashboard" && (
        <div className="summary-grid">
          <SummaryCard
            icon={FolderKanban}
            label="Total projects"
            value={summary?.total_projects ?? "—"}
            detail="Ideas in your workspace"
          />
          <SummaryCard
            icon={Activity}
            label="Running now"
            value={summary?.running_count ?? "—"}
            detail={
              summary?.active_count
                ? "Your workspace is in motion"
                : "Ready for your next session"
            }
            tone="green"
          />
          <SummaryCard
            icon={Clock3}
            label="Runtime today"
            value={shortDuration(summary?.runtime_today)}
            detail="Across all project sessions"
            tone="blue"
          />
          <SummaryCard
            icon={Trophy}
            label="Most used project"
            value={summary?.most_used?.name || "Your next favorite"}
            detail={
              summary?.most_used
                ? `${shortDuration(summary.most_used.runtime_seconds)} total runtime`
                : "A little history starts with a launch"
            }
            tone="amber"
          />
        </div>
      )}
      {page !== "projects" && (
        <RunningProjectsList
          projects={
            page === "running"
              ? running.filter((p) => filtered.includes(p))
              : running
          }
          onAction={onAction}
          onDetails={onDetails}
          busy={busy}
        />
      )}
      {page !== "running" && (
        <section className="projects-section">
          <div className="section-heading">
            <h2>
              <LayoutGrid size={18} />
              Your projects <span className="count">{filtered.length}</span>
            </h2>
            <span className="section-note">
              A home for everything you build
            </span>
          </div>
          {filtered.length ? (
            <div className="projects-grid">
              {filtered.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onAction={onAction}
                  onDetails={onDetails}
                  busy={busy[project.id]}
                />
              ))}
              <button className="add-project-card" onClick={onAdd}>
                <span>
                  <Plus size={23} />
                </span>
                <strong>A new idea starts here</strong>
                <p>Add another project to your workspace</p>
              </button>
            </div>
          ) : search ? (
            <div className="empty-state">
              <FolderKanban size={32} />
              <h3>No projects found</h3>
              <p>Try another name or technology.</p>
            </div>
          ) : (
            <div className="first-project">
              <div className="first-project-art">
                <span className="art-window">
                  <span>
                    <i />
                    <i />
                    <i />
                  </span>
                  <code>
                    <b>~/</b> your next big thing
                    <br />
                    <em>›</em> ready to launch<span className="cursor">_</span>
                  </code>
                </span>
                <span className="art-orbit">
                  <ArrowUpRight size={29} />
                </span>
              </div>
              <div>
                <span className="eyebrow">FROM LOCAL FOLDER TO LIFTOFF</span>
                <h2>Give your projects a home.</h2>
                <p>
                  Add a project once. Launch it, follow its vitals, and get back
                  to creating — all from one place.
                </p>
                <button className="button primary" onClick={onAdd}>
                  <Plus size={17} />
                  Add your first project
                </button>
              </div>
            </div>
          )}
        </section>
      )}
      <footer className="content-footer">
        <span>
          <span />
          Built for your local flow.
        </span>
        <span>On your machine. Under your control.</span>
      </footer>
    </>
  );
}
