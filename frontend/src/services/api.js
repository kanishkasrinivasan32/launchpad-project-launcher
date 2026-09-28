export async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Launchpad-Request": "1",
        ...options.headers,
      },
      signal: options.signal || AbortSignal.timeout(15000),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(
      "Cannot reach the backend. Check that the dashboard launcher is running.",
    );
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail
          .map(
            (e) =>
              `${e.loc?.at(-1) || "Field"}: ${e.msg.replace("Value error, ", "")}`,
          )
          .join(" ")
      : data.detail;
    throw new Error(detail || "Something went wrong. Please try again.");
  }
  return data;
}

export const isActive = (session) =>
  ["starting", "running", "stopping"].includes(session?.status);
export function duration(seconds = 0) {
  const total = Math.max(0, Math.floor(seconds));
  return [Math.floor(total / 3600), Math.floor(total / 60) % 60, total % 60]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}
export function shortDuration(seconds = 0) {
  return `${Math.floor(seconds / 3600)}h ${Math.floor(seconds / 60) % 60}m`;
}
export function dateTime(value) {
  return value ? new Date(value).toLocaleString() : "—";
}
