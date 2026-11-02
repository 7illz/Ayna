import type { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import ModelViewer from './ModelViewer'

const state = vi.hoisted(() => ({ pending: false }))

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useThree: () => ({
    camera: {
      position: { set: vi.fn(), applyAxisAngle: vi.fn(), multiplyScalar: vi.fn() },
      lookAt: vi.fn(),
      updateProjectionMatrix: vi.fn(),
    },
  }),
}))

vi.mock('@react-three/drei', () => ({
  Center: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Float: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  OrbitControls: () => <div />,
  useGLTF: () => {
    if (state.pending) throw new Promise(() => undefined)
    return { scene: {} }
  },
}))

beforeEach(() => {
  state.pending = false
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
})

test('falls back to the seller photo and exposes keyboard-operable controls', () => {
  render(<ModelViewer url="/broken.glb" photo="/front.png" />)
  expect(screen.getByAltText('Seller product photograph')).toHaveAttribute('src', '/front.png')
  expect(screen.getByText('3D unavailable. Use the product photographs.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Rotate 3D view left' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Rotate 3D view right' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Zoom 3D view in' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Zoom 3D view out' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Reset 3D view' })).toBeInTheDocument()
  expect(
    screen.getByText('AI-generated 3D preview, unobserved views may be estimated.'),
  ).toBeInTheDocument()
})

test('announces the 3D loading state', () => {
  vi.restoreAllMocks()
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({} as WebGLRenderingContext)
  state.pending = true
  render(<ModelViewer url="/model.glb" photo="/front.png" />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading 3D preview')
})
