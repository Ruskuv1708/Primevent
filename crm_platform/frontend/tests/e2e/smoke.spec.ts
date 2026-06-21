import { test, expect } from '@playwright/test'
import {
  assertQaWorkspace,
  login,
  registerFailureDiagnostics,
  requireQaCredentials,
} from './helpers'

registerFailureDiagnostics(test)

test('login and navigate core pages', async ({ page }) => {
  requireQaCredentials(test)
  await login(page)
  await assertQaWorkspace(page)

  await page.goto('/requests')
  await expect(page.getByRole('heading', { name: 'All Requests' })).toBeVisible()

  await page.goto('/departments')
  await expect(page.getByRole('heading', { name: 'Departments & Rankings' })).toBeVisible()

  await page.goto('/forms')
  await expect(page.getByRole('heading', { name: 'Form Templates' })).toBeVisible()

  await page.goto('/reports')
  await expect(page.getByRole('heading', { name: 'Reports Library' })).toBeVisible()

  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible()

  await page.getByRole('button', { name: 'Profile', exact: true }).click()
  await expect(page.getByRole('heading', { name: /My Profile/i })).toBeVisible()
})

test('admin can create department', async ({ page }) => {
  requireQaCredentials(test)
  await login(page)
  await assertQaWorkspace(page)

  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible()

  const deptName = `E2E Dept ${Date.now()}`
  await page.getByPlaceholder('Department name').fill(deptName)
  await page.getByPlaceholder('Description (optional)').fill('Created by Playwright')
  await page.getByRole('button', { name: 'Add' }).click()

  await expect(page.getByRole('cell', { name: deptName })).toBeVisible()
})

test('mobile shell stays navigable without horizontal overflow', async ({ page }) => {
  requireQaCredentials(test)
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page)
  await assertQaWorkspace(page)

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)

  await page.getByRole('button', { name: 'Me', exact: true }).click()
  await expect(page.getByText('Account & Preferences')).toBeVisible()
})
