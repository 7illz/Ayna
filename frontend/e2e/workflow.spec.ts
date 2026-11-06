import { test, expect } from '@playwright/test'
import path from 'node:path'

test('seller uploads, queues, reviews, and opens an approved 3D preview', async ({
  page,
}, testInfo) => {
  const name = `Ayna browser tote ${testInfo.project.name} ${Date.now()}`
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/#/studio')
  await expect(page).toHaveTitle('Ayna')
  await page.getByRole('button', { name: 'Add product', exact: true }).click()
  await page.getByLabel('Product name').fill(name)
  await page
    .getByLabel('Description', { exact: true })
    .fill('Original procedural photos for the bootstrap browser smoke.')
  await page
    .getByLabel('Product photographs')
    .setInputFiles([path.resolve('e2e/fixtures/front.png'), path.resolve('e2e/fixtures/side.png')])
  await page.getByRole('button', { name: 'Create product', exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  await page.getByRole('combobox', { name: 'Direction for photo 2' }).selectOption('left')
  await expect(page.getByRole('combobox', { name: 'Direction for photo 2' })).toHaveValue('left')
  await page.getByRole('button', { name: 'Generate mock preview' }).click()
  await expect(page.getByText('Generation succeeded · 100%')).toBeVisible({ timeout: 60000 })
  await expect(page.getByText('DUMMY MODEL · MOCK')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Model inspection renders' })).toBeVisible()
  await expect(page.getByAltText('Generated model inspection view 1')).toBeVisible()
  const canvas = page.locator('.viewer canvas')
  await expect(canvas).toBeVisible()
  const beforeRotation = await canvas.screenshot()
  await page.getByRole('button', { name: 'Rotate 3D view left' }).click()
  await expect.poll(async () => (await canvas.screenshot()).equals(beforeRotation)).toBe(false)
  const beforeZoom = await canvas.screenshot()
  await page.getByRole('button', { name: 'Zoom 3D view in' }).click()
  await expect.poll(async () => (await canvas.screenshot()).equals(beforeZoom)).toBe(false)
  await page.getByRole('button', { name: 'Reset 3D view' }).click()
  await page.getByLabel('Review notes').fill('Dummy fixture checked; no product fidelity claim.')
  await page.getByRole('button', { name: 'Approve preview' }).click()
  await expect(page.locator('.product-row.selected .status')).toHaveText('approved')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: testInfo.outputPath('ayna-studio.png'), fullPage: true })
  await page.getByRole('button', { name: 'Storefront', exact: true }).click()
  await page.getByRole('button', { name: new RegExp(name) }).click()
  await expect(page.locator('.store-detail')).toBeVisible()
  await expect(page.locator('.store-detail .photo-strip img')).toHaveCount(2)
  await expect(page.locator('.store-detail .disclosure')).toContainText('not a reconstruction')
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  )
  expect(overflow).toBe(false)
  expect(errors).toEqual([])
  await page.route('**/api/v1/store/products/*/model', (route) =>
    route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: '{"detail":"Model unavailable"}',
    }),
  )
  await page.reload()
  await page.getByRole('button', { name: 'Storefront', exact: true }).click()
  await page.getByRole('button', { name: new RegExp(name) }).click()
  await expect(page.getByText('3D unavailable. Use the product photographs.')).toBeVisible()
  await expect(
    page.getByRole('img', { name: 'Seller product photograph', exact: true }),
  ).toBeVisible()
})
