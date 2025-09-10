import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const typographyVariants = cva('', {
  variants: {
    variant: {
      h1: 'scroll-m-20 text-2xl font-bold tracking-tight',
      h2: 'scroll-m-20 text-xl font-semibold tracking-tight',
      h3: 'scroll-m-20 text-lg font-semibold tracking-tight',
      p: 'text-base leading-7',
      muted: 'text-sm text-muted-foreground',
    },
  },
  defaultVariants: {
    variant: 'p',
  },
});

export interface TypographyProps
  extends React.HTMLAttributes<HTMLElement>,
    VariantProps<typeof typographyVariants> {
  as?: React.ElementType;
}

const Typography = React.forwardRef<HTMLElement, TypographyProps>(
  ({ className, variant, as: Comp = 'p', ...props }, ref) => (
    <Comp ref={ref} className={cn(typographyVariants({ variant }), className)} {...props} />
  ),
);
Typography.displayName = 'Typography';

export { Typography, typographyVariants };
