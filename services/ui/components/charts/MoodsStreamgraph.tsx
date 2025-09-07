'use client';
import { AreaStack } from '@visx/shape';
import { scaleLinear, scaleTime, scaleOrdinal } from '@visx/scale';
import { extent, bisector } from 'd3-array';
import { motion } from 'framer-motion';
import { useTooltip, TooltipWithBounds } from '@visx/tooltip';
import { LegendOrdinal } from '@visx/legend';
import { localPoint } from '@visx/event';
import useMeasure from 'react-use-measure';
import { useMemo } from 'react';

type Series = { week: Date; [axis: string]: number | Date };

export default function MoodsStreamgraph({ data, axes }: { data: Series[]; axes: string[] }) {
  const [ref, bounds] = useMeasure();
  const width = bounds.width || 800;
  const height = bounds.height || 320;
  const margin = { top: 10, right: 10, bottom: 20, left: 10 };

  const xDomain = useMemo(() => extent(data, (d) => d.week as Date) as [Date, Date], [data]);
  const xScale = useMemo(
    () => scaleTime({ domain: xDomain, range: [margin.left, width - margin.right] }),
    [xDomain, width, margin.left, margin.right],
  );
  const yScale = useMemo(
    () => scaleLinear({ domain: [0, 1], range: [height - margin.bottom, margin.top] }),
    [height, margin.bottom, margin.top],
  );
  const color = useMemo(
    () =>
      scaleOrdinal<string, string>({
        domain: axes,
        range: ['#2FE08B', '#39D2FF', '#FFA84D', '#FF7A7A', '#A88BFF'],
      }),
    [axes],
  );

  const { tooltipData, tooltipLeft, tooltipTop, showTooltip, hideTooltip } = useTooltip<Series>();

  const dateBisect = useMemo(() => bisector<Series, Date>((d) => d.week as Date).left, []);

  const handleMouseMove = (event: React.MouseEvent<SVGRectElement>) => {
    const point = localPoint(event);
    if (!point) return;
    const x0 = xScale.invert(point.x);
    const index = dateBisect(data, x0, 1);
    const d0 = data[index - 1];
    const d1 = data[index];
    let d = d0;
    if (d1 && +x0 - +(d0.week as Date) > +(d1.week as Date) - +x0) {
      d = d1;
    }
    showTooltip({
      tooltipData: d,
      tooltipLeft: xScale(d.week as Date),
      tooltipTop: margin.top,
    });
  };

  return (
    <div ref={ref} className="relative w-full aspect-[4/3] h-[clamp(240px,40vh,320px)]">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <svg width={width} height={height} className="glass rounded-lg">
          <AreaStack
            keys={axes}
            data={data}
            x={(d) => xScale(d.week as Date) ?? 0}
            y0={() => 0}
            y1={(d) => yScale(d as number)}
          >
            {({ stacks, path }) =>
              stacks.map((stack) => {
                const d = path(stack) || '';
                return (
                  <motion.path
                    key={stack.key}
                    d={d}
                    fill={color(stack.key) ?? '#2FE08B'}
                    fillOpacity={0.35}
                    stroke={color(stack.key) ?? '#2FE08B'}
                    strokeWidth={1}
                    initial={{ d }}
                    animate={{ d }}
                    transition={{ duration: 0.5 }}
                  />
                );
              })
            }
          </AreaStack>
          <rect
            width={width}
            height={height}
            fill="transparent"
            onMouseMove={handleMouseMove}
            onMouseLeave={hideTooltip}
          />
        </svg>
        <div className="mt-2 flex justify-center">
          <LegendOrdinal scale={color} direction="row" labelMargin="0 12px 0 0" />
        </div>
        {tooltipData && (
          <TooltipWithBounds
            left={tooltipLeft}
            top={tooltipTop}
            className="rounded-md bg-black/80 p-2 text-xs text-white"
          >
            <div className="font-medium">{(tooltipData.week as Date).toLocaleDateString()}</div>
            {axes.map((axis) => (
              <div key={axis} style={{ color: color(axis) }}>
                {axis}: {(tooltipData[axis] as number).toFixed(2)}
              </div>
            ))}
          </TooltipWithBounds>
        )}
      </motion.div>
    </div>
  );
}
