import { expect, test } from '@playwright/test'
import {
  assertQaWorkspace,
  login,
  registerFailureDiagnostics,
  requireQaCredentials,
} from './helpers'

registerFailureDiagnostics(test)

test('profile owns UI mode and logout controls', async ({ page }) => {
  requireQaCredentials(test)
  await login(page)
  await assertQaWorkspace(page)

  await expect(page.getByRole('button', { name: /UI:/ })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Logout' })).toHaveCount(0)

  await page.getByRole('button', { name: 'Profile', exact: true }).click()
  await expect(page.getByText('Account & Preferences')).toBeVisible()
  await expect(page.getByRole('button', { name: /1C Table/i })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Logout' })).toBeVisible()
})
