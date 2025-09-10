import * as React from 'react';
import { useFormContext } from 'react-hook-form';
import { Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

interface SubmitBarProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  label?: string;
}

function SubmitBar({ children, label = 'Save', className, ...props }: SubmitBarProps) {
  const { formState } = useFormContext();
  return (
    <div className={cn('flex justify-end pt-4', className)} {...props}>
      {children ?? (
        <Button type="submit" disabled={formState.isSubmitting}>
          {formState.isSubmitting && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          )}
          {label}
        </Button>
      )}
    </div>
  );
}

export { SubmitBar };
