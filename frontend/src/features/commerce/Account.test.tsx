import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { AuthPage } from './Account'

const state = vi.hoisted(() => ({
  api: vi.fn(),
  setUser: vi.fn(),
  reloadCart: vi.fn(),
  go: vi.fn(),
}))
vi.mock('../../shared/api', () => ({ api: state.api, assetUrl: (url: string) => url }))
vi.mock('./shared', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./shared')>()),
  useShop: () => ({
    setUser: state.setUser,
    reloadCart: state.reloadCart,
    config: { demo_mode: false },
  }),
  go: state.go,
}))

test('finishes cart refresh before exposing signed-in navigation and redirecting', async () => {
  let finishCart!: () => void
  state.reloadCart.mockReturnValue(
    new Promise<void>((resolve) => {
      finishCart = resolve
    }),
  )
  const user = { id: 'seller', name: 'Seller', role: 'seller' }
  state.api.mockResolvedValue(user)
  render(<AuthPage next="/seller" />)
  fireEvent.change(screen.getByLabelText('Email address'), {
    target: { value: 'seller@example.com' },
  })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'AynaPassword2026!' } })
  fireEvent.click(screen.getByRole('button', { name: /^Sign in$/ }))
  await waitFor(() => expect(state.reloadCart).toHaveBeenCalledOnce())
  expect(state.setUser).not.toHaveBeenCalled()
  expect(state.go).not.toHaveBeenCalled()
  await act(async () => {
    finishCart()
  })
  expect(state.setUser).toHaveBeenCalledWith(user)
  expect(state.go).toHaveBeenCalledOnce()
  expect(state.go).toHaveBeenCalledWith('/seller')
})
