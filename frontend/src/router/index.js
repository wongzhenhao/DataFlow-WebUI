import { createRouter, createWebHashHistory } from 'vue-router'

import Review from '@/views/review/index.vue'

const router = createRouter({
    history: createWebHashHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'review',
            component: Review,
            meta: {
                title: 'DataFlow Results'
            }
        },
        {
            path: '/:pathMatch(.*)*',
            redirect: '/'
        }
    ]
})

router.beforeEach((to, from, next) => {
    if (to.meta.title) document.title = to.meta.title
    next()
})

export default router
