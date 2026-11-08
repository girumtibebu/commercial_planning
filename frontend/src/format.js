const MULTIPLIERS = { k: 1e3, m: 1e6 }

export function makeFormatter(currency) {
  const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })
  const compact = new Intl.NumberFormat(undefined, {
    notation: 'compact',
    maximumFractionDigits: 1,
  })
  return {
    currency,
    number: (value) => (value == null || value === '' ? '' : number.format(value)),
    compact: (value) => (value == null ? '—' : compact.format(value)),
    money: (value) => (value == null ? '—' : number.format(value)),
    percent: (value) => (value == null ? '—' : `${value.toFixed(1)}%`),
    signed: (value) =>
      value == null ? '—' : `${value > 0 ? '+' : ''}${number.format(value)}`,
  }
}

/** Accepts 1,200 · 1.2k · 3m · 12.5 ; returns null when the text is not a number. */
export function parseNumber(text) {
  const clean = String(text ?? '').trim().toLowerCase().replace(/[,\s]/g, '')
  if (!clean) return null
  const match = clean.match(/^(-?\d*\.?\d+)([km])?$/)
  if (!match) return null
  return parseFloat(match[1]) * (MULTIPLIERS[match[2]] || 1)
}

export function timeAgo(value) {
  if (!value) return ''
  const seconds = (Date.now() - new Date(String(value).replace(' ', 'T')).getTime()) / 1000
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`
  return new Date(String(value).replace(' ', 'T')).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: '2-digit' })
}

export function fullDate(value) {
  return value ? new Date(String(value).replace(' ', 'T')).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
}
