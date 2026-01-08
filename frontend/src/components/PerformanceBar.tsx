interface PerformanceBarProps {
  label: string;
  value: number;
  maxValue: number;
  unit?: string;
  color?: string;
  icon?: string;
}

export function PerformanceBar({
  label,
  value,
  maxValue,
  unit = '',
  color = '#3298dc',
  icon = '',
}: PerformanceBarProps) {
  // Ensure value and maxValue are valid numbers
  const safeValue = typeof value === 'number' && !isNaN(value) ? value : 0;
  const safeMaxValue = typeof maxValue === 'number' && !isNaN(maxValue) ? maxValue : 0;
  const percentage = safeMaxValue > 0 ? Math.min((safeValue / safeMaxValue) * 100, 100) : 0;

  return (
    <div className="performance-bar mb-2">
      <div className="is-flex is-justify-content-space-between is-align-items-center mb-1">
        <span className="is-size-7 has-text-grey">
          {icon && <span className="mr-1">{icon}</span>}
          {label}
        </span>
        <span className="is-size-7 has-text-weight-semibold">
          {safeValue.toLocaleString()}{unit}
        </span>
      </div>
      <div className="bar-container">
        <div
          className="bar-fill"
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}
