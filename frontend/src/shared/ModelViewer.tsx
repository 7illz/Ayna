import { Component, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Canvas, useFrame, useLoader, useThree } from '@react-three/fiber'
import { RotateCcw, Move, Box, RotateCw, ZoomIn, ZoomOut } from 'lucide-react'
import { Box3, Vector3 } from 'three'
import type { Group } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

type CameraCommand = 'left' | 'right' | 'in' | 'out' | 'reset'

function Model({ url }: { url: string }) {
  const { scene } = useLoader(GLTFLoader, url)
  const offset = useMemo(() => {
    const center = new Box3().setFromObject(scene, true).getCenter(new Vector3())
    return [-center.x, -center.y, -center.z] as [number, number, number]
  }, [scene])
  return (
    <group position={offset}>
      <primitive object={scene} />
    </group>
  )
}

function FloatingPlaceholder() {
  const group = useRef<Group>(null)
  useFrame(({ clock }) => {
    if (!group.current) return
    const elapsed = clock.elapsedTime * 1.5
    group.current.rotation.x = Math.cos(elapsed / 4) * 0.35
    group.current.rotation.y = Math.sin(elapsed / 4) * 0.35
    group.current.rotation.z = Math.sin(elapsed / 4) * 0.14
    group.current.position.y = Math.sin(elapsed / 4) * 0.1
  })
  return (
    <group ref={group}>
      <mesh rotation={[0.2, 0.4, 0.1]}>
        <octahedronGeometry args={[1.1]} />
        <meshStandardMaterial color="#869e80" roughness={0.45} metalness={0.15} />
      </mesh>
    </group>
  )
}

function ViewerControls() {
  const { camera, gl } = useThree()
  const controls = useMemo(() => {
    const next = new OrbitControls(camera, gl.domElement)
    next.enableDamping = true
    next.enablePan = true
    next.minDistance = 2
    next.maxDistance = 8
    return next
  }, [camera, gl])
  useEffect(() => {
    return () => controls.dispose()
  }, [controls])
  useFrame(() => controls.update(), -1)
  return null
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
                <FloatingPlaceholder />
              )}
              <gridHelper args={[20, 20, '#d2d7c9', '#e1e4da']} position={[0, -1.2, 0]} />
              <CameraRig command={cameraCommand} sequence={cameraSequence} />
              <ViewerControls />
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
