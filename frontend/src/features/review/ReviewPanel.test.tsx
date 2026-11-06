import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { ReviewPanel } from './ReviewPanel'

const product = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  seller_id: '11111111-1111-4111-8111-111111111111',
  name: 'Ayna tote',
  category: 'bags',
  description: '',
  images: [],
  created_at: '2026-11-03T00:00:00Z',
  updated_at: '2026-11-03T00:00:00Z',
  publish_status: 'needs_review' as const,
}

test('shows uncertain views and requires a rejection reason', async () => {
  const quality = {
    product_id: product.id,
    job_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    status: 'needs_review' as const,
    metrics: { flags: ['front: likely color mismatch'] },
    notes: 'Advisory aligned-view checks only.',
    uncertain_views: ['back'],
    reviewed_by: null,
    reviewed_at: null,
  }
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  render(<ReviewPanel product={product} quality={quality} onReviewed={vi.fn()} />)
  expect(screen.getByText('front: likely color mismatch')).toBeInTheDocument()
  expect(screen.getByText('back')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Reject' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Add a reason')
  expect(fetchMock).not.toHaveBeenCalled()
})
