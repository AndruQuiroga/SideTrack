export interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
}

export function renderMetricCard(props: MetricCardProps): string {
  const tone = props.tone ?? 'default';
  const trendCopy = props.trend ? `<span class="metric-trend">${props.trend}</span>` : '';
  return `
<article class="metric-card metric-${tone}">
  <p class="metric-title">${props.title}</p>
  <p class="metric-value">${props.value}</p>
  <p class="metric-subtitle">${props.subtitle ?? ''}</p>
  ${trendCopy}
</article>
`.trim();
}

export function renderMetricGrid(cards: MetricCardProps[]): string {
  if (!cards.length) {
    return '<p class="state state-empty">No metrics available yet.</p>';
  }

  const body = cards.map((card) => renderMetricCard(card)).join('\n');
  return `<section class="metric-grid">${body}</section>`;
}
