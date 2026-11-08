<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[name] || ''" />
  </svg>
</template>

<script setup>
defineProps({ name: String, size: { type: Number, default: 16 }, strokeWidth: { type: Number, default: 1.6 } })

const PATHS = {
  sheet: 'M2.5 3.5h11v9h-11zM2.5 6.5h11M2.5 9.5h11M6 3.5v9',
  layers: 'M8 2.5 13.5 5.5 8 8.5 2.5 5.5zM2.5 8 8 11l5.5-3M2.5 10.5 8 13.5l5.5-3',
  history: 'M2.5 8a5.5 5.5 0 1 0 1.7-4M2.5 2.5v2.5H5M8 5v3.5L10 10',
  message: 'M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z',
  info: 'M8 13.5a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11ZM8 7.5V11M8 5.2h.01',
  back: 'M13 8H3M7 4 3 8l4 4',
  chevright: 'M6 4l4 4-4 4',
  chevdown: 'M4 6l4 4 4-4',
  plus: 'M8 3v10M3 8h10',
  close: 'M4 4l8 8M12 4l-8 8',
  search: 'M7 2.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9ZM10.5 10.5l3 3',
  dots: 'M3.5 8h.01M8 8h.01M12.5 8h.01',
  user: 'M8 8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM3 13c.5-2 2.5-3 5-3s4.5 1 5 3',
  check: 'M3 8.5 6.5 12 13 4',
  lock: 'M4 7.5h8v5.5H4zM5.5 7.5V5.5a2.5 2.5 0 0 1 5 0v2',
  tag: 'M2.5 8.5v-5h5l6 6-5 5zM5.2 5.2h.01',
  paperclip: 'M12 7.5 7.5 12a2.8 2.8 0 0 1-4-4l5-5a1.9 1.9 0 0 1 2.7 2.7l-5 5a.9.9 0 0 1-1.3-1.3L9.5 5',
  share: 'M11.5 5.5a1.7 1.7 0 1 0 0-3.4 1.7 1.7 0 0 0 0 3.4ZM4.5 9.7a1.7 1.7 0 1 0 0-3.4 1.7 1.7 0 0 0 0 3.4ZM11.5 13.9a1.7 1.7 0 1 0 0-3.4 1.7 1.7 0 0 0 0 3.4ZM6 7.2l4-1.8M6 8.8l4 1.8',
  trash: 'M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.5 8.5h6l.5-8.5',
  copy: 'M5.5 5.5h7v8h-7zM3.5 10.5v-8h7',
  indent: 'M2.5 3.5h11M8 8h5.5M8 12.5h5.5M2.5 6l2.5 2-2.5 2',
  outdent: 'M2.5 3.5h11M8 8h5.5M8 12.5h5.5M5 6 2.5 8 5 10',
  up: 'M8 13V3M4 7l4-4 4 4',
  down: 'M8 3v10M4 9l4 4 4-4',
  split: 'M8 2.5v4M8 6.5 3.5 13M8 6.5 12.5 13',
  edit: 'M3 13l.7-3L10.5 3.2a1.4 1.4 0 0 1 2 2L5.7 12.3z',
  compare: 'M5.5 3.5v9M10.5 3.5v9M2.5 6l3-2.5 3 2.5M7.5 10l3 2.5 3-2.5',
  clock: 'M8 13.5a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11ZM8 5v3.5L10 10',
  eye: 'M1.5 8s2.3-4.5 6.5-4.5S14.5 8 14.5 8 12.2 12.5 8 12.5 1.5 8 1.5 8ZM8 9.8a1.8 1.8 0 1 0 0-3.6 1.8 1.8 0 0 0 0 3.6Z',
  menu: 'M2 4h12M2 8h12M2 12h12',
  external: 'M9 3h4v4M13 3 7.5 8.5M11 9.5V13H3V5h3.5',
}
</script>
