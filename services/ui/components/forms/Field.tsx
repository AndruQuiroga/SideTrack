import * as React from 'react';
import {
  Controller,
  useFormContext,
  type ControllerRenderProps,
  type FieldPath,
  type FieldValues,
} from 'react-hook-form';
import { Loader2 } from 'lucide-react';
import { Input } from '../ui/input';

type FieldChildProps<
  TFieldValues extends FieldValues,
  TName extends FieldPath<TFieldValues>,
> = ControllerRenderProps<TFieldValues, TName> & { id: string };

type FieldChild<
  TFieldValues extends FieldValues,
  TName extends FieldPath<TFieldValues>,
> =
  | ((field: FieldChildProps<TFieldValues, TName>) => React.ReactNode)
  | React.ReactElement<Partial<FieldChildProps<TFieldValues, TName>>>;

interface FieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> {
  name: TName;
  label: string;
  help?: string;
  required?: boolean;
  children?: FieldChild<TFieldValues, TName>;
}

function Field<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({
  name,
  label,
  help,
  required,
  children,
}: FieldProps<TFieldValues, TName>) {
  const { control, formState } = useFormContext<TFieldValues>();

  return (
    <Controller<TFieldValues, TName>
      name={name}
      control={control}
      render={({ field, fieldState }) => {
        const fieldId = field.name;
        const fieldWithId: FieldChildProps<TFieldValues, TName> = { ...field, id: fieldId };
        let rendered: React.ReactNode;

        if (typeof children === 'function') {
          rendered = children(fieldWithId);
        } else if (React.isValidElement(children)) {
          rendered = React.cloneElement(children, fieldWithId);
        } else {
          rendered = <Input id={fieldId} {...field} />;
        }
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
