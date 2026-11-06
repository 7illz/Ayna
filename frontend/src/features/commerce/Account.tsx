import { useState } from 'react'
import {
  ArrowRight,
  Bell,
  ChevronRight,
  MapPin,
  Package,
  ShieldCheck,
  UserRound,
} from 'lucide-react'
import { api } from '../../shared/api'
import { AddressFields } from './Checkout'
import { Empty, Loading, Notice, date, go, useAction, useResource, useShop } from './shared'
import type { Address, AddressInput, Notification, Ticket, User } from './shared'

export function AuthPage({
  register = false,
  next = '/account',
}: {
  register?: boolean
  next?: string
}) {
  const { setUser, reloadCart, config } = useShop()
  const [email, setEmail] = useState(''),
    [password, setPassword] = useState('')
  const action = useAction()
  return (
    <section className="shop-auth">
      <div className="shop-auth-story">
        <p className="shop-kicker">WELCOME TO YOUR EVERYDAY</p>
        <h1>
          Good things
          <br />
          start here<span>.</span>
        </h1>
        <p>A place for your favorites, your next discoveries, and everything you make your own.</p>
        <div className="shop-auth-mark">a</div>
      </div>
      <div className="shop-auth-form">
        <p className="shop-kicker">
          {register ? 'MAKE YOURSELF AT HOME' : 'GOOD TO SEE YOU AGAIN'}
        </p>
        <h2>{register ? 'Create your account' : 'Welcome back'}</h2>
        <p className="shop-muted">
          {register
            ? 'One account. A world of good finds.'
            : 'Sign in for a more personal perspective.'}
        </p>
        <form
          className="shop-form"
          onSubmit={(e) => {
            e.preventDefault()
            const f = new FormData(e.currentTarget)
            void action.run(async () => {
              const user = await api<User>(register ? '/auth/register' : '/auth/login', {
                method: 'POST',
                body: JSON.stringify(
                  register
                    ? { email, password, name: f.get('name'), role: f.get('role') || 'customer' }
                    : { email, password },
                ),
              })
              await reloadCart()
              setUser(user)
              go(next.startsWith('/') ? next : '/account')
            })
          }}
        >
          {register && (
            <label>
              Your name
              <input name="name" required minLength={2} maxLength={120} autoComplete="name" />
            </label>
          )}
          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              maxLength={254}
              autoComplete="email"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={register ? 10 : 1}
              maxLength={128}
              autoComplete={register ? 'new-password' : 'current-password'}
            />
          </label>
          {register ? (
            <>
              <p className="shop-small shop-muted">Use at least 10 characters.</p>
              <label>
                Account type
                <select name="role">
                  <option value="customer">I’m here to shop</option>
                  <option value="seller">I want to sell on Ayna</option>
                </select>
              </label>
            </>
          ) : (
            <a className="shop-forgot" href="#/forgot-password">
              Forgot your password?
            </a>
          )}
          <Notice error={action.error} />
          <button className="shop-button full" disabled={action.busy}>
            {action.busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}
            <ArrowRight size={16} />
          </button>
        </form>
        <p className="shop-small">
          {register ? 'Already at home here?' : 'New to Ayna?'}{' '}
          <a
            className="shop-text-link"
            href={`#/${register ? 'login' : 'register'}?next=${encodeURIComponent(next)}`}
          >
            {register ? 'Sign in' : 'Create an account'}
          </a>
        </p>
        {config?.demo_mode && (
          <div className="shop-demo-accounts">
            <strong>Explore the local demo</strong>
            <p>Choose an account to fill the sign-in form.</p>
            {['shopper', 'seller', 'admin'].map((role) => (
              <button
                key={role}
                onClick={() => {
                  if (register) go('/login')
                  setEmail(`${role}@ayna.local`)
                  setPassword('AynaDemo!2026')
                }}
              >
                {role}
              </button>
            ))}
            <p>Demo accounts are created by the local catalog setup.</p>
          </div>
        )}
      </div>
    </section>
  )
}

export function PasswordRecovery({ token }: { token?: string }) {
  const action = useAction(),
    { notify } = useShop()
  const [result, setResult] = useState<{
    message: string
    development_reset_url?: string | null
  } | null>(null)
  return (
    <section className="shop-narrow shop-section">
      <p className="shop-kicker">LET’S GET YOU BACK IN</p>
      <h1>{token ? 'A fresh start.' : 'Forgot your password?'}</h1>
      <form
        className="shop-form"
        onSubmit={(e) => {
          e.preventDefault()
          const f = new FormData(e.currentTarget)
          void action.run(async () => {
            const response = await api<{ message: string; development_reset_url?: string | null }>(
              token ? '/auth/reset-password' : '/auth/forgot-password',
              {
                method: 'POST',
                body: JSON.stringify(
                  token ? { token, password: f.get('password') } : { email: f.get('email') },
                ),
              },
            )
            setResult(response)
            if (token) {
              notify(response.message)
              go('/login')
            }
          })
        }}
      >
        {token ? (
          <label>
            New password
            <input
              type="password"
              name="password"
              required
              minLength={10}
              maxLength={128}
              autoComplete="new-password"
            />
          </label>
        ) : (
          <label>
            Email address
            <input type="email" name="email" required maxLength={254} autoComplete="email" />
          </label>
        )}
        <Notice error={action.error} />
        <button className="shop-button" disabled={action.busy}>
          {token ? 'Reset password' : 'Request reset link'}
          <ArrowRight size={16} />
        </button>
      </form>
      {result && (
        <div className="shop-info-box">
          <p>{result.message}</p>
          {result.development_reset_url && (
            <p>
              <a className="shop-text-link" href={result.development_reset_url}>
                Open development reset link
              </a>
            </p>
          )}
        </div>
      )}
      <a href="#/login" className="shop-text-link">
        Back to sign in
      </a>
    </section>
  )
}

export function AccountPage() {
  const { user, setUser, notify } = useShop()
  const action = useAction()
  const addresses = useResource<Address[]>('/account/addresses')
  const notices = useResource<Notification[]>('/notifications')
  const [address, setAddress] = useState<AddressInput>({
    label: 'Home',
    recipient: user?.name || '',
    phone: '',
    street: '',
    city: '',
    postal_code: '',
    country: 'BD',
  })
  const [showAddress, setShowAddress] = useState(false)
  const [editingAddress, setEditingAddress] = useState<string | null>(null)
  return (
    <section className="shop-section">
      <p className="shop-kicker">YOUR OWN CORNER OF AYNA</p>
      <h1>Hello, {user?.name.split(' ')[0]}.</h1>
      <p className="shop-muted">Your details, your orders, your next perspective.</p>
      <Notice error={action.error} />
      <div className="shop-account-links">
        {[
          ['/orders', 'Your orders', Package],
          ['/wishlist', 'Saved favorites', ShieldCheck],
          ['/support', 'Get in touch', UserRound],
        ].map(([href, title, Icon]) => {
          const Component = Icon as typeof Package
          return (
            <a key={String(href)} href={`#${href}`}>
              <Component size={25} />
              <span>{String(title)}</span>
              <ChevronRight size={17} />
            </a>
          )
        })}
      </div>
      <div className="shop-account-grid">
        <section className="shop-panel">
          <h2>Personal details</h2>
          <p className="shop-muted shop-small">{user?.email}</p>
          <form
            className="shop-form"
            onSubmit={(e) => {
              e.preventDefault()
              const f = new FormData(e.currentTarget)
              void action.run(async () => {
                setUser(
                  await api<User>('/account', {
                    method: 'PATCH',
                    body: JSON.stringify({ name: f.get('name') }),
                  }),
                )
                notify('Your profile has been updated')
              })
            }}
          >
            <label>
              Your name
              <input name="name" defaultValue={user?.name} required minLength={2} maxLength={120} />
            </label>
            <button className="shop-button" disabled={action.busy}>
              Save details
            </button>
          </form>
        </section>
        <section className="shop-panel">
          <h2>Change password</h2>
          <form
            className="shop-form"
            onSubmit={(e) => {
              e.preventDefault()
              const f = new FormData(e.currentTarget),
                form = e.currentTarget
              void action.run(async () => {
                await api('/account/password', {
                  method: 'POST',
                  body: JSON.stringify({
                    current_password: f.get('current'),
                    new_password: f.get('password'),
                  }),
                })
                form.reset()
                notify('Password updated; other sessions signed out')
              })
            }}
          >
            <label>
              Current password
              <input type="password" name="current" required autoComplete="current-password" />
            </label>
            <label>
              New password
              <input
                type="password"
                name="password"
                minLength={10}
                maxLength={128}
                required
                autoComplete="new-password"
              />
            </label>
            <button className="shop-button outline" disabled={action.busy}>
              Update password
            </button>
          </form>
        </section>
        <section className="shop-panel">
          <div className="shop-section-title">
            <h2>
              <MapPin size={19} />
              Your addresses
            </h2>
            <button
              className="shop-text-button"
              onClick={() => {
                setEditingAddress(null)
                setShowAddress(!showAddress)
                setAddress({
                  label: 'Home',
                  recipient: user?.name || '',
                  phone: '',
                  street: '',
                  city: '',
                  postal_code: '',
                  country: 'BD',
                })
              }}
            >
              {showAddress ? 'Close' : 'Add address'}
            </button>
          </div>
          <Notice error={addresses.error} />
          {addresses.data?.map((a) => (
            <article className="shop-address-card" key={a.id}>
              <strong>
                {a.label} · {a.recipient}
              </strong>
              <p>
                {a.street}, {a.city} {a.postal_code}
              </p>
              <p>{a.phone}</p>
              <button
                className="shop-text-button"
                onClick={() => {
                  setAddress(a)
                  setEditingAddress(a.id)
                  setShowAddress(true)
                }}
              >
                Edit address
              </button>
              {' · '}
              <button
                className="shop-text-button"
                disabled={action.busy}
                onClick={() =>
                  action.run(async () => {
                    await api(`/account/addresses/${a.id}`, { method: 'DELETE' })
                    await addresses.reload()
                  })
                }
              >
                Remove
              </button>
            </article>
          ))}
          {!addresses.data?.length && (
            <p className="shop-small shop-muted">
              Save a delivery address for a smoother checkout.
            </p>
          )}
          {showAddress && (
            <form
              className="shop-form"
              onSubmit={(e) => {
                e.preventDefault()
                void action.run(async () => {
                  await api(
                    editingAddress ? `/account/addresses/${editingAddress}` : '/account/addresses',
                    { method: editingAddress ? 'PUT' : 'POST', body: JSON.stringify(address) },
                  )
                  await addresses.reload()
                  setShowAddress(false)
                  setEditingAddress(null)
                  notify('Address saved')
                })
              }}
            >
              <label>
                Address label
                <input
                  value={address.label || ''}
                  onChange={(e) => setAddress({ ...address, label: e.target.value })}
                  required
                  maxLength={50}
                />
              </label>
              <AddressFields address={address} setAddress={setAddress} />
              <button className="shop-button" disabled={action.busy}>
                Save address
              </button>
            </form>
          )}
        </section>
        <section className="shop-panel">
          <div className="shop-section-title">
            <h2>
              <Bell size={19} />
              Updates for you
            </h2>
            <button
              className="shop-text-button"
              onClick={() =>
                action.run(async () => {
                  await api('/notifications/read', { method: 'POST' })
                  await notices.reload()
                })
              }
            >
              Mark all read
            </button>
          </div>
          {notices.loading ? (
            <Loading />
          ) : notices.data?.length ? (
            notices.data.map((n) => (
              <article key={n.id} className={`shop-notice ${n.is_read ? '' : 'unread'}`}>
                <strong>{n.title}</strong>
                <p>{n.message}</p>
                <small>{date(n.created_at)}</small>
              </article>
            ))
          ) : (
            <p className="shop-muted shop-small">Order and support updates will appear here.</p>
          )}
        </section>
      </div>
    </section>
  )
}

export function SupportPage() {
  const tickets = useResource<Ticket[]>('/support/tickets')
  const action = useAction(),
    { notify } = useShop()
  return (
    <section className="shop-section">
      <p className="shop-kicker">WE’RE HERE FOR YOU</p>
      <h1>A little help?</h1>
      <div className="shop-account-grid">
        <form
          className="shop-panel shop-form"
          onSubmit={(e) => {
            e.preventDefault()
            const f = new FormData(e.currentTarget),
              form = e.currentTarget
            void action.run(async () => {
              await api('/support/tickets', {
                method: 'POST',
                body: JSON.stringify({ subject: f.get('subject'), message: f.get('message') }),
              })
              form.reset()
              await tickets.reload()
              notify('Your support request has been sent')
            })
          }}
        >
          <h2>Send us a message</h2>
          <label>
            Subject
            <input name="subject" required minLength={3} maxLength={160} />
          </label>
          <label>
            How can we help?
            <textarea name="message" required minLength={10} maxLength={3000} rows={6} />
          </label>
          <Notice error={action.error} />
          <button className="shop-button" disabled={action.busy}>
            Send message
            <ArrowRight size={16} />
          </button>
        </form>
        <div>
          <h2>Your conversations</h2>
          <Notice error={tickets.error} />
          {tickets.loading ? (
            <Loading />
          ) : tickets.data?.length ? (
            tickets.data.map((t) => (
              <article className="shop-panel shop-ticket" key={t.id}>
                <div>
                  <h3>{t.subject}</h3>
                  <span className="shop-status">{t.status}</span>
                </div>
                <p>{t.message}</p>
                {t.response && <blockquote>{t.response}</blockquote>}
                <small className="shop-muted">{date(t.created_at)}</small>
              </article>
            ))
          ) : (
            <Empty
              title="Everything in one place."
              description="Your support conversations will appear here."
              action="Browse help"
              href="/pages/help"
            />
          )}
        </div>
      </div>
    </section>
  )
}
