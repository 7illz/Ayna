import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, CheckCircle2, LockKeyhole, Minus, Plus, Trash2 } from 'lucide-react'
import { api, assetUrl } from '../../shared/api'
import {
  Empty,
  Loading,
  Notice,
  OrderSummary,
  go,
  money,
  useAction,
  useResource,
  useShop,
} from './shared'
import type { Address, AddressInput, Cart, Order } from './shared'

export function CartPage() {
  const resource = useResource<Cart>('/cart')
  const [coupon, setCoupon] = useState(localStorage.getItem('ayna_coupon') || '')
  const { setCart } = useShop()
  const action = useAction()
  const cart = resource.data
  const { setData: setQuoteData } = resource
  const { setError: setQuoteError } = action
  const restored = useRef(false)
  useEffect(() => {
    if (!cart || restored.current) return
    restored.current = true
    if (coupon) {
      api<Cart>('/cart/quote', { method: 'POST', body: JSON.stringify({ coupon_code: coupon }) })
        .then((result) => {
          setQuoteData(result)
          setCart(result)
        })
        .catch((err) => {
          setQuoteError(err.message)
          localStorage.removeItem('ayna_coupon')
          setCoupon('')
        })
    }
  }, [cart, coupon, setQuoteData, setCart, setQuoteError])
  async function apply() {
    await action.run(async () => {
      const result = await api<Cart>('/cart/quote', {
        method: 'POST',
        body: JSON.stringify({ coupon_code: coupon }),
      })
      localStorage.setItem('ayna_coupon', coupon)
      resource.setData(result)
      setCart(result)
    })
  }
  async function update(itemId: string, quantity?: number) {
    await action.run(async () => {
      const result = await api<Cart>(
        `/cart/items/${itemId}`,
        quantity ? { method: 'PATCH', body: JSON.stringify({ quantity }) } : { method: 'DELETE' },
      )
      resource.setData(result)
      setCart(result)
      if (coupon) {
        const quote = await api<Cart>('/cart/quote', {
          method: 'POST',
          body: JSON.stringify({ coupon_code: coupon }),
        })
        resource.setData(quote)
        setCart(quote)
      }
    })
  }
  return (
    <section className="shop-section">
      <div className="shop-breadcrumb">
        <a href="#/">Home</a> / Your bag
      </div>
      <p className="shop-kicker">A FEW GOOD CHOICES</p>
      <h1>
        Your shopping bag
        {cart?.items.length ? (
          <span className="shop-count">{cart.items.reduce((sum, i) => sum + i.quantity, 0)}</span>
        ) : null}
      </h1>
      <Notice error={resource.error || action.error} />
      {resource.loading ? (
        <Loading />
      ) : cart?.items.length ? (
        <div className="shop-cart-layout">
          <div className="shop-cart-list">
            {cart.items.map((item) => (
              <article className="shop-cart-item" key={item.id}>
                <a href={`#/products/${item.product.id}`}>
                  {item.product.images[0] && (
                    <img src={assetUrl(item.product.images[0].url)} alt={item.product.name} />
                  )}
                </a>
                <div>
                  <p className="shop-kicker">{item.product.category}</p>
                  <a href={`#/products/${item.product.id}`}>
                    <h3>{item.product.name}</h3>
                  </a>
                  {item.variant_label && (
                    <p className="shop-small shop-muted">Option: {item.variant_label}</p>
                  )}
                  <p className="shop-small">{money(item.unit_price_minor, cart.currency)} each</p>
                  {!item.available && (
                    <p className="shop-error">This quantity or option is unavailable.</p>
                  )}
                  <div className="shop-quantity small">
                    <button
                      aria-label={`Decrease ${item.product.name}`}
                      disabled={action.busy || item.quantity <= 1}
                      onClick={() => update(item.id, item.quantity - 1)}
                    >
                      <Minus size={13} />
                    </button>
                    <span>{item.quantity}</span>
                    <button
                      aria-label={`Increase ${item.product.name}`}
                      disabled={
                        action.busy || item.quantity >= item.available_stock || item.quantity >= 99
                      }
                      onClick={() => update(item.id, item.quantity + 1)}
                    >
                      <Plus size={13} />
                    </button>
                  </div>
                </div>
                <div className="shop-cart-price">
                  <strong>{money(item.line_total_minor, cart.currency)}</strong>
                  <button
                    aria-label={`Remove ${item.product.name}`}
                    className="shop-icon-button"
                    disabled={action.busy}
                    onClick={() => update(item.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </article>
            ))}
            <a className="shop-text-link" href="#/shop">
              <ArrowLeft size={15} />
              Continue exploring
            </a>
          </div>
          <OrderSummary cart={cart}>
            <form
              className="shop-coupon"
              onSubmit={(e) => {
                e.preventDefault()
                void apply()
              }}
            >
              <label htmlFor="coupon">Have a promo code?</label>
              <div>
                <input
                  id="coupon"
                  placeholder="e.g. WELCOME10"
                  value={coupon}
                  onChange={(e) => setCoupon(e.target.value.toUpperCase())}
                  maxLength={32}
                />
                <button className="shop-button outline" disabled={action.busy}>
                  Apply
                </button>
              </div>
            </form>
            <a
              className={`shop-button full ${cart.items.some((i) => !i.available) ? 'disabled' : ''}`}
              href={cart.items.some((i) => !i.available) ? '#/cart' : '#/checkout'}
            >
              Continue to checkout
              <ArrowRight size={16} />
            </a>
            <p className="shop-small shop-muted">
              <LockKeyhole size={12} /> Cash on delivery available
            </p>
          </OrderSummary>
        </div>
      ) : (
        <Empty
          title="Your next favorite is waiting."
          description="Your bag is empty. Let's find something you'll love."
        />
      )}
    </section>
  )
}

const emptyAddress: AddressInput = {
  label: 'Home',
  recipient: '',
  phone: '',
  street: '',
  city: '',
  postal_code: '',
  country: 'BD',
}
export function AddressFields({
  address,
  setAddress,
}: {
  address: AddressInput
  setAddress: (a: AddressInput) => void
}) {
  return (
    <div className="shop-address-fields">
      {[
        ['recipient', 'Full name', 'name'],
        ['phone', 'Phone number', 'tel'],
        ['street', 'Street address', 'street-address'],
        ['city', 'City', 'address-level2'],
        ['postal_code', 'Postal code', 'postal-code'],
      ].map(([key, title, autocomplete]) => (
        <label className={key === 'street' ? 'wide' : ''} key={key}>
          {title}
          <input
            required
            name={key}
            type={key === 'phone' ? 'tel' : 'text'}
            autoComplete={autocomplete}
            value={address[key as keyof AddressInput] || ''}
            maxLength={key === 'street' ? 300 : key === 'phone' ? 30 : 120}
            minLength={key === 'street' ? 5 : key === 'phone' ? 6 : 2}
            onChange={(e) => setAddress({ ...address, [key]: e.target.value })}
          />
        </label>
      ))}
      <label>
        Country
        <select
          value={address.country}
          onChange={(e) => setAddress({ ...address, country: e.target.value })}
        >
          <option value="BD">Bangladesh</option>
        </select>
      </label>
    </div>
  )
}

export function CheckoutPage() {
  const { config, user, reloadCart } = useShop()
  const [address, setAddress] = useState<AddressInput>({
    ...emptyAddress,
    recipient: user?.name || '',
  })
  const [method, setMethod] = useState('cod')
  const [notes, setNotes] = useState('')
  const [save, setSave] = useState(false)
  const [quote, setQuote] = useState<Cart | null>(null)
  const [quoteError, setQuoteError] = useState('')
  const addresses = useResource<Address[]>('/account/addresses')
  const action = useAction()
  const submitting = useRef(false)
  const requestKey = useRef(crypto.randomUUID())
  useEffect(() => {
    api<Cart>('/cart/quote', {
      method: 'POST',
      body: JSON.stringify({ coupon_code: localStorage.getItem('ayna_coupon') || '' }),
    })
      .then(setQuote)
      .catch((e) => setQuoteError(e.message))
  }, [])
  async function submit() {
    if (submitting.current) return
    submitting.current = true
    await action.run(async () => {
      if (save) await api('/account/addresses', { method: 'POST', body: JSON.stringify(address) })
      const order = await api<Order>('/checkout', {
        method: 'POST',
        headers: { 'Idempotency-Key': requestKey.current },
        body: JSON.stringify({
          address,
          payment_method: method,
          notes,
          coupon_code: localStorage.getItem('ayna_coupon') || '',
        }),
      })
      localStorage.removeItem('ayna_coupon')
      await reloadCart()
      if (method === 'stripe') {
        go(`/orders/${order.id}`)
        const result = await api<{ url: string }>(`/orders/${order.id}/payment-session`, {
          method: 'POST',
        })
        window.location.assign(result.url)
      } else go(`/orders/${order.id}?placed=true`)
    })
    submitting.current = false
  }
  if (quoteError)
    return (
      <section className="shop-section">
        <Notice error={quoteError} />
        <a className="shop-button" href="#/cart">
          Return to your bag
        </a>
      </section>
    )
  if (!quote) return <Loading />
  if (!quote.items.length)
    return (
      <Empty
        title="Your bag is empty."
        description="Add something to your bag before checking out."
      />
    )
  return (
    <section className="shop-section">
      <div className="shop-breadcrumb">
        <a href="#/cart">Your bag</a> / Checkout
      </div>
      <p className="shop-kicker">JUST A FEW MORE DETAILS</p>
      <h1>Make it yours.</h1>
      <form
        className="shop-checkout-layout shop-form"
        onSubmit={(e) => {
          e.preventDefault()
          void submit()
        }}
      >
        <div>
          <section className="shop-checkout-block">
            <h2>
              <span>01</span>Where should it go?
            </h2>
            {!!addresses.data?.length && (
              <label>
                Saved address
                <select
                  defaultValue=""
                  onChange={(e) => {
                    const found = addresses.data!.find((a) => a.id === e.target.value)
                    if (found) setAddress(found)
                  }}
                >
                  <option value="">Use a new address</option>
                  {addresses.data.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.label}: {a.street}, {a.city}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <AddressFields address={address} setAddress={setAddress} />
            <label className="shop-checkbox">
              <input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} />
              Save this address for next time
            </label>
          </section>
          <section className="shop-checkout-block">
            <h2>
              <span>02</span>How would you like to pay?
            </h2>
            {(config?.payment_methods || ['cod']).map((p) => (
              <label className={`shop-payment-option ${method === p ? 'active' : ''}`} key={p}>
                <input
                  type="radio"
                  name="payment"
                  value={p}
                  checked={method === p}
                  onChange={() => setMethod(p)}
                />
                <div>
                  <strong>
                    {p === 'cod'
                      ? 'Cash on delivery'
                      : p === 'demo'
                        ? 'Demo payment · no money charged'
                        : 'Card via secure hosted checkout'}
                  </strong>
                  <p>
                    {p === 'cod'
                      ? 'Pay when your order arrives.'
                      : p === 'demo'
                        ? 'Test the prepaid order flow without entering card details.'
                        : 'Continue to the payment provider after placing your order.'}
                  </p>
                </div>
              </label>
            ))}
          </section>
          <section className="shop-checkout-block">
            <h2>
              <span>03</span>Anything we should know?
            </h2>
            <label>
              Delivery notes <span className="shop-muted">(optional)</span>
              <textarea
                value={notes}
                maxLength={1000}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="A helpful landmark or delivery instructions…"
              />
            </label>
          </section>
        </div>
        <OrderSummary cart={quote}>
          <div className="shop-checkout-mini-items">
            {quote.items.map((i) => (
              <div key={i.id}>
                <span>
                  {i.quantity} × {i.product.name}
                  {i.variant_label ? ` · ${i.variant_label}` : ''}
                </span>
                <strong>{money(i.line_total_minor, quote.currency)}</strong>
              </div>
            ))}
          </div>
          <Notice error={action.error} />
          {quote.items.some((i) => !i.available) && (
            <Notice error="An item is unavailable. Update your bag before placing the order." />
          )}
          <button
            className="shop-button full"
            disabled={action.busy || quote.items.some((i) => !i.available)}
          >
            {action.busy
              ? 'Placing your order…'
              : method === 'stripe'
                ? 'Continue to payment'
                : 'Place order'}
            <ArrowRight size={16} />
          </button>
          <p className="shop-small shop-muted">
            <CheckCircle2 size={13} /> Check your details before placing your order.
          </p>
        </OrderSummary>
      </form>
    </section>
  )
}
