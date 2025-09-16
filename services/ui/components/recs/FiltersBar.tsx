'use client';

import { useEffect, useRef } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import { Slider } from '../ui/slider';
import {
  DEFAULT_FILTERS,
  filtersSchema,
  type FiltersFormValues,
} from './filters.schema';

interface Props {
  filters: FiltersFormValues;
  onChange: (f: FiltersFormValues) => void;
}

export default function FiltersBar({ filters, onChange }: Props) {
  const initialValuesResult = filtersSchema.safeParse(filters);
  const form = useForm<FiltersFormValues>({
    resolver: zodResolver(filtersSchema),
    defaultValues: initialValuesResult.success
      ? initialValuesResult.data
      : DEFAULT_FILTERS,
  });

  const watchedValues = form.watch();
  const values: FiltersFormValues = {
    newOnly: watchedValues?.newOnly ?? DEFAULT_FILTERS.newOnly,
    freshness: watchedValues?.freshness ?? DEFAULT_FILTERS.freshness,
    diversity: watchedValues?.diversity ?? DEFAULT_FILTERS.diversity,
    energy: watchedValues?.energy ?? DEFAULT_FILTERS.energy,
  };

  const skipNextChange = useRef(true);
  const debounceTimeout = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const parsed = filtersSchema.safeParse(filters);
    skipNextChange.current = true;
    form.reset(parsed.success ? parsed.data : DEFAULT_FILTERS);
  }, [filters, form]);

  useEffect(() => {
    if (skipNextChange.current) {
      skipNextChange.current = false;
      return;
    }

    if (debounceTimeout.current) {
      clearTimeout(debounceTimeout.current);
      debounceTimeout.current = null;
    }

    const parsed = filtersSchema.safeParse(values);
    if (!parsed.success) {
      return;
    }

    debounceTimeout.current = setTimeout(() => {
      onChange(parsed.data);
    }, 300);

    return () => {
      if (debounceTimeout.current) {
        clearTimeout(debounceTimeout.current);
        debounceTimeout.current = null;
      }
    };
  }, [values, onChange]);

  useEffect(() => {
    return () => {
      if (debounceTimeout.current) {
        clearTimeout(debounceTimeout.current);
        debounceTimeout.current = null;
      }
    };
  }, []);

  const apply = form.handleSubmit((data) => {
    if (debounceTimeout.current) {
      clearTimeout(debounceTimeout.current);
      debounceTimeout.current = null;
    }
    onChange(data);
  });

  return (
    <div className="space-y-4 text-sm">
      <div className="space-y-2">
        <span className="font-medium">Artist filters</span>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>New artists only</span>
            {values.newOnly && (
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                On
              </span>
            )}
          </div>
          <Controller
            control={form.control}
            name="newOnly"
            render={({ field }) => (
              <Switch
                checked={field.value}
                onCheckedChange={field.onChange}
                onBlur={field.onBlur}
                ref={field.ref}
              />
            )}
          />
        </div>
      </div>
      <div className="space-y-2">
        <span className="font-medium">Track attributes</span>
        <div className="space-y-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span>Min freshness</span>
              {values.freshness > DEFAULT_FILTERS.freshness && (
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                  {values.freshness.toFixed(1)}
                </span>
              )}
            </div>
            <Controller
              control={form.control}
              name="freshness"
              render={({ field }) => (
                <Slider
                  value={[field.value]}
                  min={0}
                  max={1}
                  step={0.1}
                  onValueChange={(v) => field.onChange(v[0])}
                  onBlur={field.onBlur}
                />
              )}
            />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span>Diversity</span>
              {values.diversity > DEFAULT_FILTERS.diversity && (
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                  {values.diversity.toFixed(1)}
                </span>
              )}
            </div>
            <Controller
              control={form.control}
              name="diversity"
              render={({ field }) => (
                <Slider
                  value={[field.value]}
                  min={0}
                  max={1}
                  step={0.1}
                  onValueChange={(v) => field.onChange(v[0])}
                  onBlur={field.onBlur}
                />
              )}
            />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span>Energy</span>
              {values.energy > DEFAULT_FILTERS.energy && (
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                  {values.energy.toFixed(1)}
                </span>
              )}
            </div>
            <Controller
              control={form.control}
              name="energy"
              render={({ field }) => (
                <Slider
                  value={[field.value]}
                  min={0}
                  max={1}
                  step={0.1}
                  onValueChange={(v) => field.onChange(v[0])}
                  onBlur={field.onBlur}
                />
              )}
            />
          </div>
        </div>
      </div>
      <Button type="button" onClick={() => void apply()} className="mt-2">
        Apply
      </Button>
    </div>
  );
}
