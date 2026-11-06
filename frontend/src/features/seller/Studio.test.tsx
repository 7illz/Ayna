import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { Studio } from './Studio'
import type { Config, Job, Product } from '../../shared/api'

const { apiMock } = vi.hoisted(() => ({ apiMock: vi.fn() }))
vi.mock('../../shared/api', () => ({ api: apiMock, assetUrl: (url: string) => url }))
vi.mock('../../shared/LazyModelViewer', () => ({ LazyModelViewer: () => <div>Viewer</div> }))

afterEach(() => vi.useRealTimers())

test('polls one request at a time and ignores a late response after switching products', async () => {
  vi.useFakeTimers()
  const first: Product = {
    id: 'first',
    seller_id: 'seller',
    name: 'First product',
    category: 'bags',
    description: '',
    images: [],
    publish_status: 'generating',
    created_at: '2026-11-06T00:00:00Z',
    updated_at: '2026-11-06T00:00:00Z',
  }
  const second: Product = {
    ...first,
    id: 'second',
    name: 'Second product',
    publish_status: 'draft',
  }
  const job: Job = {
    id: 'job',
    product_id: first.id,
    provider: 'mock',
    status: 'queued',
    progress: 0,
    created_at: first.created_at,
    finished_at: null,
    error_code: null,
    model_asset_url: null,
    preview_asset_urls: [],
    disclosure: 'Dummy mock',
  }
  let resolvePoll!: (value: Job) => void
  const pending = new Promise<Job>((resolve) => {
    resolvePoll = resolve
  })
  apiMock.mockImplementation((path: string) => {
    if (path === '/products') return Promise.resolve([first, second])
    if (path === '/products/first/generation-jobs') return Promise.resolve([job])
    if (path === '/products/second/generation-jobs') return Promise.resolve([])
    if (path === '/generation-jobs/job') return pending
    return Promise.resolve(null)
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
  await act(async () => {
    render(<Studio config={config} />)
  })
  await act(async () => {
    await vi.advanceTimersByTimeAsync(4000)
  })
  expect(apiMock.mock.calls.filter(([path]) => path === '/generation-jobs/job')).toHaveLength(1)
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /Second product/ }))
  })
  await act(async () => {
    resolvePoll({ ...job, status: 'succeeded', progress: 100 })
  })
  expect(screen.getByText('Ready when you are')).toBeInTheDocument()
  expect(screen.queryByText('Generation succeeded · 100%')).not.toBeInTheDocument()
})
