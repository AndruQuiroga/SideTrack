import ExploreTabs from '../../components/ExploreTabs';

export default function ExploreLayout({ children }: { children: React.ReactNode }) {
  return (
    <section className="space-y-6">
      <ExploreTabs />
      {children}
    </section>
  );
}
