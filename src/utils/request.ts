import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api', // Use environment variable or default to /api
    timeout: 15000 // Request timeout
})

// Request interceptor
service.interceptors.request.use(
    (config) => {
        // Add token to header if it exists
        const token = localStorage.getItem('token')
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        console.error('Request error:', error)
        return Promise.reject(error)
    }
)

// Response interceptor
service.interceptors.response.use(
    (response) => {
        const res = response.data
        // You can add custom code checking here based on your backend response structure
        // For now, we assume 200 is success
        return res
    },
    (error) => {
        console.error('Response error:', error)
        const message = error.response?.data?.message || error.message || 'Error'
        ElMessage.error(message)
        return Promise.reject(error)
    }
)

export default service
