export interface ChartDataPoint {
  label: string;
  value: number;
  accent?: boolean;
}

export interface ChartOptions {
  title: string;
  unit?: string;
  cta?: string;
}

export function renderBarChart(data: ChartDataPoint[], options: ChartOptions): string {
  if (!data.length) {
    return `<section class="chart chart-empty"><h3>${options.title}</h3><p class="state state-empty">No data yet.</p></section>`;
  }

  const maxValue = Math.max(...data.map((point) => point.value), 1);
  const bars = data
    .map((point) => {
      const height = Math.max(6, Math.round((point.value / maxValue) * 100));
      const accentClass = point.accent ? 'chart-bar-accent' : '';
      return `
      <div class="chart-bar ${accentClass}" style="height:${height}%" aria-label="${point.label} ${point.value}${
        options.unit ? ' ' + options.unit : ''
      }">
        <span class="chart-bar-value">${point.value}${options.unit ? ` ${options.unit}` : ''}</span>
        <span class="chart-bar-label">${point.label}</span>
      </div>`;
    })
    .join('\n');

  const ctaCopy = options.cta ? `<p class="chart-cta">${options.cta}</p>` : '';
  return `
<section class="chart chart-bar">
  <h3>${options.title}</h3>
  <div class="chart-bar-grid">${bars}</div>
  ${ctaCopy}
</section>
`.trim();
}

export function renderLineChart(data: ChartDataPoint[], options: ChartOptions): string {
  if (!data.length) {
    return `<section class="chart chart-empty"><h3>${options.title}</h3><p class="state state-empty">No data yet.</p></section>`;
  }

  const maxValue = Math.max(...data.map((point) => point.value), 1);
  const points = data.map((point, index) => {
    const x = (index / Math.max(data.length - 1, 1)) * 100;
    const y = 100 - Math.round((point.value / maxValue) * 100);
    return `${x},${y}`;
  });

  const labels = data
    .map((point) => `<span class="chart-line-label"><strong>${point.label}:</strong> ${point.value}${options.unit ?? ''}</span>`)
    .join('');

  return `
<section class="chart chart-line">
  <h3>${options.title}</h3>
  <div class="chart-line-graph">
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="${options.title}">
      <polyline fill="none" stroke="currentColor" stroke-width="2" points="${points.join(' ')}" />
    </svg>
  </div>
  <div class="chart-line-legend">${labels}</div>
</section>
`.trim();
}
