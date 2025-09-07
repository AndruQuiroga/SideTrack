import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cn } from '../lib/utils';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  asChild?: boolean;
}

const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'div';
    return (
      <Comp
        ref={ref}
        className={cn('animate-pulse rounded-lg bg-muted w-full', className)}
        {...props}
      />
    );
  },
);
Skeleton.displayName = 'Skeleton';

export default Skeleton;
