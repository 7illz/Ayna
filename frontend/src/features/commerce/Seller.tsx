import { useRef, useState } from 'react'
import { ArrowRight, BarChart3, Box, Check, ImagePlus, Pencil, Plus, Trash2, X } from 'lucide-react'
import { api, assetUrl } from '../../shared/api'
import { Empty, Loading, Notice, date, money, useAction, useResource, useShop } from './shared'
import type { Order, ShopProduct } from './shared'

export function ProductEditor({
  product,
  onClose,
  onSaved,
}: {
  product: ShopProduct | null
  onClose: () => void
  onSaved: () => void
}) {
  const { config, notify } = useShop()
  const [current, setCurrent] = useState(product)
  const [files, setFiles] = useState<File[]>([])
  const [tab, setTab] = useState<'details' | 'options'>('details')
  const uploaded = useRef(false)
  const action = useAction()
  const [editingVariant, setEditingVariant] = useState<string | null>(null)
  const variant = current?.variants.find((v) => v.id === editingVariant)
  async function save(form: HTMLFormElement) {
    const f = new FormData(form)
    const body = {
      name: f.get('name'),
      category: f.get('category'),
      description: f.get('description'),
      brand: f.get('brand'),
      sku: f.get('sku'),
      price_minor: Math.round(Number(f.get('price')) * 100),
      compare_at_minor: f.get('compare') ? Math.round(Number(f.get('compare')) * 100) : null,
      stock: Number(f.get('stock')),
      is_listed: f.get('listed') === 'on',
    }
    await action.run(async () => {
      let listing = await api<ShopProduct>(
        current ? `/seller/products/${current.id}` : '/seller/products',
        {
          method: current ? 'PUT' : 'POST',
          body: JSON.stringify({ ...body, is_listed: current ? body.is_listed : false }),
        },
      )
      setCurrent(listing)
      if (files.length && !uploaded.current) {
        const images = new FormData()
        files.forEach((file) => images.append('files', file))
        listing = await api<ShopProduct>(`/seller/products/${listing.id}/images`, {
          method: 'POST',
          body: images,
        })
        uploaded.current = true
        setCurrent(listing)
      }
      if (body.is_listed !== listing.is_listed)
        await api(`/seller/products/${listing.id}`, { method: 'PUT', body: JSON.stringify(body) })
      notify('Product saved')
      onSaved()
      onClose()
    })
  }
  return (
    <div
      className="shop-modal-backdrop"
      onKeyDown={(e) => {
        if (e.key === 'Escape' && !action.busy) onClose()
      }}
    >
      <section
        className="shop-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="listing-title"
      >
        <div className="shop-section-title">
          <h2 id="listing-title">{product ? 'Edit your product' : 'Add a good find'}</h2>
          <button
            className="shop-icon-button"
            aria-label="Close product editor"
            onClick={onClose}
            disabled={action.busy}
          >
            <X size={20} />
          </button>
        </div>
        <div className="shop-tabs">
          <button className={tab === 'details' ? 'active' : ''} onClick={() => setTab('details')}>
            Details & photos
          </button>
          <button
            disabled={!current}
            className={tab === 'options' ? 'active' : ''}
            onClick={() => setTab('options')}
          >
            Sizes & options
          </button>
        </div>
        <Notice error={action.error} />
        {tab === 'details' ? (
          <form
            className="shop-form"
            onSubmit={(e) => {
              e.preventDefault()
              void save(e.currentTarget)
            }}
          >
            <label>
              Product name
              <input
                autoFocus
                name="name"
                defaultValue={current?.name || ''}
                required
                minLength={2}
                maxLength={160}
              />
            </label>
            <div className="shop-form-row">
              <label>
                Category
                <select name="category" defaultValue={current?.category || 'bags'}>
                  {config?.categories.map((c) => (
                    <option value={c.slug} key={c.slug}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Brand
                <input name="brand" defaultValue={current?.brand || ''} maxLength={100} />
              </label>
            </div>
            <label>
              Description
              <textarea
                name="description"
                defaultValue={current?.description || ''}
                maxLength={3000}
                rows={3}
              />
            </label>
            <div className="shop-form-row">
              <label>
                Price ({config?.currency || 'BDT'})
                <input
                  name="price"
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  defaultValue={current ? current.price_minor / 100 : ''}
                />
              </label>
              <label>
                Original price (optional)
                <input
                  name="compare"
                  type="number"
                  min="0.01"
                  step="0.01"
                  defaultValue={current?.compare_at_minor ? current.compare_at_minor / 100 : ''}
                />
              </label>
            </div>
            <div className="shop-form-row">
              <label>
                SKU
                <input name="sku" required maxLength={80} defaultValue={current?.sku || ''} />
              </label>
              <label>
                Stock quantity
                <input
                  name="stock"
                  required
                  type="number"
                  min="0"
                  max="1000000"
                  defaultValue={current?.stock || 0}
                />
              </label>
            </div>
            <p className="shop-small shop-muted">
              For products with sizes or options, each option has its own price and stock.
            </p>
            {!!current?.images.length && (
              <div className="shop-editor-photos">
                {current.images.map((i) => (
                  <div key={i.id}>
                    <img src={assetUrl(i.url)} alt="Product photo" />
                    <button
                      type="button"
                      aria-label="Remove product photo"
                      onClick={() =>
                        action.run(async () => {
                          setCurrent(
                            await api<ShopProduct>(
                              `/seller/products/${current.id}/images/${i.id}`,
                              { method: 'DELETE' },
                            ),
                          )
                          onSaved()
                        })
                      }
                    >
                      <X size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <label className="shop-photo-input">
              <ImagePlus size={22} />
              Product photos <span>JPEG, PNG or WebP · up to 5 photos total</span>
              <input
                aria-label="Listing photographs"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={(e) => {
                  setFiles(Array.from(e.target.files || []))
                  uploaded.current = false
                }}
              />
            </label>
            <label className="shop-checkbox">
              <input type="checkbox" name="listed" defaultChecked={current?.is_listed || false} />
              List this product in the shop
            </label>
            <p className="shop-small shop-muted">
              A price and at least one photo are required. A 3D model is optional.
            </p>
            <button className="shop-button full" disabled={action.busy}>
              {action.busy ? 'Saving…' : 'Save product'}
              <Check size={16} />
            </button>
          </form>
        ) : (
          current && (
            <>
              <p className="shop-muted shop-small">
                Create or edit size/color options. Deactivate an option to remove it from sale while
                keeping order history.
              </p>
              <div className="shop-variant-list">
                {current.variants.map((v) => (
                  <button
                    className={editingVariant === v.id ? 'active' : ''}
                    key={v.id}
                    onClick={() => setEditingVariant(v.id)}
                  >
                    {v.label}
                    <span>
                      {v.stock} in stock · {money(v.price_minor, config?.currency)}
                    </span>
                    <Pencil size={14} />
                  </button>
                ))}
              </div>
              <button className="shop-text-button" onClick={() => setEditingVariant(null)}>
                + New option
              </button>
              <form
                key={editingVariant || 'new'}
                className="shop-form"
                onSubmit={(e) => {
                  e.preventDefault()
                  const f = new FormData(e.currentTarget)
                  void action.run(async () => {
                    await api(`/seller/products/${current.id}/variants`, {
                      method: 'POST',
                      body: JSON.stringify({
                        id: editingVariant,
                        label: f.get('label'),
                        sku: f.get('sku'),
                        size: f.get('size'),
                        color: f.get('color'),
                        price_minor: Math.round(Number(f.get('price')) * 100),
                        stock: Number(f.get('stock')),
                        is_active: f.get('active') === 'on',
                      }),
                    })
                    const listings = await api<ShopProduct[]>('/seller/products')
                    setCurrent(listings.find((p) => p.id === current.id) || current)
                    setEditingVariant(null)
                    onSaved()
                    notify('Product option saved')
                  })
                }}
              >
                <label>
                  Option label
                  <input
                    name="label"
                    required
                    maxLength={100}
                    placeholder="Medium · olive"
                    defaultValue={variant?.label || ''}
                  />
                </label>
                <label>
                  Option SKU
                  <input name="sku" required maxLength={80} defaultValue={variant?.sku || ''} />
                </label>
                <div className="shop-form-row">
                  <label>
                    Size
                    <input name="size" maxLength={30} defaultValue={variant?.size || ''} />
                  </label>
                  <label>
                    Color
                    <input name="color" maxLength={40} defaultValue={variant?.color || ''} />
                  </label>
                </div>
                <div className="shop-form-row">
                  <label>
                    Price
                    <input
                      name="price"
                      type="number"
                      step="0.01"
                      min="0.01"
                      required
                      defaultValue={variant ? variant.price_minor / 100 : current.price_minor / 100}
                    />
                  </label>
                  <label>
                    Stock
                    <input
                      name="stock"
                      type="number"
                      min="0"
                      required
                      defaultValue={variant?.stock || 0}
                    />
                  </label>
                </div>
                <label className="shop-checkbox">
                  <input
                    type="checkbox"
                    name="active"
                    defaultChecked={variant?.is_active ?? true}
                  />
                  Available for purchase
                </label>
                <button className="shop-button" disabled={action.busy}>
                  Save option
                </button>
              </form>
            </>
          )
        )}
      </section>
    </div>
  )
}

export function FulfillmentList({
  orders,
  onUpdated,
  admin = false,
}: {
  orders: Order[]
  onUpdated: () => void
  admin?: boolean
}) {
  const action = useAction(),
    { notify } = useShop()
  const [tracking, setTracking] = useState<Record<string, string>>({})
  const [couriers, setCouriers] = useState<Record<string, string>>({})
  return (
    <>
      <Notice error={action.error} />
      {orders.length ? (
        orders.map((order) => (
          <article className="shop-panel shop-fulfillment-card" key={order.id}>
            <div className="shop-section-title">
              <div>
                <a href={admin ? `#/orders/${order.id}` : undefined}>
                  <strong>{order.number}</strong>
                </a>
                <p className="shop-small shop-muted">
                  {date(order.created_at)} · {order.payment_method} · {order.payment_status}
                </p>
              </div>
              <span className="shop-status">{order.status.replaceAll('_', ' ')}</span>
              <strong>{money(order.total_minor, order.currency)}</strong>
            </div>
            <p className="shop-small">
              {Object.values(order.shipping_address).filter(Boolean).join(' · ')}
            </p>
            {order.items.map((item) => {
              const next = { pending: 'processing', processing: 'shipped', shipped: 'delivered' }[
                item.fulfillment_status
              ]
              return (
                <div className="shop-fulfillment-line" key={item.id}>
                  <div>
                    <strong>
                      {item.name}
                      {item.variant_label ? ` · ${item.variant_label}` : ''}
                    </strong>
                    <p className="shop-small shop-muted">
                      {item.quantity} × {money(item.unit_price_minor, order.currency)} · {item.sku}
                    </p>
                    <span className="shop-status">{item.fulfillment_status}</span>
                    {item.tracking_number && (
                      <p className="shop-small">Tracking: {item.tracking_number}</p>
                    )}
                  </div>
                  {next &&
                    !['cancelled', 'returned', 'return_requested'].includes(order.status) && (
                      <form
                        className="shop-form"
                        onSubmit={(e) => {
                          e.preventDefault()
                          void action.run(async () => {
                            await api(`/seller/order-items/${item.id}/fulfill`, {
                              method: 'POST',
                              body: JSON.stringify({
                                status: next,
                                tracking_number: tracking[item.id] || '',
                                courier: couriers[item.id] || 'Seller delivery',
                              }),
                            })
                            onUpdated()
                            notify('Order fulfillment updated')
                          })
                        }}
                      >
                        {next === 'shipped' && (
                          <input
                            aria-label={`Courier for ${item.name}`}
                            placeholder="Courier name"
                            maxLength={80}
                            value={couriers[item.id] || ''}
                            onChange={(e) =>
                              setCouriers({ ...couriers, [item.id]: e.target.value })
                            }
                          />
                        )}
                        {next === 'shipped' && (
                          <input
                            aria-label={`Tracking number for ${item.name}`}
                            placeholder="Tracking number"
                            required
                            maxLength={100}
                            value={tracking[item.id] || ''}
                            onChange={(e) =>
                              setTracking({ ...tracking, [item.id]: e.target.value })
                            }
                          />
                        )}
                        <button className="shop-button outline" disabled={action.busy}>
                          Mark {next}
                          <ArrowRight size={14} />
                        </button>
                      </form>
                    )}
                </div>
              )
            })}
            {admin && (
              <div className="shop-admin-order-actions">
                {[
                  ...(order.status === 'delivered' &&
                  order.payment_method === 'cod' &&
                  order.payment_status === 'pending'
                    ? [['mark_cod_paid', 'Record COD payment']]
                    : []),
                  ...(['placed', 'processing'].includes(order.status)
                    ? [['cancel', 'Cancel order']]
                    : []),
                  ...(order.status === 'return_requested'
                    ? [
                        ['approve_return', 'Accept return & restock'],
                        ['reject_return', 'Decline return'],
                      ]
                    : []),
                  ...(['cancelled', 'returned'].includes(order.status) &&
                  order.payment_status === 'paid'
                    ? [
                        [
                          'refund',
                          order.payment_method === 'stripe'
                            ? 'Refund hosted payment'
                            : 'Record refund',
                        ],
                      ]
                    : []),
                ].map(([command, title]) => (
                  <button
                    key={command}
                    className="shop-button outline"
                    disabled={action.busy}
                    onClick={() => {
                      if (!window.confirm(`${title}?`)) return
                      void action.run(async () => {
                        await api(`/admin/orders/${order.id}`, {
                          method: 'POST',
                          body: JSON.stringify({ action: command }),
                        })
                        onUpdated()
                        notify('Order updated')
                      })
                    }}
                  >
                    {title}
                  </button>
                ))}
              </div>
            )}
          </article>
        ))
      ) : (
        <Empty
          title="Ready for your first order."
          description="Orders and fulfillment details will appear here."
        />
      )}
    </>
  )
}

export function SellerPage() {
  const [tab, setTab] = useState('products')
  const listings = useResource<ShopProduct[]>('/seller/products')
  const orders = useResource<Order[]>('/seller/orders')
  const [editor, setEditor] = useState<ShopProduct | null | undefined>(undefined)
  const action = useAction(),
    { config, notify } = useShop()
  return (
    <section className="shop-section">
      <div className="shop-section-title">
        <div>
          <p className="shop-kicker">YOUR PRODUCTS. YOUR POSSIBILITIES.</p>
          <h1>Seller workspace</h1>
          <p className="shop-muted">Manage the good things you bring to Ayna.</p>
        </div>
        <button className="shop-button" onClick={() => setEditor(null)}>
          <Plus size={16} />
          Add product
        </button>
      </div>
      <div className="shop-tabs">
        <button className={tab === 'products' ? 'active' : ''} onClick={() => setTab('products')}>
          <Box size={16} />
          Products
        </button>
        <button className={tab === 'orders' ? 'active' : ''} onClick={() => setTab('orders')}>
          Orders & shipping
        </button>
        <button className={tab === 'insights' ? 'active' : ''} onClick={() => setTab('insights')}>
          <BarChart3 size={16} />
          Insights
        </button>
        <a href="#/studio">
          3D product studio
          <ArrowRight size={15} />
        </a>
      </div>
      <Notice error={listings.error || orders.error || action.error} />
      {tab === 'products' ? (
        listings.loading ? (
          <Loading />
        ) : listings.data?.length ? (
          <div className="shop-table-wrap">
            <table className="shop-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Status</th>
                  <th>Manage</th>
                </tr>
              </thead>
              <tbody>
                {listings.data.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div className="shop-table-product">
                        {p.images[0] && <img src={assetUrl(p.images[0].url)} alt="" />}
                        <div>
                          <strong>{p.name}</strong>
                          <small>
                            {p.sku} · {p.category}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>{money(p.price_minor, config?.currency)}</td>
                    <td>
                      {p.stock}
                      {p.variants.length ? ` · ${p.variants.length} options` : ''}
                    </td>
                    <td>
                      <span className={`shop-status ${p.is_listed ? 'delivered' : ''}`}>
                        {p.is_listed ? 'Live' : 'Draft'}
                      </span>
                    </td>
                    <td>
                      <div className="shop-row-actions">
                        <button
                          className="shop-icon-button"
                          aria-label={`Edit ${p.name}`}
                          onClick={() => setEditor(p)}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="shop-icon-button"
                          aria-label={`Archive ${p.name}`}
                          disabled={action.busy}
                          onClick={() => {
                            if (
                              !window.confirm(`Archive ${p.name}? Historical orders will be kept.`)
                            )
                              return
                            void action.run(async () => {
                              await api(`/seller/products/${p.id}`, { method: 'DELETE' })
                              await listings.reload()
                              notify('Product archived')
                            })
                          }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="Make your first good impression."
            description="Add a product, its price, stock, and photographs to get started."
            action="Explore the shop"
          />
        )
      ) : tab === 'orders' ? (
        orders.loading ? (
          <Loading />
        ) : (
          <FulfillmentList
            orders={orders.data || []}
            onUpdated={() => {
              void orders.reload()
            }}
          />
        )
      ) : (
        <>
          <div className="shop-dashboard-stats">
            <div>
              <span>Products</span>
              <strong>{listings.data?.length || 0}</strong>
            </div>
            <div>
              <span>Live listings</span>
              <strong>{listings.data?.filter((p) => p.is_listed).length || 0}</strong>
            </div>
            <div>
              <span>Recent orders</span>
              <strong>{orders.data?.length || 0}</strong>
            </div>
            <div>
              <span>Paid order value</span>
              <strong>
                {money(
                  orders.data
                    ?.filter(
                      (o) =>
                        o.payment_status === 'paid' &&
                        !['returned', 'cancelled'].includes(o.status),
                    )
                    .reduce((n, o) => n + o.total_minor, 0) || 0,
                  config?.currency,
                )}
              </strong>
            </div>
          </div>
          <p className="shop-small shop-muted">
            Order insights cover your most recent 100 orders. Totals include only your own items.
          </p>
        </>
      )}
      {editor !== undefined && (
        <ProductEditor
          product={editor}
          onClose={() => setEditor(undefined)}
          onSaved={() => {
            void listings.reload()
          }}
        />
      )}
    </section>
  )
}
