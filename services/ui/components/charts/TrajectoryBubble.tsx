'use client';
import { scaleLinear, scaleOrdinal } from '@visx/scale';
import { AxisBottom, AxisLeft } from '@visx/axis';
import { GridColumns, GridRows } from '@visx/grid';
import { Group } from '@visx/group';
import { Zoom } from '@visx/zoom';
import { localPoint } from '@visx/event';
import { useTooltip, TooltipWithBounds } from '@visx/tooltip';
import useMeasure from 'react-use-measure';
import { motion } from 'framer-motion';
import { useMemo, useState } from 'react';
import { LegendOrdinal } from '@visx/legend';

type Point = { week: string; x: number; y: number; r?: number };
type Arrow = { from: Point; to: Point };

export type TrajectoryData = { points: Point[]; arrows: Arrow[] };

export default function TrajectoryBubble({ data }: { data: TrajectoryData }) {
  const { points = [], arrows = [] } = data;
  const [ref, bounds] = useMeasure();
  const width = bounds.width || 800;
  const height = bounds.height || 340;
  const margin = { top: 10, right: 10, bottom: 40, left: 40 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const color = '#2FE08B';

  const xScale = useMemo(
    () => scaleLinear<number>({ domain: [0, 1], range: [0, innerWidth] }),
    [innerWidth],
  );
  const yScale = useMemo(
    () => scaleLinear<number>({ domain: [0, 1], range: [innerHeight, 0] }),
    [innerHeight],
  );

  const { tooltipData, tooltipLeft, tooltipTop, showTooltip, hideTooltip } =
    useTooltip<Point>();
  const [highlight, setHighlight] = useState<number | null>(null);

  return (
    <div
      ref={ref}
      className="relative w-full aspect-[4/3] h-[clamp(240px,40vh,380px)]"
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Zoom<SVGSVGElement>
          width={innerWidth}
          height={innerHeight}
          scaleXMin={0.5}
          scaleXMax={4}
          scaleYMin={0.5}
          scaleYMax={4}
        >
          {(zoom) => (
            <svg width={width} height={height} className="glass rounded-lg">
              <rect
                width={width}
                height={height}
                fill="transparent"
                onMouseDown={zoom.dragStart}
                onMouseMove={zoom.dragMove}
                onMouseUp={zoom.dragEnd}
                onMouseLeave={() => {
                  zoom.dragEnd();
                  hideTooltip();
                  setHighlight(null);
                }}
                onWheel={zoom.handleWheel}
              />
              <Group left={margin.left} top={margin.top}>
                <GridColumns
                  scale={zoom.applyToScale(xScale)}
                  height={innerHeight}
                  stroke="#e0e0e0"
                />
                <GridRows
                  scale={zoom.applyToScale(yScale)}
                  width={innerWidth}
                  stroke="#e0e0e0"
                />
                <AxisBottom
                  top={innerHeight}
                  scale={zoom.applyToScale(xScale)}
                  numTicks={4}
                />
                <AxisLeft scale={zoom.applyToScale(yScale)} numTicks={4} />
                <Group transform={zoom.toString()}>
                  {arrows.map((a, i) => (
                    <motion.line
                      key={i}
                      x1={xScale(a.from.x)}
                      y1={yScale(a.from.y)}
                      x2={xScale(a.to.x)}
                      y2={yScale(a.to.y)}
                      stroke="#999"
                      strokeWidth={1}
                      markerEnd="url(#arrow)"
                      initial={{ x2: xScale(a.from.x), y2: yScale(a.from.y) }}
                      animate={{ x2: xScale(a.to.x), y2: yScale(a.to.y) }}
                      transition={{ duration: 0.5 }}
                    />
                  ))}
                  {points.map((p, i) => (
                    <motion.circle
                      key={i}
                      cx={xScale(p.x)}
                      cy={yScale(p.y)}
                      r={highlight === i ? (p.r ? p.r : 8) * 1.3 : p.r ? p.r : 8}
                      fill={highlight === i ? '#FF7A7A' : color}
                      onMouseMove={(event) => {
                        const point = localPoint(event);
                        if (!point) return;
                        const inverted = zoom.applyInverseToPoint({
                          x: point.x,
                          y: point.y,
                        });
                        showTooltip({
                          tooltipData: p,
                          tooltipLeft: inverted.x + margin.left,
                          tooltipTop: inverted.y + margin.top,
                        });
                        setHighlight(i);
                      }}
                      onMouseLeave={() => {
                        hideTooltip();
                        setHighlight(null);
                      }}
                      initial={{ cx: xScale(p.x), cy: yScale(p.y), r: 0 }}
                      animate={{ cx: xScale(p.x), cy: yScale(p.y), r: p.r ? p.r : 8 }}
                      transition={{ duration: 0.5 }}
                    />
                  ))}
                </Group>
                <defs>
                  <marker
                    id="arrow"
                    viewBox="0 0 10 10"
                    refX="5"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M0 0L10 5L0 10z" fill="#999" />
                  </marker>
                </defs>
              </Group>
            </svg>
          )}
        </Zoom>
        <div className="mt-2 flex justify-center">
          <LegendOrdinal
            scale={scaleOrdinal<string, string>({
              domain: ['Trajectory'],
              range: [color],
            })}
            direction="row"
          />
        </div>
        {tooltipData && (
          <TooltipWithBounds
            left={tooltipLeft}
            top={tooltipTop}
            className="rounded-md bg-black/80 p-2 text-xs text-white"
          >
            <div className="font-medium">Week {tooltipData.week}</div>
            <div>x: {tooltipData.x.toFixed(3)}</div>
            <div>y: {tooltipData.y.toFixed(3)}</div>
          </TooltipWithBounds>
        )}
      </motion.div>
    </div>
  );
}

