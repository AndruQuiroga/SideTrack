import Link from 'next/link';

import { Button } from '../components/ui/button';
import { Typography } from '../components/ui/Typography';

export default function NotFound() {
  return (
    <section className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center">
      <Typography as="h1" variant="h1" className="text-3xl sm:text-4xl">
        Page not found
      </Typography>
      <Typography className="max-w-md text-muted-foreground">
        We couldn't find the page you're looking for. Head back home to continue exploring your insights.
      </Typography>
      <Button asChild>
        <Link href="/">Return home</Link>
      </Button>
    </section>
  );
}
