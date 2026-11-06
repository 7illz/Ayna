import { useState } from 'react'
import { ArrowRight, CheckCircle2, Download, Package, Truck } from 'lucide-react'
import { api } from '../../shared/api'
import { Empty, Loading, Notice, date, money, useAction, useResource, useShop } from './shared'
import type { Order } from './shared'

export function OrdersPage() {
  const orders = useResource<Order[]>('/orders')
  return (
    <section className="shop-section">
      <p className="shop-kicker">EVERY GOOD FIND HAS A STORY</p>
      <h1>Your orders</h1>
      <Notice error={orders.error} />
      {orders.loading ? (
        <Loading />
      ) : orders.data?.length ? (
        <div className="shop-order-list">
          {orders.data.map((order) => (
            <a key={order.id} className="shop-panel shop-order-card" href={`#/orders/${order.id}`}>
              <Package size={25} />
              <div>
                <strong>{order.number}</strong>
                <p>
                  {date(order.created_at)} · {order.items.reduce((n, i) => n + i.quantity, 0)} items
                </p>
                <small>{order.items.map((i) => i.name).join(', ')}</small>
              </div>
              <span className={`shop-status ${order.status}`}>
                {order.status.replaceAll('_', ' ')}
              </span>
              <strong>{money(order.total_minor, order.currency)}</strong>
              <ArrowRight size={18} />
            </a>
          ))}
        </div>
      ) : (
        <Empty
          title="Your story starts with a good find."
          description="Once you place an order, you can follow it all the way here."
        />
      )}
    </section>
  )
}

export function OrderDetail({ id, placed }: { id: string; placed: boolean }) {
  const resource = useResource<Order>(`/orders/${id}`)
  const action = useAction(),
    { notify } = useShop()
  const [reason, setReason] = useState('')
  const order = resource.data
  if (resource.loading) return <Loading />
  if (!order)
    return (
      <section className="shop-section">
        <Notice error={resource.error} />
        <Empty
          title="Order not found."
          description="Check your order list or contact support."
          action="Your orders"
          href="/orders"
        />
      </section>
    )
  async function cancel() {
    if (!window.confirm('Cancel this order? Your reserved items will be returned to stock.')) return
    await action.run(async () => {
      resource.setData(await api<Order>(`/orders/${id}/cancel`, { method: 'POST' }))
      notify('Order cancelled')
    })
  }
  return (
    <section className="shop-section">
      <div className="shop-breadcrumb">
        <a href="#/orders">Your orders</a> / {order.number}
      </div>
      {placed && (
        <div className="shop-order-success">
          <CheckCircle2 size={28} />
          <div>
            <h2>Thanks for your order.</h2>
            <p>
              {order.payment_method === 'cod'
                ? 'Your order is placed. Pay when your delivery arrives.'
                : order.payment_method === 'demo'
                  ? 'Your demo order is placed. No money was charged.'
                  : 'Complete your payment to confirm your order.'}
            </p>
          </div>
        </div>
      )}
      <div className="shop-section-title">
        <div>
          <p className="shop-kicker">ORDER {order.number}</p>
          <h1>Your next good find.</h1>
          <p className="shop-muted">Placed {date(order.created_at)}</p>
        </div>
        <div className="shop-order-actions">
          <button className="shop-button outline" onClick={() => window.print()}>
            <Download size={15} />
            Print receipt
          </button>
          <button className="shop-button outline" onClick={resource.reload}>
            Refresh status
          </button>
        </div>
      </div>
      <Notice error={action.error} />
      <div className="shop-order-detail-layout">
        <div>
          <div className="shop-panel">
            <div className="shop-section-title">
              <h2>
                <Truck size={20} />
                Order progress
              </h2>
              <span className={`shop-status ${order.status}`}>
                {order.status.replaceAll('_', ' ')}
              </span>
            </div>
            <div className="shop-order-timeline">
              {order.events.map((event, index) => (
                <div key={`${event.created_at}-${index}`}>
                  <span />
                  <div>
                    <strong>{event.status.replaceAll('_', ' ')}</strong>
                    <p>{event.message}</p>
                    <small>{date(event.created_at)}</small>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="shop-panel">
            <h2>Your items</h2>
            {order.items.map((item) => (
              <article className="shop-order-line" key={item.id}>
                <div>
                  <a href={`#/products/${item.product_id}`}>
                    <strong>{item.name}</strong>
                  </a>
                  <p>
                    {item.variant_label ? `${item.variant_label} · ` : ''}
                    {item.quantity} × {money(item.unit_price_minor, order.currency)}
                  </p>
                  <span className="shop-status">{item.fulfillment_status}</span>
                  {item.tracking_number && (
                    <p className="shop-tracking">
                      {item.courier} · Tracking: <strong>{item.tracking_number}</strong>
                    </p>
                  )}
                </div>
                <strong>{money(item.unit_price_minor * item.quantity, order.currency)}</strong>
              </article>
            ))}
          </div>
          {order.status === 'placed' && (
            <button className="shop-text-button danger" disabled={action.busy} onClick={cancel}>
              Cancel this order
            </button>
          )}
          {order.payment_method === 'stripe' &&
            order.payment_status === 'pending' &&
            order.status === 'placed' && (
              <button
                className="shop-button"
                disabled={action.busy}
                onClick={() =>
                  action.run(async () => {
                    const result = await api<{ url: string }>(`/orders/${id}/payment-session`, {
                      method: 'POST',
                    })
                    window.location.assign(result.url)
                  })
                }
              >
                Complete payment
                <ArrowRight size={16} />
              </button>
            )}
          {order.status === 'delivered' && (
            <form
              className="shop-panel shop-form"
              onSubmit={(e) => {
                e.preventDefault()
                void action.run(async () => {
                  resource.setData(
                    await api<Order>(`/orders/${id}/return`, {
                      method: 'POST',
                      body: JSON.stringify({ reason }),
                    }),
                  )
                  notify('Your return request has been sent')
                })
              }}
            >
              <h2>Need to return something?</h2>
              <label>
                Tell us why
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  required
                  minLength={5}
                  maxLength={1000}
                  rows={3}
                />
              </label>
              <button className="shop-button outline" disabled={action.busy}>
                Request return
              </button>
            </form>
          )}
        </div>
        <aside>
          <section className="shop-panel">
            <h2>Order details</h2>
            <dl className="shop-order-totals">
              <div>
                <dt>Subtotal</dt>
                <dd>{money(order.subtotal_minor, order.currency)}</dd>
              </div>
              <div>
                <dt>Discount{order.coupon_code ? ` · ${order.coupon_code}` : ''}</dt>
                <dd>−{money(order.discount_minor, order.currency)}</dd>
              </div>
              <div>
                <dt>Delivery</dt>
                <dd>{money(order.shipping_minor, order.currency)}</dd>
              </div>
              {order.tax_minor > 0 && (
                <div>
                  <dt>Tax</dt>
                  <dd>{money(order.tax_minor, order.currency)}</dd>
                </div>
              )}
              <div>
                <dt>Total</dt>
                <dd>
                  <strong>{money(order.total_minor, order.currency)}</strong>
                </dd>
              </div>
            </dl>
            <p className="shop-small shop-muted">
              {order.payment_method === 'cod'
                ? 'Cash on delivery'
                : order.payment_method === 'demo'
                  ? 'Demo payment'
                  : 'Hosted payment'}{' '}
              · {order.payment_status}
            </p>
          </section>
          <section className="shop-panel">
            <h2>Delivering to</h2>
            <address>
              {['recipient', 'street', 'city', 'postal_code', 'country', 'phone'].map((key) => (
                <span key={key}>{String(order.shipping_address[key] || '')}</span>
              ))}
            </address>
            {order.notes && <p className="shop-small shop-muted">Notes: {order.notes}</p>}
          </section>
          <a className="shop-text-link" href="#/support">
            Need help with this order?
            <ArrowRight size={15} />
          </a>
        </aside>
      </div>
    </section>
  )
}
