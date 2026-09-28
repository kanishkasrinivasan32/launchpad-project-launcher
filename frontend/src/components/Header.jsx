import { Search, Plus, RefreshCw, ChevronRight } from "lucide-react";

const labels = {
  dashboard: "Overview",
  projects: "All projects",
  running: "Running projects",
  history: "Session history",
  settings: "Settings",
  details: "Project details",
};
export default function Header({
  page,
  search,
  setSearch,
  onAdd,
  onRefresh,
  refreshing,
}) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        Workspace
        <ChevronRight size={14} />
        <strong>{labels[page]}</strong>
      </div>
      <div className="header-actions">
        <label className="search">
          <Search size={16} />
          <input
            aria-label="Search projects"
            placeholder="Search projects…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <kbd>/</kbd>
        </label>
        <button
          className="icon-button"
          title="Refresh dashboard"
          aria-label="Refresh dashboard"
          onClick={onRefresh}
          disabled={refreshing}
        >
          <RefreshCw size={17} />
        </button>
        <button className="button primary" onClick={onAdd}>
          <Plus size={17} />
          Add project
        </button>
      </div>
    </header>
  );
}
