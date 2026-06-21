import { expect, type Page, type TestType } from '@playwright/test'

export const qaAdmin = {
  email: process.env.E2E_ADMIN_EMAIL!,
  password: process.env.E2E_ADMIN_PASSWORD!,
}

export const apiBaseUrl = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8008'

export const requireQaCredentials = (test: TestType<any, any>) => {
  test.skip(
    !qaAdmin.email || !qaAdmin.password,
    'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run QA workspace E2E tests.',
  )
}

export const login = async (page: Page, email = qaAdmin.email, password = qaAdmin.password) => {
  await page.goto('/')
  await page.getByPlaceholder('Email').fill(email)
  await page.getByPlaceholder('Password').fill(password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await page.waitForURL('**/home')
  await expect(page.getByRole('button', { name: /Profile|Me/ })).toBeVisible()
}

export const assertQaWorkspace = async (page: Page) => {
  const token = await page.evaluate(() => localStorage.getItem('crm_token'))
  expect(token, 'QA login should produce a token before workspace checks').toBeTruthy()

  const meResponse = await page.request.get(`${apiBaseUrl}/access/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(meResponse.ok(), 'QA account lookup should succeed').toBeTruthy()
  const currentUser = await meResponse.json()
  expect(currentUser.email).toBe(qaAdmin.email)
  expect(currentUser.workspace_id).toBeTruthy()

  const workspaceResponse = await page.request.get(`${apiBaseUrl}/superadmin/workspaces/${currentUser.workspace_id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(workspaceResponse.ok(), 'QA workspace lookup should succeed').toBeTruthy()
  const workspace = await workspaceResponse.json()
  expect(workspace.name).toBe('QA Workspace')
}

export const registerFailureDiagnostics = (test: TestType<any, any>) => {
  test.afterEach(async ({ page }, testInfo) => {
    if (testInfo.status === testInfo.expectedStatus) return
    await testInfo.attach('current-url', {
      body: Buffer.from(page.url()),
      contentType: 'text/plain',
    })
  })
}
