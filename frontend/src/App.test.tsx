import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, test, expect } from 'vitest'
import App from './App'
import { CreateProduct } from './features/seller/CreateProduct'
import type { Config } from './shared/api'

vi.mock('./shared/ModelViewer', () => ({ default: () => <div>3D preview placeholder</div> }))
const config: Config = {
  brand: 'Ayna',
  provider: 'mock',
  min_images: 2,
  max_images: 5,
  max_image_bytes: 10485760,
  max_image_pixels: 20000000,
  dev_auth_enabled: true,
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
