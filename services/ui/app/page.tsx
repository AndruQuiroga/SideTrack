'use client';
import MetricCard from '../components/MetricCard';
import Link from 'next/link';
import { motion } from 'framer-motion';
import ChartContainer from '../components/ChartContainer';
import FilterBar from '../components/FilterBar';
import Avatar from '../components/ui/Avatar';

export default function Home() {
  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Overview</h1>
          <p className="text-sm text-muted-foreground">Your listening vibe at a glance</p>
        </div>
        <Link
          href="/trajectory"
          className="rounded-full bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300 hover:bg-emerald-500/20"
        >
          View trajectory
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          <MetricCard
            key="m1"
            title="Listens (7d)"
            value={128}
            delta={{ value: 12, suffix: '%' }}
          />,
          <MetricCard key="m2" title="Energy" value={0.67} delta={{ value: -0.03 }} />,
          <MetricCard key="m3" title="Valence" value={0.51} delta={{ value: 0.02 }} />,
          <MetricCard key="m4" title="Momentum" value={'+0.08'} />,
        ].map((card, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 * i, duration: 0.35, ease: 'easeOut' }}
          >
            {card}
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
      <div className="grid gap-6 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <ChartContainer
            title="Recent Weeks"
            subtitle="Quick glance at your trajectory"
            actions={
              <Link href="/trajectory" className="text-xs text-muted-foreground hover:underline">
                Open
              </Link>
            }
          >
            <motion.div
              className="h-48 rounded-md bg-white/5"
              initial={{ scale: 0.98, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.4 }}
            />
          </ChartContainer>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.05 }}
        >
          <ChartContainer
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
          </ChartContainer>
        </motion.div>
      </div>
    </section>
  );
}
