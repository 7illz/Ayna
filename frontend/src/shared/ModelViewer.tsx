import { Component, Suspense, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { Center, Float, OrbitControls, useGLTF } from '@react-three/drei'
import { RotateCcw, Move, Box, RotateCw, ZoomIn, ZoomOut } from 'lucide-react'
import { Vector3 } from 'three'

type CameraCommand = 'left' | 'right' | 'in' | 'out' | 'reset'

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url)
  return (
    <Center>
      <primitive object={scene} />
    </Center>
  )
}

function CameraRig({ command, sequence }: { command: CameraCommand; sequence: number }) {
  const { camera } = useThree()
  useEffect(() => {
    if (!sequence) return
    if (command === 'reset') camera.position.set(3.2, 2.2, 3.2)
    if (command === 'left' || command === 'right')
      camera.position.applyAxisAngle(
        new Vector3(0, 1, 0),
        command === 'left' ? Math.PI / 8 : -Math.PI / 8,
      )
    if (command === 'in' || command === 'out')
      camera.position.multiplyScalar(command === 'in' ? 0.8 : 1.25)
    camera.lookAt(0, 0, 0)
    camera.updateProjectionMatrix()
  }, [camera, command, sequence])
  return null
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
  const [cameraCommand, setCameraCommand] = useState<CameraCommand>('reset')
  const [cameraSequence, setCameraSequence] = useState(0)
  const [webgl] = useState(supportsWebGL)
  function moveCamera(command: CameraCommand) {
    setCameraCommand(command)
    setCameraSequence((value) => value + 1)
    if (command === 'reset') setReset((value) => value + 1)
  }
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
        {url ? 'AI-GENERATED 3D PREVIEW' : 'STUDIO PREVIEW'}
      </span>
      {webgl ? (
        <ViewerBoundary key={`${url}-${reset}`} fallback={fallback}>
          <Suspense
            fallback={
              <div className="viewer-fallback" role="status">
                Loading 3D preview...
              </div>
            }
          >
            <Canvas
              camera={{ position: [3.2, 2.2, 3.2], fov: 42 }}
              dpr={[1, 1.5]}
              aria-label="Rotatable Ayna product model"
              tabIndex={0}
            >
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
              <CameraRig command={cameraCommand} sequence={cameraSequence} />
              <OrbitControls makeDefault enablePan minDistance={2} maxDistance={8} />
            </Canvas>
          </Suspense>
        </ViewerBoundary>
      ) : (
        fallback
      )}
      <div className="viewer-toolbar">
        <span>
          <Move size={14} /> Drag to rotate or pan. Scroll to zoom.
        </span>
        <div className="viewer-buttons" aria-label="3D view controls">
          <button className="icon-button" aria-label="Rotate 3D view left" onClick={() => moveCamera('left')}>
            <RotateCcw size={16} />
          </button>
          <button className="icon-button" aria-label="Rotate 3D view right" onClick={() => moveCamera('right')}>
            <RotateCw size={16} />
          </button>
          <button className="icon-button" aria-label="Zoom 3D view in" onClick={() => moveCamera('in')}>
            <ZoomIn size={16} />
          </button>
          <button className="icon-button" aria-label="Zoom 3D view out" onClick={() => moveCamera('out')}>
            <ZoomOut size={16} />
          </button>
          <button className="icon-button" aria-label="Reset 3D view" onClick={() => moveCamera('reset')}>
            <RotateCcw size={16} />
          </button>
        </div>
      </div>
      <p className="viewer-disclosure">
        AI-generated 3D preview, unobserved views may be estimated.
      </p>
    </div>
  )
}
