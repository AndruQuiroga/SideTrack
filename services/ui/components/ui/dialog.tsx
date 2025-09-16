import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { cn } from '../../lib/utils';

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;

type DialogA11yContextValue = {
  setTitleId: (id: string | undefined) => void;
  setDescriptionId: (id: string | undefined) => void;
};

const DialogA11yContext = React.createContext<DialogA11yContextValue | null>(null);

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...contentProps }, ref) => {
  const [labelId, setLabelId] = React.useState<string | undefined>();
  const [descriptionId, setDescriptionId] = React.useState<string | undefined>();

  const {
    ['aria-labelledby']: ariaLabelledByProp,
    ['aria-describedby']: ariaDescribedByProp,
    ...restContentProps
  } = contentProps;

  const contextValue = React.useMemo(
    () => ({
      setTitleId: setLabelId,
      setDescriptionId,
    }),
    [setLabelId, setDescriptionId],
  );

  const ariaLabelledBy = ariaLabelledByProp ?? labelId;
  const ariaDescribedBy = ariaDescribedByProp ?? descriptionId;

  return (
    <DialogA11yContext.Provider value={contextValue}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/80" />
        <DialogPrimitive.Content
          ref={ref}
          className={cn(
            'fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border border-border bg-background p-6 shadow-lg',
            className,
          )}
          aria-labelledby={ariaLabelledBy}
          aria-describedby={ariaDescribedBy}
          {...restContentProps}
        >
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogA11yContext.Provider>
  );
});
DialogContent.displayName = DialogPrimitive.Content.displayName;

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, id: idProp, ...props }, ref) => {
  const context = React.useContext(DialogA11yContext);
  const autoId = React.useId();
  const id = idProp ?? autoId;

  React.useEffect(() => {
    if (!context) return;
    context.setTitleId(id);
    return () => context.setTitleId(undefined);
  }, [context, id]);

  return (
    <DialogPrimitive.Title
      ref={ref}
      id={id}
      className={cn('text-lg font-semibold leading-none tracking-tight', className)}
      {...props}
    />
  );
});
DialogTitle.displayName = DialogPrimitive.Title.displayName;

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, id: idProp, ...props }, ref) => {
  const context = React.useContext(DialogA11yContext);
  const autoId = React.useId();
  const id = idProp ?? autoId;

  React.useEffect(() => {
    if (!context) return;
    context.setDescriptionId(id);
    return () => context.setDescriptionId(undefined);
  }, [context, id]);

  return (
    <DialogPrimitive.Description
      ref={ref}
      id={id}
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
    />
  );
});
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export { Dialog, DialogTrigger, DialogContent, DialogTitle, DialogDescription };
