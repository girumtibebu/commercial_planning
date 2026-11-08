import { createRouter, createWebHistory } from 'vue-router'

const PlanPage = () => import('./pages/PlanPage.vue')
const VersionsPage = () => import('./pages/VersionsPage.vue')
const ActivityPage = () => import('./pages/ActivityPage.vue')
const CommentsPage = () => import('./pages/CommentsPage.vue')
const DetailsPage = () => import('./pages/DetailsPage.vue')

export const PAGES = [
  { key: 'plan', label: 'Cost plan', icon: 'sheet' },
  { key: 'versions', label: 'Versions', icon: 'layers' },
  { key: 'activity', label: 'Activity', icon: 'history' },
  { key: 'comments', label: 'Comments', icon: 'message' },
  { key: 'details', label: 'Details', icon: 'info' },
]

export default createRouter({
  history: createWebHistory('/commercial-planning'),
  routes: [
    { path: '/plan/:plan', redirect: (to) => `/plan/${to.params.plan}/plan` },
    { path: '/plan/:plan/plan', name: 'plan', component: PlanPage },
    { path: '/plan/:plan/versions', name: 'versions', component: VersionsPage },
    { path: '/plan/:plan/activity', name: 'activity', component: ActivityPage },
    { path: '/plan/:plan/comments', name: 'comments', component: CommentsPage },
    { path: '/plan/:plan/details', name: 'details', component: DetailsPage },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
