# Forms

The UI uses a small collection of composable helpers in
`apps/web/src/components/forms` built on top of zod and
react-hook-form.

```tsx
import { z } from 'zod';
import { ZForm, FormSection, Field, SubmitBar } from './components/forms';
import { Input } from './components/ui/input';

const schema = z.object({ name: z.string() });

export default function Example() {
  return (
    <ZForm schema={schema} onSubmit={(v) => console.log(v)}>
      <FormSection title="Profile">
        <Field name="name" label="Name" required>
          {(field) => <Input {...field} />}
        </Field>
      </FormSection>
      <SubmitBar />
    </ZForm>
  );
}
```

## Arrays

Use `Field` inside an array map and index names:

```tsx
const schema = z.object({ tags: z.array(z.string().min(1)) });

{fields.map((f, i) => (
  <Field key={f.id} name={`tags.${i}`} label={`Tag ${i + 1}`}
    required>
    {(field) => <Input {...field} />}
  </Field>
))}
```

## File input

File inputs can be wired by passing an `<input type="file" />` as
children and reading `field.files`:

```tsx
<Field name="avatar" label="Avatar" required>
  {(field) => (
    <Input type="file" {...field} onChange={(e) => field.onChange(e.target.files)} />
  )}
</Field>
```

## Async rules

Zod refinements may return promises. `Field` will display a spinner while
validation runs via `formState.isValidating`:

```tsx
const schema = z.object({
  username: z.string().refine(async (v) => !(await exists(v)), {
    message: 'Taken',
  }),
});
```
