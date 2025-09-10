import * as React from 'react';
import { Card } from '../ui/card';
import { cn } from '../../lib/utils';

interface FormSectionProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
}

function FormSection({ title, description, className, children, ...props }: FormSectionProps) {
  return (
    <Card className={cn('space-y-4 p-4', className)} {...props}>
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
    </Card>
  );
}

export { FormSection };
