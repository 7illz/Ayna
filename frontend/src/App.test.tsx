import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, test, expect } from 'vitest'
import { StudioApp as App } from './App'
import { CreateProduct } from './features/seller/CreateProduct'
import type { Config } from './shared/api'

vi.mock('./shared/ModelViewer', () => ({ default: () => <div>3D preview placeholder</div> }))

test('hosted configuration is labelled paid and authenticated sellers can create products', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async (input: string | URL | Request) =>
        new Response(
          JSON.stringify(
            String(input).endsWith('/config')
              ? {
                  ...config,
                  provider: 'meshy',
                  dev_auth_enabled: false,
                  seller_authenticated: true,
                }
              : [],
          ),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
    ),
  )
  render(<App />)
  expect(await screen.findByText('Meshy enabled')).toBeInTheDocument()
  expect(screen.queryByText('Mock mode is on')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^Add product$/ })).toBeEnabled()
})
const config: Config = {
  brand: 'Ayna',
  provider: 'mock',
  min_images: 2,
  max_images: 5,
  max_image_bytes: 10485760,
  max_image_pixels: 20000000,
  dev_auth_enabled: true,
  seller_authenticated: false,
}

test('Ayna studio connects, opens upload dialog, and navigates to approved storefront', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async (url: string) =>
        new Response(JSON.stringify(url.endsWith('/config') ? config : []), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    ),
  )
  render(<App />)
  expect(await screen.findByRole('heading', { name: 'Product studio.' })).toBeInTheDocument()
  expect(await screen.findByText('Start with something yours.')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Add product' }))
  expect(screen.getByRole('dialog')).toBeInTheDocument()
  expect(screen.getByLabelText('Product name')).toHaveFocus()
  await userEvent.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Storefront' }))
  expect(await screen.findByText('A little anticipation.')).toBeInTheDocument()
})

test('connection failures can be retried', async () => {
  const fetchMock = vi
    .fn()
    .mockRejectedValueOnce(new Error('Offline'))
    .mockImplementation(
      async (url: string) =>
        new Response(JSON.stringify(url.endsWith('/config') ? config : []), { status: 200 }),
    )
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Offline')
  await userEvent.click(screen.getByRole('button', { name: 'Retry connection' }))
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'Product studio.' })).toBeInTheDocument(),
  )
})

test('one photograph cannot submit a generation-ready product', async () => {
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  render(<CreateProduct config={config} onClose={vi.fn()} onCreated={vi.fn()} />)
  await userEvent.type(screen.getByLabelText('Product name'), 'A tote')
  await userEvent.upload(
    screen.getByLabelText('Product photographs'),
    new File(['png'], 'front.png', { type: 'image/png' }),
  )
  await userEvent.click(screen.getByRole('button', { name: 'Create product' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Choose 2–5')
  expect(fetchMock).not.toHaveBeenCalled()
})

test('approved storefront loads public detail and preserves original gallery', async () => {
  const product = {
    id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    name: 'Ayna verified tote',
    category: 'bags',
    description: 'Seller photograph remains authoritative.',
    images: [
      {
        id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
        url: '/api/v1/store/products/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/images/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
        view_tag: 'front',
      },
    ],
    model_asset_url: '/api/v1/store/products/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/model',
    disclosure: 'AI-generated 3D preview; unobserved views may be estimated.',
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string | URL | Request) => {
      const url = String(input)
      const body = url.endsWith('/config')
        ? config
        : url.endsWith('/api/v1/products')
          ? []
          : url.endsWith('/store/products')
            ? [product]
            : product
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
  render(<App />)
  await screen.findByRole('heading', { name: 'Product studio.' })
  await userEvent.click(screen.getByRole('button', { name: 'Storefront' }))
  await userEvent.click(await screen.findByRole('button', { name: /Open Ayna verified tote/ }))
  expect(await screen.findByText('Original seller photographs')).toBeInTheDocument()
  expect(screen.getByLabelText('Original product photo gallery')).toBeInTheDocument()
  expect(screen.getByText(product.disclosure)).toBeInTheDocument()
})
