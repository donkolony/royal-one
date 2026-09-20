import { test, expect, type Page } from '@playwright/test';

async function login(page: Page, role: 'client' | 'advisor' = 'client') {
  await page.addInitScript(role => sessionStorage.setItem('rs_mock_role', role), role);
  await page.goto('/');
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeAttached();
}

test('sign-in and role guards protect staff routes', async ({ page }) => {
  await page.goto('/advisor/clients');
  await expect(page).toHaveURL(/sign-in/);
  await page.getByRole('button', { name: 'Client Thabo Mokoena' }).click();
  await expect(page).toHaveURL(/not-found/);
  await page.getByRole('link', { name: 'Return home' }).click();
  await expect(page.getByRole('heading', { name: 'Good morning, Thabo.' })).toBeVisible();
  await page.goto('/owner');
  await expect(page).toHaveURL(/not-found/);
});

test('client dashboard retains the design and navigates to API-backed pages', async ({ page }) => {
  await login(page);
  await expect(page.getByRole('region', { name: 'Your net worth' })).toContainText('Total assets');
  await expect(page.locator('.brand-logo')).toBeVisible();
  await page.getByRole('link', { name: 'View all goals' }).click();
  await expect(page.getByRole('heading', { name: 'My Goals' })).toBeVisible();
  await page.getByRole('button', { name: 'More', exact: true }).click();
  await page.getByRole('link', { name: 'Policies', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Policies/ }).first()).toBeVisible();
  await expect(page.getByRole('link', { name: 'Identity', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'My record', exact: true })).toBeVisible();
});

test('adviser client search and added feature navigation', async ({ page }) => {
  await login(page, 'advisor');
  await page.getByRole('link', { name: 'Clients', exact: true }).click();
  await page.getByPlaceholder('Search clients...').fill('Lerato');
  await expect(page.getByRole('cell', { name: /Lerato Dlamini/ })).toBeVisible();
  await expect(page.getByRole('cell', { name: /Thabo Mokoena/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'More', exact: true }).click();
  for (const label of ['Opportunities', 'Compliance', 'Audit log', 'Privacy', 'Assistant', 'Email']) {
    await expect(page.getByRole('link', { name: label, exact: true })).toBeVisible();
  }
});

test('desktop and mobile workspace have no horizontal overflow', async ({ page }) => {
  await login(page);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Good morning, Thabo.' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await page.screenshot({ path: `test-results/overview-${width}.png`, fullPage: true });
    if (width === 390) {
      await page.getByRole('button', { name: 'Open navigation' }).click();
      await page.getByRole('link', { name: 'Goals', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'My Goals' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Open navigation' })).toBeVisible();
    }
  }
});

 test('reminder completion moves the record into the done filter', async ({ page }) => {
  await login(page);
  await page.getByRole('link', { name: 'Reminders', exact: true }).click();
  const button = page.getByRole('button', { name: 'Mark Done', exact: true }).first();
  await expect(button).toBeVisible();
  const title = await button.locator('..').locator('p').first().innerText();
  await button.click();
  await expect(page.getByText(title, { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'done', exact: true }).click();
  await expect(page.getByText(title, { exact: true })).toBeVisible();
});

test('a saved draft opens the claim form and saves incident details', async ({ page }) => {
  await login(page);
  await page.getByRole('link', { name: 'Claims', exact: true }).click();
  await page.getByRole('link', { name: 'Draft claim', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'What happened?', exact: true })).toBeVisible();
  await page.getByLabel('When did it happen?').fill('2026-09-18T10:30');
  await page.getByLabel('Where did it happen?', { exact: false }).fill('Synthetic test intersection');
  await page.getByLabel('What happened?', { exact: false }).fill('Synthetic incident for workflow testing.');
  await page.getByRole('button', { name: 'Save and continue' }).click();
  await expect(page.getByRole('heading', { name: 'Police, driver and other people' })).toBeVisible();
  await page.getByRole('button', { name: 'Back', exact: true }).click();
  await expect(page.getByLabel('Where did it happen?', { exact: false })).toHaveValue('Synthetic test intersection');
});

test('adviser dashboard stays readable on desktop, tablet and mobile', async ({ page }) => {
  await login(page, 'advisor');
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('/advisor');
    await expect(page.getByRole('heading', { name: /A clearer day ahead/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Claims at a glance' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    if (width === 1440) {
      await expect(page.locator('.sidebar')).toHaveCSS('width', '280px');
      await expect(page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Clients', exact: true })).toHaveCSS('font-size', '16px');
    }
    await page.screenshot({ path: `test-results/adviser-${width}.png`, fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  const task = page.locator('.adviser-task').first();
  await expect(task).toBeVisible();
  await expect(task).toHaveAttribute('href', /^\/advisor\//);
  const destination = await task.getAttribute('href');
  await task.click();
  await expect(page).toHaveURL(new RegExp(destination!.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '$'));
  await expect(page.getByRole('heading', { name: 'Page not found' })).toHaveCount(0);
});
