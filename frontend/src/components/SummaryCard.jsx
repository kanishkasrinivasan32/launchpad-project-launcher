export default function SummaryCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = "purple",
}) {
  return (
    <div className="summary-card">
      <div className="summary-top">
        <span>{label}</span>
        <span className={`summary-icon ${tone}`}>
          <Icon size={17} />
        </span>
      </div>
      <strong className="summary-value" title={String(value)}>
        {value}
      </strong>
      <span className="summary-detail">{detail}</span>
    </div>
  );
}
