import { test, expect } from '@playwright/test';

// Ensure the trajectory page renders a Plotly chart

test('renders trajectory plot', async ({ page }) => {
  await page.goto('/trajectory');
  const plot = page.locator('.js-plotly-plot');
  await expect(plot).toBeVisible();
});
