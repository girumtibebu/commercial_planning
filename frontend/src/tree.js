/** Pure helpers over the merged matrix rows (flat, depth-first, each with row_key/parent_key/depth). */

export function indexRows(rows) {
  const byKey = new Map()
  const children = new Map()
  for (const row of rows) {
    byKey.set(row.row_key, row)
    const list = children.get(row.parent_key || '') || []
    list.push(row.row_key)
    children.set(row.parent_key || '', list)
  }
  return { byKey, children }
}

export function ancestorsOf(rowKey, byKey) {
  const found = []
  let parent = byKey.get(rowKey)?.parent_key
  while (parent) {
    found.push(parent)
    parent = byKey.get(parent)?.parent_key
  }
  return found
}

export function descendantsOf(rowKey, children) {
  const found = []
  for (const key of children.get(rowKey) || []) {
    found.push(key, ...descendantsOf(key, children))
  }
  return found
}

/** Rows to render: honours collapsed categories and a text/cost-type filter (keeping ancestors of matches). */
export function visibleRows(rows, { collapsed, search, costType, matchText }) {
  const { byKey, children } = indexRows(rows)
  const filtering = Boolean(search || costType)
  let included = null
  if (filtering) {
    included = new Set()
    for (const row of rows) {
      if (!matchText(row, search, costType)) continue
      included.add(row.row_key)
      ancestorsOf(row.row_key, byKey).forEach((key) => included.add(key))
      if (row.row_type === 'Category') {
        descendantsOf(row.row_key, children).forEach((key) => included.add(key))
      }
    }
  }
  return rows
    .filter((row) => !included || included.has(row.row_key))
    .filter((row) => filtering || !ancestorsOf(row.row_key, byKey).some((key) => collapsed.has(key)))
    .map((row) => ({ ...row, hasChildren: (children.get(row.row_key) || []).length > 0 }))
}

export function siblingKeys(row, children) {
  return children.get(row.parent_key || '') || []
}

/** Operation that moves a row one place up/down among its siblings, or null at the edge. */
export function moveOp(row, children, direction) {
  const siblings = siblingKeys(row, children)
  const index = siblings.indexOf(row.row_key)
  if (direction < 0) {
    if (index <= 0) return null
    return { op: 'move', row_key: row.row_key, parent_key: row.parent_key || '', before_key: siblings[index - 1] }
  }
  if (index >= siblings.length - 1) return null
  return {
    op: 'move',
    row_key: row.row_key,
    parent_key: row.parent_key || '',
    before_key: siblings[index + 2] || null,
  }
}
