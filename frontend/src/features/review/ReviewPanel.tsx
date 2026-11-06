import { useState } from 'react'
import { Check, X, ShieldCheck } from 'lucide-react'
import { api } from '../../shared/api'
import type { Product, Quality } from '../../shared/api'

export function ReviewPanel({
  product,
  quality,
  onReviewed,
}: {
  product: Product
  quality: Quality | null
  onReviewed: (p: Product) => void
}) {
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const flags = Array.isArray(quality?.metrics.flags)
    ? quality.metrics.flags.filter((item): item is string => typeof item === 'string')
    : []
  async function review(decision: 'approve' | 'reject') {
    if (decision === 'reject' && !notes.trim()) {
      setError('Add a reason before rejecting this preview.')
      return
    }
    setBusy(true)
    setError('')
    try {
      onReviewed(
        await api<Product>(`/products/${product.id}/review`, {
          method: 'POST',
          body: JSON.stringify({ decision, notes }),
        }),
      )
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="review-panel">
      <div className="section-heading">
        <h3>
          <ShieldCheck size={18} /> Seller review
        </h3>
        <span className="tag">REQUIRED</span>
      </div>
      <p className="muted small">
        {quality?.notes ||
          'Photo fidelity is not evaluated in mock mode. No similarity score is available.'}
      </p>
      <div className="quality-summary" aria-label="Quality validation summary">
        <span className={`status ${quality?.status || 'pending'}`}>
          {(quality?.status || 'pending').replaceAll('_', ' ')}
        </span>
        {flags.length > 0 && (
          <ul>
            {flags.map((flag) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
        )}
        {quality?.uncertain_views && quality.uncertain_views.length > 0 && (
          <div>
            <strong>Uncertain or unobserved views</strong>
            <ul>
              {quality.uncertain_views.map((view) => (
                <li key={view}>{view}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <label className="small">
        Review notes
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={2000}
          rows={2}
          placeholder="Record any differences from the original photos…"
        />
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="review-actions">
        <button
          className="button primary"
          onClick={() => review('approve')}
          disabled={busy || quality?.status === 'failed'}
        >
          <Check size={16} /> Approve preview
        </button>
        <button className="button secondary" onClick={() => review('reject')} disabled={busy}>
          <X size={16} /> Reject
        </button>
      </div>
      <p className="small muted">
        Approval publishes this labeled AI-generated preview. Original photos remain authoritative.
      </p>
    </section>
  )
}
