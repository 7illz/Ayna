export function savedProductIds(key: string): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(value)
      ? value
          .filter((id): id is string => typeof id === 'string' && /^[a-f0-9-]{36}$/i.test(id))
          .slice(0, 8)
      : []
  } catch {
    return []
  }
}
export function rememberProduct(id: string) {
  const ids = savedProductIds('ayna_recent').filter((value) => value !== id)
  localStorage.setItem('ayna_recent', JSON.stringify([id, ...ids].slice(0, 8)))
}
export function compareProduct(id: string, notify: (message: string) => void) {
  const ids = savedProductIds('ayna_compare')
  if (ids.includes(id)) {
    notify('This product is already in your comparison')
    return
  }
  if (ids.length >= 4) {
    notify('Compare up to four products. Remove one from the comparison first.')
    return
  }
  localStorage.setItem('ayna_compare', JSON.stringify([...ids, id]))
  notify('Added to comparison. Open Compare products from the shop footer.')
}
