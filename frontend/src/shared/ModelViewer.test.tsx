import type { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import ModelViewer from './ModelViewer'

const state = vi.hoisted(() => ({ pending: false, failed: false }))

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useFrame: vi.fn(),
  useLoader: () => {
    if (state.pending) throw new Promise(() => undefined)
    if (state.failed) throw new Error('simulated GLB failure')
    return { scene: {} }
  },
  useThree: () => ({
    camera: {
      position: { set: vi.fn(), applyAxisAngle: vi.fn(), multiplyScalar: vi.fn() },
      lookAt: vi.fn(),
      updateProjectionMatrix: vi.fn(),
    },
    gl: { domElement: document.createElement('canvas') },
  }),
}))

vi.mock('three/addons/controls/OrbitControls.js', () => ({
  OrbitControls: class {
    enableDamping = false
    enablePan = false
    minDistance = 0
    maxDistance = 0
    update = vi.fn()
    dispose = vi.fn()
  },
}))

vi.mock('three/addons/loaders/GLTFLoader.js', () => ({ GLTFLoader: class {} }))

beforeEach(() => {
  state.pending = false
  state.failed = false
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

test('falls back to the seller photograph when GLB loading fails', async () => {
  vi.restoreAllMocks()
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({} as WebGLRenderingContext)
  state.failed = true
  render(<ModelViewer url="/broken.glb" photo="/front.png" />)
  expect(await screen.findByAltText('Seller product photograph')).toHaveAttribute(
    'src',
    '/front.png',
  )
  expect(screen.getByText('3D unavailable. Use the product photographs.')).toBeInTheDocument()
})
