import { z } from 'zod';

export const filtersSchema = z.object({
  newOnly: z.boolean(),
  freshness: z
    .number()
    .min(0, 'Freshness must be between 0 and 1')
    .max(1, 'Freshness must be between 0 and 1'),
  diversity: z
    .number()
    .min(0, 'Diversity must be between 0 and 1')
    .max(1, 'Diversity must be between 0 and 1'),
  energy: z
    .number()
    .min(0, 'Energy must be between 0 and 1')
    .max(1, 'Energy must be between 0 and 1'),
});

export type FiltersFormValues = z.infer<typeof filtersSchema>;

export const DEFAULT_FILTERS: FiltersFormValues = {
  newOnly: false,
  freshness: 0,
  diversity: 0,
  energy: 0,
};
