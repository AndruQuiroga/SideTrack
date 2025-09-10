import * as React from 'react';
import { useForm, FormProvider, type SubmitHandler } from 'react-hook-form';
import { z, type ZodType } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { cn } from '../../lib/utils';

interface ZFormProps<TSchema extends ZodType<any, any>> extends React.HTMLAttributes<HTMLFormElement> {
  schema: TSchema;
  defaultValues?: z.infer<TSchema>;
  onSubmit: SubmitHandler<z.infer<TSchema>>;
}

function ZForm<TSchema extends ZodType<any, any>>({
  schema,
  defaultValues,
  onSubmit,
  className,
  children,
  ...props
}: ZFormProps<TSchema>) {
  const form = useForm<z.infer<TSchema>>({
    resolver: zodResolver(schema),
    defaultValues,
  });

  React.useEffect(() => {
    if (defaultValues) {
      form.reset(defaultValues);
    }
  }, [defaultValues]);

  return (
    <FormProvider {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className={cn(className)}
        noValidate
        {...props}
      >
        {children}
      </form>
    </FormProvider>
  );
}

export { ZForm };
