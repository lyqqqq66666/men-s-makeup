import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '../store/user'

const routes: Array<RouteRecordRaw> = [
    {
        path: '/',
        name: 'Home',
        component: () => import('../views/Home.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('../views/Login.vue')
    },
    {
        path: '/upload',
        name: 'Upload',
        component: () => import('../views/UploadView.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/result',
        name: 'Result',
        component: () => import('../views/ResultView.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/pca-result',
        name: 'PcaResult',
        component: () => import('../views/PcaResultView.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/shop',
        name: 'Shop',
        component: () => import('../views/Shop.vue')
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach((to, _from, next) => {
    const userStore = useUserStore()
    if (to.meta.requiresAuth && !userStore.token) {
        next('/login')
    } else {
        next()
    }
})

export default router
