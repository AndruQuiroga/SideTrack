import React from 'react';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FiltersBar from './FiltersBar';
import { DEFAULT_FILTERS, filtersSchema, type FiltersFormValues } from './filters.schema';

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined' && !('ResizeObserver' in window)) {
  // @ts-expect-error jsdom environment mock
  window.ResizeObserver = ResizeObserverMock;
}

describe('filtersSchema', () => {
  it('rejects values outside the allowed range', () => {
    const result = filtersSchema.safeParse({
      newOnly: false,
      freshness: 1.1,
      diversity: -0.1,
      energy: 0.5,
    });

    expect(result.success).toBe(false);
    if (result.success) {
      return;
    }

    const issuesByField = result.error.issues.reduce<Record<string, string[]>>((acc, issue) => {
      const key = issue.path.join('.') || 'root';
      acc[key] = acc[key] ?? [];
      acc[key].push(issue.message);
      return acc;
    }, {});

    expect(Object.keys(issuesByField)).toEqual(expect.arrayContaining(['freshness', 'diversity']));
    expect(issuesByField.freshness?.[0]).toContain('between 0 and 1');
    expect(issuesByField.diversity?.[0]).toContain('between 0 and 1');
  });
});

describe('FiltersBar', () => {
  it('debounces filter changes before calling onChange', async () => {
    jest.useFakeTimers();
    try {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const onChange = jest.fn();

      render(<FiltersBar filters={DEFAULT_FILTERS} onChange={onChange} />);

      const toggle = screen.getByRole('switch');
      await user.click(toggle);

      expect(onChange).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(299);
      });
      expect(onChange).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1);
      });

      expect(onChange).toHaveBeenCalledTimes(1);
      expect(onChange).toHaveBeenCalledWith({
        ...DEFAULT_FILTERS,
        newOnly: true,
      });
    } finally {
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    }
  });

  it('uses default values when provided invalid filters', async () => {
    const onChange = jest.fn();
    const invalidFilters = {
      newOnly: false,
      freshness: 2,
      diversity: -1,
      energy: 0.3,
    } as FiltersFormValues;
    const user = userEvent.setup();

    render(<FiltersBar filters={invalidFilters} onChange={onChange} />);

    const apply = screen.getByRole('button', { name: /apply/i });
    await user.click(apply);

    expect(onChange).toHaveBeenCalledWith(DEFAULT_FILTERS);
  });
});
