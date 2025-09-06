'use client';
import { XYChart, Tooltip, AnimatedAxis, AnimatedGrid, AnimatedScatterSeries } from '@visx/xychart';
import { motion } from 'framer-motion';

type Point = { week: string; x: number; y: number; r?: number };
type Arrow = { from: Point; to: Point };

export type TrajectoryData = { points: Point[]; arrows: Arrow[] };

const accessors = {
  xAccessor: (d: Point) => d.x,
  yAccessor: (d: Point) => d.y,
};

export default function TrajectoryBubble({ data }: { data: TrajectoryData }) {
  const points = data.points ?? [];
  const series = [{ id: 'weeks', data: points }];
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="h-[380px] w-full rounded-lg glass p-3">
        <XYChart
          height={340}
          xScale={{ type: 'linear', domain: [0, 1] }}
          yScale={{ type: 'linear', domain: [0, 1] }}
        >
          <AnimatedGrid rows columns numTicks={4} />
          <AnimatedAxis orientation="bottom" numTicks={4} />
          <AnimatedAxis orientation="left" numTicks={4} />
          <AnimatedScatterSeries
            key="weeks"
            dataKey="weeks"
            data={series[0].data}
            xAccessor={accessors.xAccessor}
            yAccessor={accessors.yAccessor}
            sizeAccessor={(d) => (d.r ? d.r : 40)}
            colorAccessor={() => '#2FE08B'}
          />
          <Tooltip<Point>
            snapTooltipToDatumX
            snapTooltipToDatumY
            showVerticalCrosshair
            showHorizontalCrosshair
            renderTooltip={({ tooltipData }) => {
              const d = tooltipData?.nearestDatum?.datum as Point | undefined;
              if (!d) return null;
              return (
                <div className="rounded-md bg-black/80 p-2 text-xs text-white">
                  <div className="font-medium">Week {d.week}</div>
                  <div>x: {d.x.toFixed(3)}</div>
                  <div>y: {d.y.toFixed(3)}</div>
                </div>
              );
            }}
          />
        </XYChart>
      </div>
    </motion.div>
  );
}
