import { useEffect, useState } from 'react'
import { ArrowRight, X } from 'lucide-react'
import { api, assetUrl } from '../../shared/api'
import { Empty, Loading, ProductCard, money } from './shared'
import type { ShopProduct } from './shared'

import { savedProductIds } from './discovery-state'

async function fetchProducts(ids: string[]) {
  const results = await Promise.allSettled(
    ids.map((id) => api<ShopProduct>(`/shop/products/${id}`)),
  )
  return results.flatMap((result) => (result.status === 'fulfilled' ? [result.value] : []))
}
export function RecentlyViewed() {
  const [items, setItems] = useState<ShopProduct[]>([])
  useEffect(() => {
    let active = true
    fetchProducts(savedProductIds('ayna_recent').slice(0, 4)).then((values) => {
      if (active) setItems(values)
    })
    return () => {
      active = false
    }
  }, [])
  if (!items.length) return null
  return (
    <section className="shop-section">
      <div className="shop-section-title">
        <div>
          <p className="shop-kicker">WORTH ANOTHER LOOK</p>
          <h2>Recently on your radar.</h2>
        </div>
        <a href="#/shop">
          Keep exploring
          <ArrowRight size={16} />
        </a>
      </div>
      <div className="shop-product-grid">
        {items.map((p) => (
          <ProductCard product={p} key={p.id} />
        ))}
      </div>
    </section>
  )
}
export function ComparePage() {
  const [items, setItems] = useState<ShopProduct[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    fetchProducts(savedProductIds('ayna_compare'))
      .then(setItems)
      .finally(() => setLoading(false))
  }, [])
  function remove(id: string) {
    const ids = savedProductIds('ayna_compare').filter((value) => value !== id)
    localStorage.setItem('ayna_compare', JSON.stringify(ids))
    setItems((all) => all.filter((p) => p.id !== id))
  }
  return (
    <section className="shop-section">
      <p className="shop-kicker">A CLOSER PERSPECTIVE</p>
      <h1>Compare your good finds.</h1>
      <p className="shop-muted">
        Up to four products, side by side. Prices and availability are loaded fresh.
      </p>
      {loading ? (
        <Loading />
      ) : !items.length ? (
        <Empty
          title="A few good options."
          description="Use the compare button on product cards to see your choices side by side."
        />
      ) : (
        <div className="shop-table-wrap shop-compare-table">
          <table className="shop-table">
            <thead>
              <tr>
                <th>Product</th>
                {items.map((p) => (
                  <th key={p.id}>
                    <button
                      className="shop-icon-button"
                      aria-label={`Remove ${p.name} from comparison`}
                      onClick={() => remove(p.id)}
                    >
                      <X size={14} />
                    </button>
                    <a href={`#/products/${p.id}`}>
                      {p.images[0] && <img src={assetUrl(p.images[0].url)} alt={p.name} />}
                      <h3>{p.name}</h3>
                    </a>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ['Price', (p: ShopProduct) => money(p.price_minor, p.currency)],
                ['Category', (p: ShopProduct) => p.category],
                ['Brand', (p: ShopProduct) => p.brand || '—'],
                ['Available stock', (p: ShopProduct) => String(p.stock)],
                [
                  'Sizes & options',
                  (p: ShopProduct) => p.variants.map((v) => v.label).join(', ') || 'Standard',
                ],
                [
                  'Rating',
                  (p: ShopProduct) =>
                    p.review_count ? `${p.rating} / 5 · ${p.review_count} reviews` : 'New arrival',
                ],
                ['Seller', (p: ShopProduct) => p.seller_name],
                [
                  '3D preview',
                  (p: ShopProduct) => (p.model_asset_url ? 'Available' : 'Photo gallery'),
                ],
              ].map(([label, getValue]) => (
                <tr key={String(label)}>
                  <td>{String(label)}</td>
                  {items.map((p) => (
                    <td key={p.id}>{(getValue as (product: ShopProduct) => string)(p)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
