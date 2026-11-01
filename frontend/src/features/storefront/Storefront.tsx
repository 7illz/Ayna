import { lazy, Suspense, useEffect, useState } from 'react'
import { ShoppingBag, ArrowUpRight } from 'lucide-react'
import { api, assetUrl } from '../../shared/api'
import type { PublicProduct } from '../../shared/api'

const ModelViewer = lazy(() => import('../../shared/ModelViewer'))

export function Storefront() {
  const [products, setProducts] = useState<PublicProduct[]>([])
  const [selected, setSelected] = useState<PublicProduct | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    api<PublicProduct[]>('/store/products')
      .then(setProducts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">A NEW PERSPECTIVE</p>
          <h1>
            The collection<span>.</span>
          </h1>
          <p className="muted">Explore seller-approved product previews.</p>
        </div>
        <span className="tag">DEMO STOREFRONT</span>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {loading ? (
        <p>Loading collection…</p>
      ) : products.length === 0 ? (
        <div className="empty-store">
          <ShoppingBag size={44} strokeWidth={1} />
          <h2>A little anticipation.</h2>
          <p className="muted">
            Approved products will appear here. Create and review one in the studio.
          </p>
        </div>
      ) : (
        <div className="store-grid">
          {products.map((p) => (
            <button className="store-card" key={p.id} onClick={() => setSelected(p)}>
              {p.images[0] && <img src={assetUrl(p.images[0].url)} alt={p.name} />}
              <div>
                <span className="eyebrow">{p.category}</span>
                <h3>
                  {p.name}
                  <ArrowUpRight size={18} />
                </h3>
                <p className="muted small">AI-generated 3D preview · dummy model</p>
              </div>
            </button>
          ))}
        </div>
      )}
      {selected && (
        <section className="store-detail">
          <div className="section-heading">
            <h2>{selected.name}</h2>
            <button className="button secondary" onClick={() => setSelected(null)}>
              Close preview
            </button>
          </div>
          <Suspense fallback={<div className="viewer-fallback">Loading viewer…</div>}>
            <ModelViewer
              url={selected.model_asset_url ? assetUrl(selected.model_asset_url) : null}
              photo={selected.images[0] ? assetUrl(selected.images[0].url) : undefined}
            />
          </Suspense>
          <p className="disclosure">{selected.disclosure}</p>
          <div className="photo-strip">
            {selected.images.map((i) => (
              <img key={i.id} src={assetUrl(i.url)} alt={`${selected.name}, ${i.view_tag} view`} />
            ))}
          </div>
          <p>{selected.description}</p>
        </section>
      )}
    </>
  )
}
