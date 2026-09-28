import { useEffect, useState } from "react";
import { Monitor, SlidersHorizontal } from "lucide-react";
import { api } from "../services/api";

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/settings")
      .then(setSettings)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">MAKE YOURSELF AT HOME</p>
          <h1>
            Workspace settings<span className="heading-dot">.</span>
          </h1>
          <p>Your local environment, at a glance.</p>
        </div>
      </div>
      {error && <p className="error-banner">{error}</p>}
      <section className="panel settings-panel">
        <h2>
          <SlidersHorizontal size={18} />
          Launch preferences
        </h2>
        <p>
          Configure these values in the root <code>.env</code> file, then
          restart the dashboard.
        </p>
        <dl className="settings-list">
          <div>
            <dt>Preferred browser</dt>
            <dd>{settings?.browser || "—"}</dd>
          </div>
          <div>
            <dt>Open browser after launch</dt>
            <dd>
              {settings
                ? settings.auto_open_browser
                  ? "Enabled"
                  : "Disabled"
                : "—"}
            </dd>
          </div>
          <div>
            <dt>Readiness timeout</dt>
            <dd>{settings?.startup_timeout ?? "—"} seconds</dd>
          </div>
          <div>
            <dt>Monitoring interval</dt>
            <dd>{settings?.monitor_interval ?? "—"} seconds</dd>
          </div>
          <div>
            <dt>Backend port</dt>
            <dd>{settings?.backend_port ?? "—"}</dd>
          </div>
          <div>
            <dt>Data directory</dt>
            <dd>{settings?.data_dir || "—"}</dd>
          </div>
        </dl>
      </section>
      <section className="panel settings-panel">
        <h2>
          <Monitor size={18} />
          About this workspace
        </h2>
        <p>
          Launchpad runs locally and stores projects, usage history, and logs on
          your machine. Closing a browser tab leaves projects running. Stop
          projects here or shut down the backend to end their sessions.
        </p>
        <p>
          Theme customization and editable preferences are planned for the next
          iteration.
        </p>
      </section>
    </>
  );
}
