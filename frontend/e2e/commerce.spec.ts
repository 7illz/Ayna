import { expect, request as playwrightRequest, test } from '@playwright/test'
import path from 'node:path'

test('customer shops as a guest, registers, checks out COD, tracks and reviews an order', async ({
  page,
}, testInfo) => {
  test.setTimeout(150000)
  const suffix = `${testInfo.project.name}-${Date.now()}`
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Find your/ })).toBeVisible()
  await page.getByRole('searchbox', { name: 'Search products' }).fill('headphones')
  await page.getByRole('button', { name: 'Submit search' }).click()
  await expect(page.getByRole('heading', { name: /Results for/ })).toBeVisible()
  await page.getByRole('heading', { name: 'Wireless over-ear headphones', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: 'Wireless over-ear headphones', level: 1 }),
  ).toBeVisible()
  await page
    .locator('.shop-add-row')
    .getByRole('button', { name: 'Add to bag', exact: true })
    .click()
  await expect(page.locator('.shop-toast')).toContainText('Added to your bag')
  await page.getByRole('link', { name: /Shopping bag, 1 items/ }).click()
  await page.getByLabel('Have a promo code?').fill('WELCOME10')
  await page.getByRole('button', { name: 'Apply', exact: true }).click()
  await expect(page.locator('.shop-discount')).toBeVisible()
  await page.getByRole('link', { name: 'Continue to checkout' }).click()
  await expect(page.getByRole('heading', { name: 'A little more personal.' })).toBeVisible()
  await page.getByRole('main').getByRole('link', { name: 'Sign in', exact: true }).click()
  await page.getByRole('link', { name: 'Create an account', exact: true }).click()
  await page.getByLabel('Your name', { exact: true }).fill(`Browser Shopper ${suffix}`)
  await page.getByLabel('Email address', { exact: true }).fill(`buyer-${suffix}@example.com`)
  await page.getByLabel('Password', { exact: true }).fill('BrowserPassword2026!')
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Make it yours.' })).toBeVisible()
  await page.getByLabel('Full name', { exact: true }).fill('Ayna Browser Shopper')
  await page.getByLabel('Phone number', { exact: true }).fill('+8801700000000')
  await page.getByLabel('Street address', { exact: true }).fill('12 Sample Road')
  await page.getByLabel('City', { exact: true }).fill('Dhaka')
  await page.getByLabel('Postal code', { exact: true }).fill('1207')
  await page.getByLabel('Save this address for next time').check()
  await page.getByRole('button', { name: 'Place order', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Thanks for your order.' })).toBeVisible()
  const orderId = page.url().split('/orders/')[1].split('?')[0]
  const manager = await playwrightRequest.newContext({
    baseURL: process.env.E2E_API_URL || 'http://localhost:8000',
    extraHTTPHeaders: { Origin: new URL(page.url()).origin },
  })
  expect(
    (
      await manager.post('/api/v1/auth/login', {
        data: { email: 'admin@ayna.local', password: 'AynaDemo!2026' },
      })
    ).ok(),
  ).toBe(true)
  const order = await (await manager.get(`/api/v1/orders/${orderId}`)).json()
  for (const status of ['processing', 'shipped', 'delivered']) {
    expect(
      (
        await manager.post(`/api/v1/seller/order-items/${order.items[0].id}/fulfill`, {
          data: { status, tracking_number: `AY-${suffix}`, courier: 'Demo delivery' },
        })
      ).ok(),
    ).toBe(true)
  }
  expect(
    (
      await manager.post(`/api/v1/admin/orders/${orderId}`, { data: { action: 'mark_cod_paid' } })
    ).ok(),
  ).toBe(true)
  await manager.dispose()
  await page.getByRole('button', { name: 'Refresh status', exact: true }).click()
  await expect(page.getByText(`Demo delivery · Tracking: AY-${suffix}`)).toBeVisible()
  await expect(page.locator('.shop-status.delivered')).toBeVisible()
  await page.getByRole('link', { name: 'Wireless over-ear headphones', exact: true }).click()
  await page.getByLabel('Title', { exact: true }).fill(`Great everyday sound ${suffix}`)
  await page
    .getByLabel('Your review', { exact: true })
    .fill('Comfortable headphones and a very easy ordering experience.')
  await page.getByRole('button', { name: 'Submit review', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: `Great everyday sound ${suffix}`, exact: true }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Save to wishlist', exact: true }).click()
  await page.goto('/#/wishlist')
  await expect(
    page.getByRole('heading', { name: 'Wireless over-ear headphones', exact: true }),
  ).toBeVisible()
  await page
    .getByRole('button', { name: 'Compare Wireless over-ear headphones', exact: true })
    .click()
  await page.goto('/#/compare')
  await expect(page.getByRole('heading', { name: 'Compare your good finds.' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Available stock', exact: true })).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'Wireless over-ear headphones', exact: true }),
  ).toBeVisible()
  await page
    .getByRole('button', { name: 'Remove Wireless over-ear headphones from comparison' })
    .click()
  await expect(page.getByRole('heading', { name: 'A few good options.' })).toBeVisible()
  await page.goto('/')
  const recent = page
    .locator('section')
    .filter({ has: page.getByRole('heading', { name: 'Recently on your radar.' }) })
    .last()
  await expect(
    recent.getByRole('heading', { name: 'Wireless over-ear headphones', exact: true }),
  ).toBeVisible()
  await page.goto('/#/support')
  await page.getByLabel('Subject', { exact: true }).fill(`Browser help ${suffix}`)
  await page
    .getByLabel('How can we help?', { exact: true })
    .fill('Please confirm the delivery details for my sample order.')
  await page.getByRole('button', { name: 'Send message', exact: true }).click()
  await expect(page.getByRole('heading', { name: `Browser help ${suffix}` })).toBeVisible()
  await page.goto('/#/account')
  await expect(page.getByText('Home · Ayna Browser Shopper')).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: testInfo.outputPath('commerce-account.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  expect(errors).toEqual([])
})

test('seller creates photo listings and options; administrator manages the shop', async ({
  page,
}, testInfo) => {
  test.setTimeout(150000)
  const suffix = `${testInfo.project.name}-${Date.now()}`
  const name = `Browser everyday tote ${suffix}`
  await page.goto('/#/login')
  await page.getByRole('button', { name: 'seller', exact: true }).click()
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('link', { name: 'Seller workspace', exact: true }).click()
  await page.getByRole('button', { name: 'Add product', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Product name', { exact: true }).fill(name)
  await dialog.getByLabel('SKU', { exact: true }).fill(`BROWSER-${suffix}`)
  await dialog.getByLabel('Price (BDT)', { exact: true }).fill('1599')
  await dialog.getByLabel('Stock quantity', { exact: true }).fill('7')
  await dialog
    .getByLabel('Listing photographs')
    .setInputFiles(path.resolve('e2e/fixtures/front.png'))
  await dialog.getByLabel('List this product in the shop').check()
  await dialog.getByRole('button', { name: 'Save product', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  const row = page.getByRole('row').filter({ hasText: name })
  await expect(row.getByText('Live', { exact: true })).toBeVisible()
  await row.getByRole('button', { name: `Edit ${name}` }).click()
  await dialog.getByRole('button', { name: 'Sizes & options' }).click()
  await dialog.getByLabel('Option label', { exact: true }).fill('Small / Natural')
  await dialog.getByLabel('Option SKU', { exact: true }).fill(`BROWSER-${suffix}-S`)
  await dialog.getByLabel('Price', { exact: true }).fill('1599')
  await dialog.getByLabel('Stock', { exact: true }).fill('4')
  await dialog.getByRole('button', { name: 'Save option', exact: true }).click()
  await expect(dialog.getByRole('button', { name: /Small \/ Natural/ })).toBeVisible()
  await dialog.getByRole('button', { name: 'Close product editor' }).click()
  await page.getByRole('searchbox', { name: 'Search products' }).fill(name)
  await page.getByRole('button', { name: 'Submit search' }).click()
  await page.getByRole('heading', { name, exact: true }).click()
  const productId = page.url().split('/products/')[1].split('?')[0]
  await page.getByRole('button', { name: 'Small / Natural', exact: true }).click()
  await page
    .locator('.shop-add-row')
    .getByRole('button', { name: 'Add to bag', exact: true })
    .click()
  await expect(page.locator('.shop-toast')).toContainText('Added to your bag')
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.locator('.shop-toast')).toContainText('You have been signed out')
  await page.goto('/#/login')
  await page.getByRole('button', { name: 'admin', exact: true }).click()
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('link', { name: 'Administration', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Store administration' })).toBeVisible()
  await expect(page.getByText('Paid revenue', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'categories', exact: true }).click()
  const slug = `test-${Date.now()}`
  await page.getByLabel('Name', { exact: true }).fill(`Browser category ${suffix}`)
  await page.getByLabel('URL slug', { exact: true }).fill(slug)
  await page.getByRole('button', { name: 'Save category', exact: true }).click()
  await expect(
    page.getByRole('button', { name: new RegExp(`Browser category ${suffix}`) }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'coupons', exact: true }).click()
  const code = `E2E${Date.now()}`
  await page.getByLabel('Code', { exact: true }).fill(code)
  await page.getByLabel('Percentage discount', { exact: true }).fill('5')
  await page.getByRole('button', { name: 'Save promotion', exact: true }).click()
  await expect(page.getByRole('button', { name: new RegExp(code) })).toBeVisible()
  await page.getByRole('button', { name: 'users', exact: true }).click()
  await expect(page.getByRole('cell', { name: /Ayna Administrator/ })).toBeVisible()
  await page.getByRole('button', { name: 'support', exact: true }).click()
  const ticket = page.locator('.shop-admin-ticket').filter({ hasText: 'Browser help' }).first()
  if (await ticket.count()) {
    await ticket.getByLabel('Your response').fill('Your demo delivery details have been confirmed.')
    await ticket.getByRole('button', { name: 'Send response' }).click()
    await expect(page.locator('.shop-toast')).toContainText('Support reply saved')
  }
  await page.getByRole('button', { name: 'overview', exact: true }).click()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: testInfo.outputPath('commerce-admin.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  expect(
    (
      await page.request.delete(
        `${process.env.E2E_API_URL || 'http://localhost:8000'}/api/v1/seller/products/${productId}`,
        { headers: { Origin: new URL(page.url()).origin } },
      )
    ).ok(),
  ).toBe(true)
})
