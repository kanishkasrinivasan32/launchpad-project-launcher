export default function StatusBadge({ status = "stopped" }) {
  return (
    <span className={`status status-${status}`}>
      <span />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
