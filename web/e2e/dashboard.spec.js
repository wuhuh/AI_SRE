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
  // Modal 表单登录（替代旧 prompt 流）
  await page.getByRole('button', { name: '登录' }).click();
  await page.getByPlaceholder(/用户名/).fill('admin');
  await page.getByPlaceholder('密码').fill(adminPw);
  await page.getByRole('button', { name: /登\s*录/ }).last().click();
  await page.waitForTimeout(1500);
  // 登录成功后 token 落库，后续请求带 Authorization（不再 401）
  const token = await page.evaluate(() => localStorage.getItem('aisre_token'));
  expect(token && token.length > 20).toBeTruthy();
});

test('incident detail tabs show real data', async ({ page }) => {
  await page.goto('/');
  let seen = 0;
  page.on('dialog', async (d) => {
    try { await d.accept(seen++ === 0 ? 'admin' : 'aisre-dev-admin-pw'); } catch { /* noop */ }
  });
  await page.getByRole('button', { name: '登录' }).click();
  await page.getByPlaceholder(/用户名/).fill('admin');
  await page.getByPlaceholder('密码').fill(process.env.ADMIN_PW || 'aisre-dev-admin-pw');
  await page.getByRole('button', { name: /登\s*录/ }).last().click();
  await expect(page.getByText('Incidents', { exact: true })).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(1200); // 列表首屏
  // 点第一行（选 RESOLVED 的行最有诊断数据：直接点第一行也行，断言 Tab 加载完成）
  await page.locator('.ant-table-row').first().click();
  await expect(page.getByText(/详情 —/)).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(1500); // 详情子资源加载
  // 修复记录接口已从 agent-token 误拦修复为 JWT 可读：不再出现全局 401 提示
  const alertCount = await page.locator('.ant-alert').count();
  expect(alertCount).toBe(0);
  // 基本信息 Tab 至少渲染了开始时间字段（详情接口通）
  await expect(page.getByText('开始时间').first()).toBeVisible();
});

test('evidence tab renders structured summary not raw json', async ({ page }) => {
  await page.goto('/');
  let seen = 0;
  page.on('dialog', async (d) => {
    try { await d.accept(seen++ === 0 ? 'admin' : 'aisre-dev-admin-pw'); } catch { /* noop */ }
  });
  await page.getByRole('button', { name: '登录' }).click();
  await page.getByPlaceholder(/用户名/).fill('admin');
  await page.getByPlaceholder('密码').fill(process.env.ADMIN_PW || 'aisre-dev-admin-pw');
  await page.getByRole('button', { name: /登\s*录/ }).last().click();
  await expect(page.getByText('Incidents', { exact: true })).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(1200);
  // 选一个 RESOLVED 行（必有诊断证据）——取 Root Cause 列非空的行
  const row = page.locator('.ant-table-row', { hasText: 'RESOLVED' }).first();
  await row.click();
  await expect(page.getByText(/详情 —/)).toBeVisible({ timeout: 10000 });
  await page.getByRole('tab', { name: /证据/ }).click();
  await page.waitForTimeout(800);
  // 结构化渲染：有结论句/折叠控件；不再以原始 JSON 起始长文
  await expect(page.getByText('原始 JSON').first()).toBeVisible();
  const rawJsonExposed = await page.evaluate(() => {
    const tabPane = document.querySelector('.ant-tabs-tabpane-active');
    return tabPane ? tabPane.textContent.trimStart().startsWith('{"status"') : false;
  });
  expect(rawJsonExposed).toBe(false);
});
