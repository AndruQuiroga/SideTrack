'use client';
import { AreaStack, AreaClosed } from '@visx/shape';
import { scaleLinear, scaleTime, scaleOrdinal } from '@visx/scale';
import { extent } from 'd3-array';
import { motion } from 'framer-motion';

type Series = { week: Date; [axis: string]: number | Date };

export default function MoodsStreamgraph({ data, axes }: { data: Series[]; axes: string[] }) {
  const width = 800;
  const height = 320;
  const margin = { top: 10, right: 10, bottom: 20, left: 10 };
  const xDomain = extent(data, (d) => d.week as Date) as [Date, Date];
  const xScale = scaleTime({ domain: xDomain, range: [margin.left, width - margin.right] });
  const yScale = scaleLinear({ domain: [0, 1], range: [height - margin.bottom, margin.top] });
  const color = scaleOrdinal<string, string>({
    domain: axes,
    range: ['#2FE08B', '#39D2FF', '#FFA84D', '#FF7A7A', '#A88BFF'],
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="glass rounded-lg">
        <AreaStack
          keys={axes}
          data={data}
          x={(d) => xScale(d.week as Date) ?? 0}
          y0={() => 0}
          y1={(d) => yScale(d as number)}
        >
          {({ stacks, path }) =>
            stacks.map((stack) => (
              <AreaClosed
                key={stack.key}
                data={stack}
                d={(d) => path(d) || ''}
                fill={color(stack.key) ?? '#2FE08B'}
                fillOpacity={0.35}
                stroke={color(stack.key) ?? '#2FE08B'}
                strokeWidth={1}
              />
            ))
          }
        </AreaStack>
      </svg>
    </motion.div>
  );
}
