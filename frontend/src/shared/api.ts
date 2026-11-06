import type { components } from './api-schema'

export type Product = components['schemas']['ProductOut']
export type Job = components['schemas']['JobOut']
export type Quality = components['schemas']['QualityOut']
export type PublicProduct = components['schemas']['PublicProduct']
export type Config = components['schemas']['AppConfig']
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(
  /\/$/,
  '',
)
export const DEMO_SELLER = '11111111-1111-4111-8111-111111111111'
export const assetUrl = (path: string) => `${API_BASE}${path}`

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!path.startsWith('/store/')) headers.set('X-Dev-Seller-Id', DEMO_SELLER)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_BASE}/api/v1${path}`, { ...init, headers })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(`${error.detail}${error.request_id ? ` (request ${error.request_id})` : ''}`)
  }
  return response.json()
}
