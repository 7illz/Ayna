import { useState } from 'react'
import { ArrowRight, Check, Settings2 } from 'lucide-react'
import { api } from '../../shared/api'
import { FulfillmentList, ProductEditor } from './Seller'
import { Loading, Notice, money, useAction, useResource, useShop } from './shared'
import type { Category, Coupon, Order, ShopProduct, Ticket, User } from './shared'

type Overview = {
  orders: number
  users: number
  products: number
  low_stock: number
  open_tickets: number
  paid_revenue_minor: number
  currency: string
  order_statuses: Record<string, number>
}
type AdminReview = {
  id: string
  title: string
  body: string
  rating: number
  is_visible: boolean
  product_id: string
}

export function AdminPage() {
  const [tab, setTab] = useState('overview')
  const tabs = [
    'overview',
    'orders',
    'products',
    'users',
    'coupons',
    'categories',
    'support',
    'reviews',
    'settings',
  ]
  return (
    <section className="shop-section">
      <p className="shop-kicker">BEHIND EVERY GOOD EXPERIENCE</p>
      <h1>Store administration</h1>
      <p className="shop-muted">Keep your collection, customers, and operations in sync.</p>
      <div className="shop-tabs admin-tabs">
        {tabs.map((t) => (
          <button className={tab === t ? 'active' : ''} key={t} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>
      {tab === 'overview' ? (
        <OverviewPanel />
      ) : tab === 'orders' ? (
        <OrdersPanel />
      ) : tab === 'products' ? (
        <ProductsPanel />
      ) : tab === 'users' ? (
        <UsersPanel />
      ) : tab === 'coupons' ? (
        <CouponsPanel />
      ) : tab === 'categories' ? (
        <CategoriesPanel />
      ) : tab === 'support' ? (
        <SupportPanel />
      ) : tab === 'reviews' ? (
        <ReviewsPanel />
      ) : (
        <SettingsPanel />
      )}
    </section>
  )
}
function OverviewPanel() {
  const info = useResource<Overview>('/admin/overview')
  if (info.loading) return <Loading />
  return (
    <>
      <Notice error={info.error} />
      {info.data && (
        <>
          <div className="shop-dashboard-stats">
            {[
              ['Paid revenue', money(info.data.paid_revenue_minor, info.data.currency)],
              ['Total orders', info.data.orders],
              ['Customers & team', info.data.users],
              ['Products', info.data.products],
              ['Low base stock', info.data.low_stock],
              ['Open support requests', info.data.open_tickets],
            ].map(([title, value]) => (
              <div key={title}>
                <span>{title}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          <div className="shop-panel shop-analytics">
            <h2>Order overview</h2>
            <p className="shop-small shop-muted">
              All-time order counts. Paid revenue excludes cancelled and returned orders.
            </p>
            {Object.keys(info.data.order_statuses).length ? (
              Object.entries(info.data.order_statuses).map(([status, count]) => (
                <div className="shop-analytics-row" key={status}>
                  <span>{status.replaceAll('_', ' ')}</span>
                  <div>
                    <i
                      style={{
                        width: `${Math.max(2, (count / Math.max(1, info.data!.orders)) * 100)}%`,
                      }}
                    />
                  </div>
                  <strong>{count}</strong>
                </div>
              ))
            ) : (
              <p className="shop-muted">Analytics will appear after your first order.</p>
            )}
          </div>
        </>
      )}
    </>
  )
}
function OrdersPanel() {
  const orders = useResource<Order[]>('/admin/orders')
  return (
    <>
      <Notice error={orders.error} />
      {orders.loading ? (
        <Loading />
      ) : (
        <FulfillmentList
          admin
          orders={orders.data || []}
          onUpdated={() => {
            void orders.reload()
          }}
        />
      )}
    </>
  )
}
function ProductsPanel() {
  const products = useResource<ShopProduct[]>('/admin/products')
  const action = useAction(),
    { notify, config } = useShop()
  const [editing, setEditing] = useState<ShopProduct | undefined>(undefined)
  return (
    <>
      <Notice error={products.error || action.error} />
      {products.loading ? (
        <Loading />
      ) : (
        <div className="shop-table-wrap">
          <table className="shop-table">
            <thead>
              <tr>
                <th>Product / seller</th>
                <th>Price / stock</th>
                <th>Listed</th>
                <th>Featured</th>
                <th>Edit</th>
              </tr>
            </thead>
            <tbody>
              {products.data?.map((p) => (
                <tr key={p.id}>
                  <td>
                    <strong>{p.name}</strong>
                    <small>
                      {p.seller_name} · {p.sku}
                    </small>
                  </td>
                  <td>
                    {money(p.price_minor, config?.currency)}
                    <small>{p.stock} available</small>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`List ${p.name}`}
                      checked={p.is_listed}
                      disabled={action.busy}
                      onChange={(e) =>
                        action.run(async () => {
                          await api(`/admin/products/${p.id}`, {
                            method: 'PATCH',
                            body: JSON.stringify({
                              is_listed: e.target.checked,
                              featured: p.featured,
                            }),
                          })
                          await products.reload()
                          notify('Product visibility updated')
                        })
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Feature ${p.name}`}
                      checked={p.featured}
                      disabled={action.busy}
                      onChange={(e) =>
                        action.run(async () => {
                          await api(`/admin/products/${p.id}`, {
                            method: 'PATCH',
                            body: JSON.stringify({
                              is_listed: p.is_listed,
                              featured: e.target.checked,
                            }),
                          })
                          await products.reload()
                        })
                      }
                    />
                  </td>
                  <td>
                    <button className="shop-button outline" onClick={() => setEditing(p)}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {editing && (
        <ProductEditor
          product={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            void products.reload()
          }}
        />
      )}
    </>
  )
}
function UsersPanel() {
  const users = useResource<User[]>('/admin/users')
  const action = useAction(),
    { notify } = useShop()
  return (
    <>
      <Notice error={users.error || action.error} />
      {users.loading ? (
        <Loading />
      ) : (
        <div className="shop-table-wrap">
          <table className="shop-table">
            <thead>
              <tr>
                <th>Account</th>
                <th>Role</th>
                <th>Active</th>
                <th>Update</th>
              </tr>
            </thead>
            <tbody>
              {users.data?.map((user) => (
                <tr key={user.id}>
                  <td>
                    <strong>{user.name}</strong>
                    <small>{user.email}</small>
                  </td>
                  <td colSpan={3}>
                    <form
                      className="shop-inline-form"
                      onSubmit={(e) => {
                        e.preventDefault()
                        const f = new FormData(e.currentTarget)
                        void action.run(async () => {
                          await api(`/admin/users/${user.id}`, {
                            method: 'PATCH',
                            body: JSON.stringify({
                              role: f.get('role'),
                              is_active: f.get('active') === 'on',
                            }),
                          })
                          await users.reload()
                          notify('Account permissions updated')
                        })
                      }}
                    >
                      <select
                        aria-label={`Role for ${user.email}`}
                        name="role"
                        defaultValue={user.role}
                      >
                        <option value="customer">Customer</option>
                        <option value="seller">Seller</option>
                        <option value="admin">Admin</option>
                      </select>
                      <label className="shop-checkbox">
                        <input
                          aria-label={`Active account ${user.email}`}
                          type="checkbox"
                          name="active"
                          defaultChecked={user.is_active}
                        />
                        Active
                      </label>
                      <button className="shop-button outline" disabled={action.busy}>
                        Save
                      </button>
                    </form>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
function CouponsPanel() {
  const coupons = useResource<Coupon[]>('/admin/coupons')
  const [editing, setEditing] = useState<Coupon | null>(null)
  const action = useAction(),
    { notify, config } = useShop()
  return (
    <div className="shop-account-grid">
      <div className="shop-panel">
        <h2>Promotion codes</h2>
        <Notice error={coupons.error} />
        {coupons.data?.map((c) => (
          <button key={c.code} className="shop-coupon-row" onClick={() => setEditing(c)}>
            <strong>{c.code}</strong>
            <span>
              {c.discount_percent}% + {money(c.discount_minor, config?.currency)}
            </span>
            <small>
              {c.used_count}/{c.max_uses} uses · {c.is_active ? 'active' : 'inactive'}
            </small>
            <ArrowRight size={15} />
          </button>
        ))}
        <button className="shop-text-button" onClick={() => setEditing(null)}>
          + Create a promotion
        </button>
      </div>
      <form
        className="shop-panel shop-form"
        key={editing?.code || 'new'}
        onSubmit={(e) => {
          e.preventDefault()
          const f = new FormData(e.currentTarget)
          void action.run(async () => {
            const code = String(f.get('code')).toUpperCase()
            await api(`/admin/coupons/${code}`, {
              method: 'PUT',
              body: JSON.stringify({
                code,
                discount_percent: Number(f.get('percent')),
                discount_minor: Math.round(Number(f.get('fixed')) * 100),
                minimum_minor: Math.round(Number(f.get('minimum')) * 100),
                max_uses: Number(f.get('uses')),
                is_active: f.get('active') === 'on',
                expires_at: f.get('expires')
                  ? new Date(String(f.get('expires'))).toISOString()
                  : null,
              }),
            })
            await coupons.reload()
            notify('Promotion saved')
          })
        }}
      >
        <h2>{editing ? `Edit ${editing.code}` : 'Create a promotion'}</h2>
        <label>
          Code
          <input
            name="code"
            defaultValue={editing?.code || ''}
            required
            pattern="[a-zA-Z0-9_-]+"
            minLength={2}
            maxLength={32}
          />
        </label>
        <div className="shop-form-row">
          <label>
            Percentage discount
            <input
              name="percent"
              type="number"
              min="0"
              max="100"
              required
              defaultValue={editing?.discount_percent || 0}
            />
          </label>
          <label>
            Fixed discount ({config?.currency})
            <input
              name="fixed"
              type="number"
              min="0"
              step="0.01"
              required
              defaultValue={(editing?.discount_minor || 0) / 100}
            />
          </label>
        </div>
        <div className="shop-form-row">
          <label>
            Minimum order amount
            <input
              name="minimum"
              type="number"
              min="0"
              step="0.01"
              required
              defaultValue={(editing?.minimum_minor || 0) / 100}
            />
          </label>
          <label>
            Maximum uses
            <input
              name="uses"
              type="number"
              min="1"
              required
              defaultValue={editing?.max_uses || 100}
            />
          </label>
        </div>
        <label>
          Expiry (optional)
          <input
            name="expires"
            type="datetime-local"
            defaultValue={editing?.expires_at ? editing.expires_at.slice(0, 16) : ''}
          />
        </label>
        <label className="shop-checkbox">
          <input type="checkbox" name="active" defaultChecked={editing?.is_active ?? true} />
          Active
        </label>
        <Notice error={action.error} />
        <button className="shop-button" disabled={action.busy}>
          Save promotion
          <Check size={16} />
        </button>
      </form>
    </div>
  )
}
function CategoriesPanel() {
  const categories = useResource<Category[]>('/admin/categories')
  const [editing, setEditing] = useState<Category | null>(null)
  const action = useAction(),
    { notify, reloadConfig } = useShop()
  return (
    <div className="shop-account-grid">
      <div className="shop-panel">
        <h2>Browse categories</h2>
        {categories.data?.map((c) => (
          <button className="shop-coupon-row" key={c.slug} onClick={() => setEditing(c)}>
            <strong>{c.name}</strong>
            <small>
              {c.slug} · {c.is_active ? 'active' : 'inactive'}
            </small>
            <ArrowRight size={16} />
          </button>
        ))}
        <button className="shop-text-button" onClick={() => setEditing(null)}>
          + New category
        </button>
      </div>
      <form
        className="shop-panel shop-form"
        key={editing?.slug || 'new'}
        onSubmit={(e) => {
          e.preventDefault()
          const f = new FormData(e.currentTarget)
          void action.run(async () => {
            const slug = String(f.get('slug'))
            await api(`/admin/categories/${slug}`, {
              method: 'PUT',
              body: JSON.stringify({
                slug,
                name: f.get('name'),
                description: f.get('description'),
                is_active: f.get('active') === 'on',
              }),
            })
            await categories.reload()
            await reloadConfig()
            notify('Category saved')
          })
        }}
      >
        <h2>{editing ? 'Edit category' : 'New category'}</h2>
        <label>
          Name
          <input
            name="name"
            defaultValue={editing?.name || ''}
            required
            minLength={2}
            maxLength={80}
          />
        </label>
        <label>
          URL slug
          <input
            name="slug"
            defaultValue={editing?.slug || ''}
            pattern="[a-z0-9-]+"
            required
            minLength={2}
            maxLength={32}
            readOnly={!!editing}
          />
        </label>
        <label>
          Description
          <textarea
            name="description"
            defaultValue={editing?.description || ''}
            maxLength={300}
            rows={3}
          />
        </label>
        <label className="shop-checkbox">
          <input type="checkbox" name="active" defaultChecked={editing?.is_active ?? true} />
          Active
        </label>
        <p className="shop-small shop-muted">
          Deactivating a category hides its existing product listings.
        </p>
        <Notice error={categories.error || action.error} />
        <button className="shop-button" disabled={action.busy}>
          Save category
        </button>
      </form>
    </div>
  )
}
function SupportPanel() {
  const tickets = useResource<Ticket[]>('/support/tickets')
  const action = useAction(),
    { notify } = useShop()
  return (
    <>
      <Notice error={tickets.error || action.error} />
      {tickets.loading ? (
        <Loading />
      ) : tickets.data?.length ? (
        tickets.data.map((t) => (
          <form
            className="shop-panel shop-form shop-admin-ticket"
            key={t.id}
            onSubmit={(e) => {
              e.preventDefault()
              const f = new FormData(e.currentTarget)
              void action.run(async () => {
                await api(`/admin/tickets/${t.id}/reply`, {
                  method: 'POST',
                  body: JSON.stringify({ response: f.get('response'), status: f.get('status') }),
                })
                await tickets.reload()
                notify('Support reply saved')
              })
            }}
          >
            <div className="shop-section-title">
              <h3>{t.subject}</h3>
              <span className="shop-status">{t.status}</span>
            </div>
            <p>{t.message}</p>
            <label>
              Your response
              <textarea
                name="response"
                defaultValue={t.response}
                required
                minLength={2}
                maxLength={3000}
                rows={3}
              />
            </label>
            <div className="shop-inline-form">
              <select name="status" aria-label="Support ticket status" defaultValue="resolved">
                <option value="resolved">Resolve request</option>
                <option value="open">Keep open</option>
              </select>
              <button className="shop-button" disabled={action.busy}>
                Send response
              </button>
            </div>
          </form>
        ))
      ) : (
        <p className="shop-panel shop-muted">No support requests yet.</p>
      )}
    </>
  )
}
function ReviewsPanel() {
  const reviews = useResource<AdminReview[]>('/admin/reviews')
  const action = useAction()
  return (
    <>
      <Notice error={reviews.error || action.error} />
      {reviews.loading ? (
        <Loading />
      ) : reviews.data?.length ? (
        reviews.data.map((r) => (
          <article className="shop-panel shop-review" key={r.id}>
            <div className="shop-section-title">
              <h3>{r.title}</h3>
              <button
                className="shop-button outline"
                disabled={action.busy}
                onClick={() =>
                  action.run(async () => {
                    await api(`/admin/reviews/${r.id}/visibility?visible=${!r.is_visible}`, {
                      method: 'POST',
                    })
                    await reviews.reload()
                  })
                }
              >
                {r.is_visible ? 'Hide review' : 'Show review'}
              </button>
            </div>
            <p className="shop-stars">{'★'.repeat(r.rating)}</p>
            <p>{r.body}</p>
            <a className="shop-text-link" href={`#/products/${r.product_id}`}>
              View product
            </a>
          </article>
        ))
      ) : (
        <p className="shop-panel shop-muted">Customer reviews will appear here.</p>
      )}
    </>
  )
}
function SettingsPanel() {
  const { config, reloadConfig, notify } = useShop()
  const action = useAction()
  if (!config) return <Loading />
  return (
    <form
      className="shop-panel shop-form shop-settings"
      onSubmit={(e) => {
        e.preventDefault()
        const f = new FormData(e.currentTarget)
        void action.run(async () => {
          await api('/admin/settings', {
            method: 'PUT',
            body: JSON.stringify({
              name: f.get('name'),
              tagline: f.get('tagline'),
              shipping_minor: Math.round(Number(f.get('shipping')) * 100),
              free_shipping_minor: Math.round(Number(f.get('free')) * 100),
              tax_basis_points: Math.round(Number(f.get('tax')) * 100),
              support_email: f.get('email'),
              announcement: f.get('announcement'),
            }),
          })
          await reloadConfig()
          notify('Store settings updated')
        })
      }}
    >
      <h2>
        <Settings2 size={20} />
        Store settings
      </h2>
      <label>
        Store name
        <input name="name" required minLength={2} maxLength={80} defaultValue={config.name} />
      </label>
      <label>
        Tagline
        <input name="tagline" maxLength={160} defaultValue={config.tagline} />
      </label>
      <label>
        Announcement
        <input name="announcement" maxLength={200} defaultValue={config.announcement} />
      </label>
      <div className="shop-form-row">
        <label>
          Delivery charge ({config.currency})
          <input
            name="shipping"
            type="number"
            min="0"
            step="0.01"
            defaultValue={config.shipping_minor / 100}
            required
          />
        </label>
        <label>
          Free delivery threshold
          <input
            name="free"
            type="number"
            min="0"
            step="0.01"
            defaultValue={config.free_shipping_minor / 100}
            required
          />
        </label>
      </div>
      <label>
        Configured tax rate (%)
        <input
          name="tax"
          type="number"
          min="0"
          max="100"
          step="0.01"
          required
          defaultValue={config.tax_basis_points / 100}
        />
      </label>
      <p className="shop-small shop-muted">
        Set the tax rate to match your business requirements. Ayna applies this configured rate to
        the discounted subtotal.
      </p>
      <label>
        Support email
        <input name="email" type="email" maxLength={254} defaultValue={config.support_email} />
      </label>
      <Notice error={action.error} />
      <button className="shop-button" disabled={action.busy}>
        Save settings
        <Check size={16} />
      </button>
    </form>
  )
}
