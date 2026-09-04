import { test, expect } from '@playwright/test';

test('dashboard renders service health and incidents', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('系统概览')).toBeVisible();
  await expect(page.getByText('Service Health').first()).toBeVisible();
  await expect(page.getByText('Recent Incidents').first()).toBeVisible();
});

test('login flow shows login button', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: '登录' })).toBeVisible();
});