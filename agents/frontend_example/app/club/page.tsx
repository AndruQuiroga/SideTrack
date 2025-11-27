import { PageShell } from "@/components/PageShell";
import { WeekCard } from "@/components/WeekCard";
import { weeks } from "@/lib/sample-data";

export default function ClubArchivePage() {
  return (
    <PageShell
      title="Club Archive"
      description="Browse every Sidetrack Club session. Each week becomes a little time capsule: winner, nominees, votes, and how the room felt about it."
      accent="Album of the Week · Archive"
    >
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {weeks.map((week) => (
          <WeekCard key={week.id} week={week} />
        ))}
      </section>
    </PageShell>
  );
}
