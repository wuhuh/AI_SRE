import { test, expect } from '@playwright/test';

// P2-FE-02: 冒烟对齐真实 React UI（compose frontend :8083，nginx 代理 /api → CP）
// 前置：docker compose up（frontend + control-plane）

test('dashboard renders summary metrics', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('系统概览')).toBeVisible();
  await expect(page.getByText('Incident', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Recovered').first()).toBeVisible();
  await expect(page.getByText('Pending Approval').first()).toBeVisible();
});

test('incidents table loads from real CP', async ({ page }) => {
  await page.goto('/');
  // IncidentTable 数据表渲染（真实数据列）
  await expect(page.locator('table').first()).toBeVisible({ timeout: 15000 });
});

test('login entry exists', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: '登录' })).toBeVisible();
});

test('401 clears token and surfaces unified error', async ({ page }) => {
  // 预置一个坏 token → incidents 请求 401 → 统一错误提示出现
  await page.addInitScript(() => localStorage.setItem('aisre_token', 'invalid-token'));
  await page.goto('/');
  await expect(page.getByText('登录已过期或未登录，请重新登录')).toBeVisible({ timeout: 15000 });
});

test('login via admin stores token', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: '登录' })).toBeVisible();
  const adminPw = process.env.ADMIN_PW || 'aisre-dev-admin-pw';
  // 预挂 dialog 监听（waitForEvent 与 SSE 重渲染竞态会漏掉 prompt）：
  // 第 1 个 prompt=用户名、第 2 个=密码，弹出即 accept
  let seen = 0;
  page.on('dialog', async (d) => {
    try { await d.accept(seen++ === 0 ? 'admin' : adminPw); } catch { /* 已关闭 */ }
  });
  await page.getByRole('button', { name: '登录' }).click({ timeout: 10000 });
  await page.waitForTimeout(1500);
  // 登录成功后 token 落库，后续请求带 Authorization（不再 401）
  const token = await page.evaluate(() => localStorage.getItem('aisre_token'));
  expect(token && token.length > 20).toBeTruthy();
});
