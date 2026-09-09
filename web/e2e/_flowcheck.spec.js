import { test, expect } from '@playwright/test';

// 流程图核查：登录 → 点行 → 诊断流程 Tab。断言节点结构 + 详情交互 + 失败突出。
test('diagnosis flow renders nodes with detail switching', async ({ page }) => {
  test.setTimeout(60000);
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: '登录' }).click();
  await page.getByPlaceholder(/用户名/).fill('admin');
  await page.getByPlaceholder('密码').fill(process.env.ADMIN_PW || 'aisre-dev-admin-pw');
  await page.getByRole('button', { name: /登\s*录/ }).last().click();
  await page.waitForTimeout(2500);
  const row = page.locator('.ant-table-row', { hasText: 'RESOLVED' }).first();
  await row.click();
  await page.getByText(/详情 —/).waitFor({ timeout: 10000 });
  await page.getByRole('tab', { name: /诊断流程/ }).click();
  await page.waitForTimeout(1200);
  const pane = page.locator('.ant-tabs-tabpane-active');
  // 节点数 = 该事件 toolCalls 数；标题与结论句都在
  const nodes = await page.locator('.ant-steps-item').count();
  expect(nodes).toBeGreaterThanOrEqual(1);
  const text = await pane.textContent();
  expect(text).toContain('查询 Prometheus');
  // 详情卡默认展开第一个节点，点其它节点可切换
  expect(text.includes('参数：') || text.includes('结果：')).toBe(true);
  await page.locator('.ant-steps-item').nth(Math.min(1, nodes - 1)).click();
  await page.waitForTimeout(500);
  expect(await pane.textContent()).toContain('参数：');
  await page.screenshot({ path: 'test-results/flow_tab.png' });
});

test('failed nodes highlighted red and auto-expanded', async ({ page }) => {
  test.setTimeout(60000);
  page.on('console', m => { if (m.text().includes('401-debug')) console.log('CAUGHT_401:', m.text()); });
  page.on('pageerror', e => console.log('PAGE_ERROR:', String(e.stack || e.message).slice(0, 400)));
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: '登录' }).click();
  await page.getByPlaceholder(/用户名/).fill('admin');
  await page.getByPlaceholder('密码').fill(process.env.ADMIN_PW || 'aisre-dev-admin-pw');
  await page.getByRole('button', { name: /登\s*录/ }).last().click();
  await page.waitForTimeout(2500);
  // 动态找一个诊断链里有失败环节的事件（数据会演进，不能钉死 id）
  const failedIncident = await page.evaluate(async () => {
    const token = localStorage.getItem('aisre_token');
    const list = await (await fetch('/api/v1/incidents', { headers: { Authorization: `Bearer ${token}` } })).json();
    for (const inc of list.slice(0, 30)) {
      const calls = await (await fetch(`/api/v1/incidents/${inc.id}/tool-calls`, { headers: { Authorization: `Bearer ${token}` } })).json();
      if (calls.some((t) => t.status !== 'SUCCESS')) return inc.id;
    }
    return null;
  });
  test.skip(failedIncident === null, '近 30 条事件中暂无带失败环节的——数据演进正常，无假失败');
  const row = page.locator('.ant-table-row', { hasText: `INC-${String(failedIncident).padStart(4, '0')}` }).first();
  await row.click();
  await page.getByText(/详情 —/).waitFor({ timeout: 10000 });
  await page.getByRole('tab', { name: /诊断流程/ }).click();
  await expect(page.locator('.ant-steps-item-error').first()).toBeVisible({ timeout: 5000 });
  const errNodes = await page.locator('.ant-steps-item-error').count();
  const text = await page.locator('.ant-tabs-tabpane-active').textContent();
  expect(errNodes).toBeGreaterThanOrEqual(1);
  expect(text).toContain('执行失败'); // 失败环节默认展开错误详情
  await page.screenshot({ path: 'test-results/flow_failed.png' });
});
