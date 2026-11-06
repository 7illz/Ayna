/* eslint-disable react-refresh/only-export-components -- Context, hooks, and UI primitives share this module. */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { components } from '../../shared/api-schema'
import { api, assetUrl } from '../../shared/api'
import { Heart, ShoppingBag, Star, ArrowRight, Package, LoaderCircle, Columns2 } from 'lucide-react'
import { compareProduct } from './discovery-state'

export type ShopProduct = components['schemas']['ShopProduct']
export type StoreConfig = components['schemas']['StoreConfig']
export type User = components['schemas']['UserOut']
export type Cart = components['schemas']['CartOut']
export type Order = components['schemas']['OrderOut']
export type Address = components['schemas']['AddressOut']
export type AddressInput = components['schemas']['AddressIn']
export type Review = components['schemas']['ReviewOut']
export type Ticket = components['schemas']['TicketOut']
export type Notification = components['schemas']['NotificationOut']
export type Coupon = components['schemas']['CouponOut']
export type Category = components['schemas']['CategoryIn']
export type ProductPage = components['schemas']['ProductPage']

export const money = (minor: number, currency = 'BDT') =>
  new Intl.NumberFormat('en-BD', {
    style: 'currency',
    currency,
    maximumFractionDigits: minor % 100 ? 2 : 0,
  }).format(minor / 100)
export const date = (value: string) =>
  new Date(value).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
export function go(path: string) {
  window.location.hash = path
}
export function useRoute() {
  const [route, setRoute] = useState(window.location.hash.slice(1) || '/')
  useEffect(() => {
    const change = () => {
      setRoute(window.location.hash.slice(1) || '/')
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', change)
    return () => window.removeEventListener('hashchange', change)
  }, [])
  const [path, query = ''] = route.split('?')
  return { path, params: new URLSearchParams(query) }
}

export function useResource<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(!!path)
  const reload = useCallback(async () => {
    if (!path) return
    setLoading(true)
    setError('')
    try {
      const result = await api<T>(path)
      setData(result)
      return result
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }, [path])
  useEffect(() => {
    setData(null)
    void reload()
  }, [reload])
  return { data, setData, error, loading, reload }
}

type ShopContextType = {
  user: User | null
  setUser: (user: User | null) => void
  authLoading: boolean
  config: StoreConfig | null
  reloadConfig: () => Promise<unknown>
  cart: Cart | null
  setCart: (cart: Cart) => void
  reloadCart: () => Promise<unknown>
  notify: (message: string) => void
}
const ShopContext = createContext<ShopContextType | null>(null)
export function ShopProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [cart, setCart] = useState<Cart | null>(null)
  const [toast, setToast] = useState('')
  const config = useResource<StoreConfig>('/shop/config')
  const reloadCart = useCallback(async () => {
    try {
      setCart(await api<Cart>('/cart'))
    } catch {
      /* Cart page shows connection errors. */
    }
  }, [])
  useEffect(() => {
    api<User>('/auth/me')
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setAuthLoading(false))
    void reloadCart()
  }, [reloadCart])
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(''), 4500)
    return () => clearTimeout(timer)
  }, [toast])
  return (
    <ShopContext.Provider
      value={{
        user,
        setUser,
        authLoading,
        config: config.data,
        reloadConfig: config.reload,
        cart,
        setCart,
        reloadCart,
        notify: setToast,
      }}
    >
      {config.error && (
        <div className="shop-network" role="alert">
          Could not connect to Ayna. <button onClick={config.reload}>Retry connection</button>
        </div>
      )}
      {children}
      {toast && (
        <div className="shop-toast" role="status">
          {toast}
          <button onClick={() => setToast('')} aria-label="Dismiss notification">
            ×
          </button>
        </div>
      )}
    </ShopContext.Provider>
  )
}
export function useShop() {
  const value = useContext(ShopContext)
  if (!value) throw new Error('Shop provider is required')
  return value
}

export function useAction() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function run<T>(task: () => Promise<T>): Promise<T | undefined> {
    setBusy(true)
    setError('')
    try {
      return await task()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return { busy, error, run, setError }
}
export function Notice({ error }: { error?: string }) {
  return error ? (
    <div className="shop-error" role="alert">
      {error}
    </div>
  ) : null
}
export function Loading() {
  return (
    <div className="shop-loading" role="status">
      <LoaderCircle size={24} className="spin" /> Loading…
    </div>
  )
}
export function Empty({
  title,
  description,
  action = 'Explore the collection',
  href = '/',
}: {
  title: string
  description: string
  action?: string
  href?: string
}) {
  return (
    <div className="shop-empty">
      <ShoppingBag size={42} strokeWidth={1} />
      <h2>{title}</h2>
      <p>{description}</p>
      <a className="shop-button" href={`#${href}`}>
        {action}
        <ArrowRight size={16} />
      </a>
    </div>
  )
}
export function RequireAccount({
  children,
  seller = false,
  admin = false,
}: {
  children: ReactNode
  seller?: boolean
  admin?: boolean
}) {
  const { user, authLoading } = useShop()
  if (authLoading) return <Loading />
  if (!user)
    return (
      <Empty
        title="A little more personal."
        description="Sign in to manage your account and keep everything together."
        action="Sign in"
        href={`/login?next=${encodeURIComponent(window.location.hash.slice(1) || '/')}`}
      />
    )
  if ((seller && !['seller', 'admin'].includes(user.role)) || (admin && user.role !== 'admin'))
    return (
      <Empty
        title="Access is restricted."
        description="This workspace requires the appropriate account permissions."
      />
    )
  return <>{children}</>
}

export function ProductCard({ product }: { product: ShopProduct }) {
  const { user, notify, setCart } = useShop()
  const action = useAction()
  async function wish() {
    if (!user) {
      go('/login')
      return
    }
    await action.run(async () => {
      await api(`/wishlist/${product.id}`, { method: 'PUT' })
      notify('Saved to your wishlist')
    })
  }
  async function add() {
    if (product.variants.length) {
      go(`/products/${product.id}`)
      return
    }
    await action.run(async () => {
      setCart(
        await api<Cart>('/cart/items', {
          method: 'POST',
          body: JSON.stringify({ product_id: product.id, quantity: 1 }),
        }),
      )
      notify('Added to your bag')
    })
  }
  return (
    <article className="shop-product-card">
      <div className="shop-product-image">
        <a href={`#/products/${product.id}`}>
          {product.images[0] ? (
            <img loading="lazy" src={assetUrl(product.images[0].url)} alt={product.name} />
          ) : (
            <div className="shop-image-placeholder">
              <Package size={48} />
            </div>
          )}
        </a>
        {product.compare_at_minor && product.compare_at_minor > product.price_minor && (
          <span className="shop-sale">
            -{Math.round((1 - product.price_minor / product.compare_at_minor) * 100)}%
          </span>
        )}
        <button
          className="shop-wish"
          aria-label={`Save ${product.name} to wishlist`}
          onClick={wish}
          disabled={action.busy}
        >
          <Heart size={18} />
        </button>
        <button
          className="shop-compare-button"
          aria-label={`Compare ${product.name}`}
          onClick={() => compareProduct(product.id, notify)}
        >
          <Columns2 size={16} />
        </button>
        <button className="shop-quick-add" onClick={add} disabled={action.busy || !product.stock}>
          {product.stock
            ? product.variants.length
              ? 'Choose options'
              : 'Add to bag'
            : 'Out of stock'}
          <ShoppingBag size={15} />
        </button>
      </div>
      <div className="shop-product-meta">
        <p>{product.category === 'shirts' ? 'Clothing' : product.category}</p>
        <a href={`#/products/${product.id}`}>
          <h3>{product.name}</h3>
        </a>
        <div className="shop-price">
          <strong>{money(product.price_minor, product.currency)}</strong>
          {product.compare_at_minor && (
            <del>{money(product.compare_at_minor, product.currency)}</del>
          )}
        </div>
        <div className="shop-rating">
          <Star size={12} fill={product.review_count ? 'currentColor' : 'none'} />
          {product.review_count ? `${product.rating} (${product.review_count})` : 'New arrival'}
          {product.model_asset_url && <span>3D preview</span>}
        </div>
        <Notice error={action.error} />
      </div>
    </article>
  )
}

export function OrderSummary({
  cart,
  children,
}: {
  cart: Pick<
    Cart,
    | 'subtotal_minor'
    | 'discount_minor'
    | 'shipping_minor'
    | 'tax_minor'
    | 'total_minor'
    | 'currency'
  >
  children?: ReactNode
}) {
  return (
    <aside className="shop-summary">
      <h2>Order summary</h2>
      <dl>
        <div>
          <dt>Subtotal</dt>
          <dd>{money(cart.subtotal_minor, cart.currency)}</dd>
        </div>
        {cart.discount_minor > 0 && (
          <div className="shop-discount">
            <dt>Discount</dt>
            <dd>−{money(cart.discount_minor, cart.currency)}</dd>
          </div>
        )}
        <div>
          <dt>Delivery</dt>
          <dd>{cart.shipping_minor ? money(cart.shipping_minor, cart.currency) : 'Free'}</dd>
        </div>
        {cart.tax_minor > 0 && (
          <div>
            <dt>Tax</dt>
            <dd>{money(cart.tax_minor, cart.currency)}</dd>
          </div>
        )}
        <div className="shop-total">
          <dt>Total</dt>
          <dd>{money(cart.total_minor, cart.currency)}</dd>
        </div>
      </dl>
      {children}
      <p className="shop-muted shop-small">Totals are confirmed by Ayna at checkout.</p>
    </aside>
  )
}
