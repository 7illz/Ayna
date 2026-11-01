import { Component, Suspense, useState } from 'react'
import type { ReactNode } from 'react'
import { Canvas } from '@react-three/fiber'
import { Center, Float, OrbitControls, useGLTF } from '@react-three/drei'
import { RotateCcw, Move, Box } from 'lucide-react'

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url)
  return (
    <Center>
      <primitive object={scene} />
    </Center>
  )
}

class ViewerBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

function supportsWebGL() {
  try {
    const canvas = document.createElement('canvas')
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    return false
  }
}

export default function ModelViewer({ url, photo }: { url?: string | null; photo?: string }) {
  const [reset, setReset] = useState(0)
  const [webgl] = useState(supportsWebGL)
  const fallback = (
    <div className="viewer-fallback">
      {photo ? (
        <img src={photo} alt="Seller product photograph" />
      ) : (
        <Box size={64} strokeWidth={1} />
      )}
      <p>
        {url
          ? '3D unavailable. Use the product photographs.'
          : 'Your product preview will appear here.'}
      </p>
    </div>
  )
  return (
    <div className="viewer" aria-label="Interactive 3D product preview">
      <span className="viewer-label">
        <span />
        {url ? 'DUMMY MODEL · MOCK' : 'STUDIO PREVIEW'}
      </span>
      {webgl ? (
        <ViewerBoundary key={`${url}-${reset}`} fallback={fallback}>
          <Suspense fallback={<div className="viewer-fallback">Loading 3D preview…</div>}>
            <Canvas camera={{ position: [3.2, 2.2, 3.2], fov: 42 }} dpr={[1, 1.5]}>
              <ambientLight intensity={1.5} />
              <directionalLight position={[4, 6, 2]} intensity={3} />
              {url ? (
                <Model url={url} />
              ) : (
                <Float speed={1.5} rotationIntensity={0.35}>
                  <mesh rotation={[0.2, 0.4, 0.1]}>
                    <octahedronGeometry args={[1.1]} />
                    <meshStandardMaterial color="#869e80" roughness={0.45} metalness={0.15} />
                  </mesh>
                </Float>
              )}
              <gridHelper args={[20, 20, '#d2d7c9', '#e1e4da']} position={[0, -1.2, 0]} />
              <OrbitControls makeDefault enablePan={false} minDistance={2} maxDistance={8} />
            </Canvas>
          </Suspense>
        </ViewerBoundary>
      ) : (
        fallback
      )}
      <div className="viewer-toolbar">
        <span>
          <Move size={14} /> Drag to rotate · Scroll to zoom
        </span>
        <button
          className="icon-button"
          aria-label="Reset 3D view"
          onClick={() => setReset((v) => v + 1)}
        >
          <RotateCcw size={16} />
        </button>
      </div>
    </div>
  )
}
