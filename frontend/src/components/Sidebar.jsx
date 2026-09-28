import {
  LayoutDashboard,
  FolderKanban,
  Activity,
  History,
  Settings,
  Zap,
  ArrowUpRight,
} from "lucide-react";

const navigation = [
  ["dashboard", "Overview", LayoutDashboard],
  ["projects", "All projects", FolderKanban],
  ["running", "Running", Activity],
  ["history", "Session history", History],
];

export default function Sidebar({ page, setPage, summary, connected }) {
  return (
    <aside className="sidebar">
      <a
        className="brand"
        href="#dashboard"
        onClick={() => setPage("dashboard")}
      >
        <span className="brand-icon">
          <Zap size={23} fill="currentColor" />
        </span>
        <span>
          launchpad<span className="brand-sub">YOUR LOCAL WORKSPACE</span>
        </span>
      </a>
      <div className="workspace">
        <span className="workspace-avatar">L</span>
        <div>
          Local workspace<small>Personal environment</small>
        </div>
        <span className="workspace-dot" />
      </div>
      <p className="nav-label">WORKSPACE</p>
      <nav aria-label="Main navigation">
        {navigation.map(([id, label, Icon]) => (
          <button
            key={id}
            className={`nav-item ${page === id ? "selected" : ""}`}
            onClick={() => setPage(id)}
          >
            <Icon size={18} />
            <span>{label}</span>
            {id === "running" && <b>{summary?.active_count || 0}</b>}
          </button>
        ))}
        <button
          className={`nav-item mobile-settings ${page === "settings" ? "selected" : ""}`}
          onClick={() => setPage("settings")}
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>
      </nav>
      <div className="sidebar-bottom">
        <button
          className={`nav-item ${page === "settings" ? "selected" : ""}`}
          onClick={() => setPage("settings")}
        >
          <Settings size={18} />
          Settings
        </button>
        <div className="system-card">
          <div className="system-title">
            <span className={`connection-dot ${connected ? "" : "offline"}`} />
            {connected ? "System online" : "Backend offline"}
            <ArrowUpRight size={14} />
          </div>
          <div className="system-row">
            <span>CPU usage</span>
            <b>{summary?.system?.cpu_percent?.toFixed(0) ?? "—"}%</b>
          </div>
          <div className="meter">
            <i style={{ width: `${summary?.system?.cpu_percent || 0}%` }} />
          </div>
          <div className="system-row">
            <span>Memory</span>
            <b>{summary?.system?.ram_percent?.toFixed(0) ?? "—"}%</b>
          </div>
          <div className="meter memory">
            <i style={{ width: `${summary?.system?.ram_percent || 0}%` }} />
          </div>
          <p>Everything runs on your machine.</p>
        </div>
        <div className="sidebar-footer">
          <span className="tiny-logo">L</span>Launchpad <span>v1.0</span>
        </div>
      </div>
    </aside>
  );
}
