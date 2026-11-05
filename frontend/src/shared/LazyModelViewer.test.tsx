import { Suspense } from 'react'
import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { LazyModelViewer } from './LazyModelViewer'

const state = vi.hoisted(() => ({ imports: 0 }))

vi.mock('./ModelViewer', () => {
  state.imports += 1
  return { default: () => <div>Loaded 3D viewer</div> }
})

test('keeps the heavy viewer module behind a React lazy boundary', async () => {
  expect(state.imports).toBe(0)
  render(
    <Suspense fallback={<div role="status">Loading viewer shell...</div>}>
      <LazyModelViewer />
    </Suspense>,
  )
  expect(await screen.findByText('Loaded 3D viewer')).toBeInTheDocument()
  expect(state.imports).toBe(1)
})
