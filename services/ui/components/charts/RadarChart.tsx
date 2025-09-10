'use client';

import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { motion } from 'framer-motion';
import { useInspector } from '../../hooks/useInspector';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

type RadarChartProps = {
  axes: Record<string, number>;
  baseline: Record<string, number>;
};

export default function RadarChart({ axes, baseline }: RadarChartProps) {
  const labels = Object.keys(axes);
  const { inspect } = useInspector();
  const data = {
    labels,
    datasets: [
      {
        label: 'Week',
        data: labels.map((l) => axes[l]),
        backgroundColor: 'rgba(47,224,139,0.2)',
        borderColor: '#2FE08B',
        pointBackgroundColor: '#2FE08B',
      },
      {
        label: 'Baseline',
        data: labels.map((l) => baseline[l]),
        backgroundColor: 'rgba(57,210,255,0.2)',
        borderColor: '#39D2FF',
        pointBackgroundColor: '#39D2FF',
      },
    ],
  };

  const options = {
    responsive: true,
    animation: { duration: 500 },
    onClick: (_: any, elements: any) => {
      if (elements && elements.length) {
        const idx = elements[0].index;
        const label = labels[idx];
        inspect({ type: 'radar', axis: label, value: axes[label] });
      }
    },
    plugins: {
      tooltip: { enabled: true },
      legend: { position: 'top' as const },
    },
    scales: {
      r: {
        beginAtZero: true,
        ticks: { display: false },
        grid: { color: 'rgba(0,0,0,0.1)' },
        angleLines: { color: 'rgba(0,0,0,0.1)' },
      },
    },
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full aspect-[4/3]"
    >
      {/* @ts-ignore */}
      <Radar data={data} options={options} />
    </motion.div>
  );
}

