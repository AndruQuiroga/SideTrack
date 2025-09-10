'use client';
import Plot from 'react-plotly.js';

export type FlowEdge = {
  source: string;
  target: string;
  prob: number;
  lift?: number | null;
};

export default function FlowChord({
  edges,
  onSelect,
}: {
  edges: FlowEdge[];
  onSelect?: (edge: { source: string; target: string }) => void;
}) {
  const nodes = Array.from(new Set(edges.flatMap((e) => [e.source, e.target])));
  const index: Record<string, number> = Object.fromEntries(
    nodes.map((n, i) => [n, i]),
  );
  const sources = edges.map((e) => index[e.source]);
  const targets = edges.map((e) => index[e.target]);
  const values = edges.map((e) => e.prob);
  const colors = edges.map((e) =>
    e.lift && e.lift > 1 ? 'rgba(16,185,129,0.8)' : 'rgba(156,163,175,0.4)',
  );

  return (
    <Plot
      data={[
        {
          type: 'sankey',
          orientation: 'h',
          arrangement: 'fixed',
          node: { label: nodes },
          link: {
            source: sources,
            target: targets,
            value: values,
            color: colors,
            hovertemplate:
              '%{source.label} → %{target.label}<br>p(next|current)=%{value:.2f}<extra></extra>',
          },
        },
      ]}
      layout={{
        margin: { l: 10, r: 10, t: 10, b: 10 },
        font: { size: 10 },
      }}
      style={{ width: '100%', height: '100%' }}
      config={{ displayModeBar: false }}
      onClick={(e) => {
        const idx = e.points?.[0]?.pointIndex;
        if (idx != null) {
          const edge = edges[idx];
          onSelect?.({ source: edge.source, target: edge.target });
        }
      }}
    />
  );
}
