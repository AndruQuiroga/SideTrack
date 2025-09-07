import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const cardVariants = cva('rounded-lg bg-card text-card-foreground', {
  variants: {
    variant: {
      default: 'border border-border',
      glass: 'bg-white/5 backdrop-blur-md backdrop-saturate-150 border border-border',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
});

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  asChild?: boolean;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'div';
    return <Comp className={cn(cardVariants({ variant }), className)} ref={ref} {...props} />;
  },
);
Card.displayName = 'Card';

export { Card, cardVariants };
