import { expect, test } from '@playwright/test'
import {
  assertQaWorkspace,
  login,
  registerFailureDiagnostics,
  requireQaCredentials,
} from './helpers'

registerFailureDiagnostics(test)

test('owner can generate, refine, apply, and roll back AI CRM changes', async ({ page }) => {
  test.slow()
  requireQaCredentials(test)

  await login(page)
  await assertQaWorkspace(page)
  await page.goto('/ai-architect')

  await expect(page.getByRole('heading', { name: 'Describe how your business works' })).toBeVisible()
  await page.getByPlaceholder('Explain your business process...').fill(
    'We run an education center with students, parents, groups, teachers, attendance, and monthly fees.',
  )
  await page.getByRole('button', { name: 'Send' }).click()
  await page.getByRole('button', { name: 'Generate CRM blueprint' }).click()
  await expect(page.getByRole('heading', { name: 'Business blueprint' })).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'Business blueprint' }).locator('..').getByText(/Education center with/i),
  ).toBeVisible()

  const formsProposal = page.getByRole('heading', { name: /Create starter forms/i }).locator('xpath=ancestor::article[1]')
  await formsProposal.getByRole('button', { name: 'Apply proposal' }).click()
  await expect(formsProposal.getByRole('button', { name: 'Applied' })).toBeVisible()

  await page.getByPlaceholder('Explain your business process...').fill('Add parent phone number to student intake')
  await page.getByRole('button', { name: 'Send' }).click()
  const refinementProposal = page.getByRole('heading', { name: /Add parent phone/i }).locator('xpath=ancestor::article[1]')
  await expect(refinementProposal).toBeVisible()
  await refinementProposal.getByRole('button', { name: 'Apply proposal' }).click()
  await expect(refinementProposal.getByRole('button', { name: 'Applied' })).toBeVisible()

  const latestHistoryItem = page.getByRole('heading', { name: 'AI change history' }).locator('..').locator('article').first()
  await expect(latestHistoryItem.getByText('update')).toBeVisible()
  await latestHistoryItem.getByRole('button', { name: 'Rollback' }).click()
  await expect(latestHistoryItem.getByText('rolled back')).toBeVisible()
})
