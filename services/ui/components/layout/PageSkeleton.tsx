import type { HTMLAttributes } from 'react';

import Skeleton from '../Skeleton';
import { cn } from '../../lib/utils';

interface PageSkeletonProps extends HTMLAttributes<HTMLElement> {
  sections?: number;
  sectionClassName?: string;
}

export default function PageSkeleton({
  sections = 3,
  className,
  sectionClassName,
  'aria-label': ariaLabel = 'Loading page',
  ...props
}: PageSkeletonProps) {
  const label = ariaLabel ?? 'Loading page';

  return (
    <section
      className={cn('space-y-6', className)}
      aria-busy="true"
      aria-label={label}
      aria-live="polite"
      role="status"
      {...props}
    >
      <span className="sr-only">{label}</span>
      <div className="space-y-2">
        <Skeleton className="h-8 w-32 max-w-full" />
        <Skeleton className="h-4 w-48 max-w-full" />
      </div>
      {Array.from({ length: sections }).map((_, index) => (
        <Skeleton key={index} className={cn('h-32', sectionClassName)} />
      ))}
    </section>
  );
}
