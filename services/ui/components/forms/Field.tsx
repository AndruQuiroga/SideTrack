import * as React from 'react';
import { Controller, useFormContext, type FieldValues } from 'react-hook-form';
import { Loader2 } from 'lucide-react';
import { Input } from '../ui/input';

interface FieldProps<T extends FieldValues = FieldValues> {
  name: string;
  label: string;
  help?: string;
  required?: boolean;
  children?: ((field: any) => React.ReactNode) | React.ReactElement;
}

function Field<T extends FieldValues = FieldValues>({
  name,
  label,
  help,
  required,
  children,
}: FieldProps<T>) {
  const { control, formState } = useFormContext<T>();

  return (
    <Controller
      name={name as any}
      control={control}
      render={({ field, fieldState }) => {
        const fieldId = field.name;
        const rendered = children
          ? typeof children === 'function'
            ? (children as any)({ ...field, id: fieldId })
            : React.cloneElement(children as React.ReactElement, { ...field, id: fieldId })
          : <Input id={fieldId} {...field} />;
        return (
          <div className="space-y-1">
            <label htmlFor={fieldId} className="text-sm font-medium flex items-center gap-1">
              {label}
              {required && <span className="text-destructive">*</span>}
            </label>
            <div className="flex items-center gap-2">
              {rendered}
              {formState.isValidating && (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              )}
            </div>
            {fieldState.error ? (
              <p className="text-sm text-destructive" role="alert">
                {fieldState.error.message}
              </p>
            ) : (
              help && <p className="text-sm text-muted-foreground">{help}</p>
            )}
          </div>
        );
      }}
    />
  );
}

export { Field };
