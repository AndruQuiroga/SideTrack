# UI Design Tokens

The UI layer exposes a small set of design tokens as CSS custom properties.
Tailwind reads these variables so components can stay in sync with the design
system without duplicating values.

## Spacing

Tokens map `space-1` through `space-6` to a stepped scale:

| Token       | Value     |
| ----------- | --------- |
| `--space-1` | `0.25rem` |
| `--space-2` | `0.5rem`  |
| `--space-3` | `0.75rem` |
| `--space-4` | `1rem`    |
| `--space-5` | `1.25rem` |
| `--space-6` | `1.5rem`  |

Use the corresponding Tailwind utilities (`p-3`, `gap-4`, etc.) for layout.

## Typography

Font sizes are driven by variables consumed by Tailwind's `text-*` classes:

| Class       | Variable      | Size       |
| ----------- | ------------- | ---------- |
| `text-xs`   | `--text-xs`   | `0.75rem`  |
| `text-sm`   | `--text-sm`   | `0.875rem` |
| `text-base` | `--text-base` | `1rem`     |
| `text-lg`   | `--text-lg`   | `1.125rem` |
| `text-xl`   | `--text-xl`   | `1.25rem`  |
| `text-2xl`  | `--text-2xl`  | `1.5rem`   |

The `Typography` component wraps these classes to provide consistent heading and
body styles.

## Shadows

The soft elevation used across surfaces is defined as:

| Token           | Class         | Value                             |
| --------------- | ------------- | --------------------------------- |
| `--shadow-soft` | `shadow-soft` | `0 10px 30px rgba(0, 0, 0, 0.12)` |

Components should reference these tokens rather than hard‑coding values to keep
the interface visually consistent.
