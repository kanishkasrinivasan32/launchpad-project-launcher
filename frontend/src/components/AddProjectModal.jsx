import { useEffect, useRef, useState } from "react";
import { X, FolderPlus, Terminal, ArrowRight } from "lucide-react";
import { api } from "../services/api";

const empty = {
  name: "",
  description: "",
  folder: "",
  startup_command: "",
  url: "http://localhost:3000",
  type: "Application",
  technologies: "",
};
export default function AddProjectModal({ project, onClose, onSaved }) {
  const [form, setForm] = useState(
    project
      ? Object.fromEntries(
          Object.keys(empty).map((key) => [key, project[key] || empty[key]]),
        )
      : empty,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const dialog = useRef(null);
  useEffect(() => {
    const el = dialog.current;
    el.showModal();
    return () => el.close();
  }, []);
  const field = (key) => ({
    value: form[key],
    onChange: (e) => setForm({ ...form, [key]: e.target.value }),
  });
  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api(project ? `/projects/${project.id}` : "/projects", {
        method: project ? "PUT" : "POST",
        body: JSON.stringify({ ...form, url: form.url.trim() || empty.url }),
      });
      onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="project-modal"
      onCancel={(e) => {
        e.preventDefault();
        if (!saving) onClose();
      }}
      onClick={(e) => {
        if (e.target === dialog.current && !saving) onClose();
      }}
    >
      <div className="modal-heading">
        <span className="modal-icon">
          <FolderPlus size={23} />
        </span>
        <button
          className="icon-button"
          onClick={onClose}
          disabled={saving}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>
      </div>
      <h2>{project ? "Edit project" : "Make room for your next idea."}</h2>
      <p className="modal-intro">
        Connect a local project. We’ll handle the launch.
      </p>
      <form onSubmit={submit}>
        <label>
          Project name
          <input
            required
            maxLength={120}
            autoFocus
            placeholder="e.g. Expense tracker"
            {...field("name")}
          />
        </label>
        <label>
          Description <span>Optional</span>
          <input
            maxLength={2000}
            placeholder="A few words about what you’re building"
            {...field("description")}
          />
        </label>
        <label>
          Project folder
          <input
            required
            placeholder="D:\Projects\expense-tracker"
            {...field("folder")}
          />
          <small>Full path to the folder where the command should run.</small>
        </label>
        <label>
          Startup command
          <div className="input-with-icon">
            <Terminal size={16} />
            <input
              required
              placeholder="npm run dev"
              {...field("startup_command")}
            />
          </div>
          <small>
            Ports are chosen automatically. For a custom command, use {"{port}"}{" "}
            in its port argument or read the PORT environment variable.
          </small>
        </label>
        <div className="form-row">
          <label>
            Localhost URL <span>Optional · preferred address</span>
            <input
              type="url"
              placeholder="http://localhost:3000"
              {...field("url")}
            />
            <small>
              We check for a free port at launch and update the running URL
              automatically.
            </small>
          </label>
          <label>
            Project type
            <select {...field("type")}>
              {[
                "Application",
                "React",
                "Vite",
                "Next.js",
                "Python",
                "FastAPI",
                "Streamlit",
                "Node.js",
                "Other",
              ].map((type) => (
                <option key={type}>{type}</option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Technologies <span>Optional · comma-separated</span>
          <input placeholder="React, TypeScript" {...field("technologies")} />
        </label>
        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}
        <div className="modal-footer">
          <button
            type="button"
            className="button secondary"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button className="button primary" disabled={saving}>
            {saving ? "Saving…" : project ? "Save changes" : "Add project"}
            <ArrowRight size={16} />
          </button>
        </div>
      </form>
    </dialog>
  );
}
