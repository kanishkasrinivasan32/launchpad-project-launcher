import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, X, CheckCircle2 } from "lucide-react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import AddProjectModal from "./components/AddProjectModal";
import Dashboard from "./pages/Dashboard";
import ProjectDetails from "./pages/ProjectDetails";
import Settings from "./pages/Settings";
import History from "./pages/History";
import { api } from "./services/api";

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [search, setSearch] = useState("");
  const [projects, setProjects] = useState([]);
  const [summary, setSummary] = useState(null);
  const [connected, setConnected] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState({});
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState(null);
  const [revision, setRevision] = useState(0);
  const requestId = useRef(0);
  const busyIds = useRef(new Set());
  const refresh = useCallback(async () => {
    const id = ++requestId.current;
    try {
      const [list, stats] = await Promise.all([
        api("/projects"),
        api("/summary"),
      ]);
      if (id !== requestId.current) return;
      const sessions = new Map(stats.sessions.map((s) => [s.project_id, s]));
      setProjects(
        list.map((p) => ({ ...p, session: sessions.get(p.id) || p.session })),
      );
      setSummary(stats);
      setConnected(true);
      setLoadError("");
    } catch (e) {
      if (id === requestId.current) {
        setConnected(false);
        setLoadError(e.message);
      }
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    let cancelled = false;
    let timer;
    const tick = async () => {
      await refresh();
      if (!cancelled) timer = setTimeout(tick, 2000);
    };
    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      requestId.current++;
    };
  }, [refresh]);
  useEffect(() => {
    if (notice?.kind !== "success") return;
    const timer = setTimeout(() => setNotice(null), 5000);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    const shortcut = (e) => {
      if (
        e.key === "/" &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(
          document.activeElement.tagName,
        ) &&
        !modal
      ) {
        e.preventDefault();
        document.querySelector('[aria-label="Search projects"]')?.focus();
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, [modal]);
  async function action(kind, project) {
    if (busyIds.current.has(project.id)) return;
    busyIds.current.add(project.id);
    setBusy((b) => ({ ...b, [project.id]: true }));
    try {
      const id = kind === "stop" ? project.session.id : project.id;
      await api(`/launcher/${kind}/${id}`, { method: "POST" });
      setNotice({
        kind: "success",
        text:
          kind === "stop"
            ? `${project.name} stopped.`
            : `${project.name} is starting. Your browser will open when it’s ready.`,
      });
      setRevision((r) => r + 1);
      await refresh();
    } catch (e) {
      setNotice({ kind: "error", text: e.message });
    } finally {
      busyIds.current.delete(project.id);
      setBusy((b) => ({ ...b, [project.id]: false }));
    }
  }
  async function remove(project) {
    if (
      !window.confirm(
        `Delete “${project.name}” and its usage history? Your project files will stay on disk.`,
      )
    )
      return;
    try {
      await api(`/projects/${project.id}`, { method: "DELETE" });
      setPage("dashboard");
      await refresh();
      setNotice({
        kind: "success",
        text: "Project removed from your workspace.",
      });
    } catch (e) {
      setNotice({ kind: "error", text: e.message });
    }
  }
  function details(id) {
    setSelected(id);
    setPage("details");
  }
  const project = projects.find((p) => p.id === selected);
  return (
    <div className="app-shell">
      <Sidebar
        page={page}
        setPage={setPage}
        summary={summary}
        connected={connected}
      />
      <div className="main-shell">
        <Header
          page={page}
          search={search}
          setSearch={setSearch}
          onAdd={() => setModal({})}
          onRefresh={() => {
            setLoading(true);
            setRevision((r) => r + 1);
            refresh();
          }}
          refreshing={loading}
        />
        <main>
          {loadError && (
            <div className="error-banner" role="alert">
              <AlertCircle size={18} />
              {loadError}
              <button onClick={refresh}>Retry</button>
            </div>
          )}
          {notice && (
            <div
              className={`toast ${notice.kind}`}
              role={notice.kind === "error" ? "alert" : "status"}
            >
              {notice.kind === "error" ? (
                <AlertCircle size={18} />
              ) : (
                <CheckCircle2 size={18} />
              )}
              <span>{notice.text}</span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice(null)}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {loading && !summary ? (
            <div className="empty-state">
              <div className="loading-dots">•••</div>
              <h3>Opening your workspace…</h3>
            </div>
          ) : page === "settings" ? (
            <Settings />
          ) : page === "history" ? (
            <History revision={revision} search={search} onDetails={details} />
          ) : page === "details" && project ? (
            <ProjectDetails
              project={project}
              onBack={() => setPage("dashboard")}
              onEdit={setModal}
              onDelete={remove}
              onAction={action}
              busy={busy[project.id]}
              revision={revision}
            />
          ) : (
            <Dashboard
              page={page}
              projects={projects}
              summary={summary}
              search={search}
              onAction={action}
              onDetails={details}
              busy={busy}
              onAdd={() => setModal({})}
            />
          )}
        </main>
      </div>
      {modal && (
        <AddProjectModal
          project={modal.id ? modal : null}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            setNotice({
              kind: "success",
              text: modal.id
                ? "Project updated."
                : "Project added. Ready for liftoff.",
            });
            refresh();
          }}
        />
      )}
    </div>
  );
}
