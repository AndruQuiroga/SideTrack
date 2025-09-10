'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';
import FilterBar from '../components/FilterBar';
import Avatar from '../components/ui/Avatar';
import RecentListensTable from '../components/RecentListensTable';
import KpiCard from '../components/dashboard/KpiCard';
import ChartCard from '../components/dashboard/ChartCard';

export default function Home() {
  return (
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Overview</h1>
          <p className="text-sm text-muted-foreground">Your listening vibe at a glance</p>
        </div>
        <Link
          href="/trajectory"
          className="h-11 rounded-full bg-emerald-500/10 px-4 text-sm text-emerald-300 hover:bg-emerald-500/20"
        >
          View trajectory
        </Link>
      </div>

      <div className="grid gap-4 @[640px]:grid-cols-2 @[1024px]:grid-cols-3">
        {[
          {
            title: 'Listens (7d)',
            value: 128,
            delta: { value: 12, suffix: '%' },
            series: [80, 96, 102, 110, 115, 120, 128],
          },
          {
            title: 'Diversity',
            value: 0.82,
            delta: { value: -0.02 },
            series: [0.78, 0.8, 0.81, 0.83, 0.82, 0.82, 0.82],
          },
          {
            title: 'Momentum',
            value: '+0.08',
            delta: { value: 0.01 },
            series: [0.02, 0.04, 0.05, 0.06, 0.07, 0.08, 0.08],
          },
        ].map((card, i) => (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 * i, duration: 0.35, ease: 'easeOut' }}
          >
            <KpiCard {...card} />
          </motion.div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <FilterBar
          options={[
            { label: '4w', value: '4w' },
            { label: '12w', value: '12w' },
            { label: '24w', value: '24w' },
          ]}
          value="12w"
        />
      </div>
      <div className="grid gap-6 @[768px]:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <ChartCard
            title="Recent Weeks"
            subtitle="Quick glance at your trajectory"
            actions={
              <Link href="/trajectory" className="text-xs text-muted-foreground hover:underline">
                Open
              </Link>
            }
            plot={{
              ariaLabel: 'recent weeks trend',
              data: [
                {
                  x: ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7'],
                  y: [0.2, 0.35, 0.4, 0.5, 0.45, 0.6, 0.65],
                  type: 'scatter',
                  mode: 'lines+markers',
                  line: { color: '#2FE08B' },
                },
              ],
            }}
          />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.05 }}
        >
          <ChartCard
            title="Outliers"
            subtitle="Far from your recent centroid"
            actions={
              <Link href="/outliers" className="text-xs text-muted-foreground hover:underline">
                Open
              </Link>
            }
          >
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <motion.div
                  key={i}
                  className="flex items-center gap-3 rounded-md p-2 hover:bg-white/5"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.05 * i }}
                  whileHover={{ scale: 1.01 }}
                >
                  <Avatar size={32} />
                  <div className="flex-1">
                    <div className="text-sm">Track {i}</div>
                    <div className="text-xs text-muted-foreground">Artist</div>
                  </div>
                  <div className="text-xs text-muted-foreground">dist 0.{9 - i}</div>
                </motion.div>
              ))}
            </div>
          </ChartCard>
        </motion.div>
      </div>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <ChartCard title="Recent Listens">
          <RecentListensTable />
        </ChartCard>
      </motion.div>
    </section>
  );
}
