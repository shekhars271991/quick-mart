import axios, { AxiosResponse } from 'axios'
import toast from 'react-hot-toast'
import type {
    ApiResponse,
    AuthResponse,
    Category,
    Coupon,
    CouponValidation,
    LoginCredentials,
    Order,
    PaginatedResponse,
    Product,
    ProductFilter,
    RegisterData,
    SearchParams,
    User,
    UserCoupon,
    UserCouponWithDetails,
} from '../types'

// Create axios instance with base configuration
// Default to 3011 for local development (./run.sh local), 3010 for Docker
const api = axios.create({
    baseURL: (import.meta.env.VITE_API_URL as string) || 'http://localhost:3011',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor to add auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor for error handling
api.interceptors.response.use(
    (response: AxiosResponse) => {
        return response
    },
    (error) => {
        if (error.response?.status === 401) {
            // Only redirect to login if not already on login/register pages
            const currentPath = window.location.pathname
            const isAuthPage = currentPath === '/login' || currentPath === '/register'

            if (!isAuthPage) {
                // Clear auth data and redirect only if not on auth pages
                localStorage.removeItem('access_token')
                localStorage.removeItem('user')
                window.location.href = '/login'
            }
            // If on auth page, let the component handle the error
        } else if (error.response?.status >= 500) {
            toast.error('Server error. Please try again later.')
        } else if (error.response?.data?.detail) {
            // Handle different types of error details
            const detail = error.response.data.detail
            if (typeof detail === 'string') {
                toast.error(detail)
            } else if (Array.isArray(detail) && detail.length > 0) {
                // Handle validation errors (422 status)
                const firstError = detail[0]
                const message = firstError?.msg || 'Validation error'
                toast.error(message)
            } else {
                toast.error('Request failed')
            }
        } else if (error.message) {
            toast.error(error.message)
        }
        return Promise.reject(error)
    }
)

// API Methods
export const authApi = {
    login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
        const response = await api.post('/api/auth/login', {
            email: credentials.email,
            password: credentials.password,
        })
        return response.data
    },

    register: async (data: RegisterData): Promise<ApiResponse<User>> => {
        // Transform data to match backend UserCreate model structure
        const payload = {
            email: data.email,
            password: data.password,
            profile: {
                name: data.name,
                age: data.age,
                location: data.location,
            },
            preferences: {
                favorite_categories: [],
                notification_enabled: true,
            },
        }
        const response = await api.post('/api/auth/register', payload)
        return response.data
    },

    getProfile: async (): Promise<User> => {
        const response = await api.get('/api/auth/profile')
        return response.data
    },

    updateProfile: async (data: Partial<User>): Promise<ApiResponse<User>> => {
        const response = await api.put('/api/auth/profile', data)
        return response.data
    },
}

export const productsApi = {
    getProducts: async (params?: SearchParams & ProductFilter): Promise<PaginatedResponse<Product>> => {
        const response = await api.get('/api/products', { params })
        // Transform backend response to match frontend interface
        const backendData = response.data
        return {
            items: backendData.products,
            total: backendData.total,
            page: backendData.page,
            limit: backendData.limit,
            pages: Math.ceil(backendData.total / backendData.limit)
        }
    },

    getProduct: async (id: string): Promise<Product> => {
        const response = await api.get(`/api/products/${id}`)
        return response.data
    },

    searchProducts: async (query: string, params?: SearchParams): Promise<PaginatedResponse<Product>> => {
        const response = await api.get('/api/products/search', {
            params: { q: query, ...params },
        })
        // Transform backend response to match frontend interface
        const backendData = response.data
        return {
            items: backendData.products,
            total: backendData.total,
            page: backendData.page,
            limit: backendData.limit,
            pages: Math.ceil(backendData.total / backendData.limit)
        }
    },

    getCategories: async (): Promise<Category[]> => {
        const response = await api.get('/api/products/categories/')
        return response.data
    },

    getProductsByCategory: async (category: string, params?: SearchParams): Promise<PaginatedResponse<Product>> => {
        const response = await api.get(`/api/products/category/${category}`, { params })
        // Transform backend response to match frontend interface
        const backendData = response.data
        return {
            items: backendData.products,
            total: backendData.total,
            page: backendData.page,
            limit: backendData.limit,
            pages: Math.ceil(backendData.total / backendData.limit)
        }
    },
}

export const couponsApi = {
    getAvailableCoupons: async (): Promise<Coupon[]> => {
        const response = await api.get('/api/coupons/available')
        return response.data
    },

    getUserCoupons: async (): Promise<UserCouponWithDetails[]> => {
        const response = await api.get('/api/coupons/user')
        return response.data
    },

    validateCoupon: async (code: string, orderTotal: number): Promise<CouponValidation> => {
        const response = await api.post('/api/coupons/validate', {
            code,
            order_total: orderTotal,
        })
        return response.data
    },

    applyCoupon: async (code: string, orderTotal: number): Promise<ApiResponse> => {
        const response = await api.post('/api/coupons/apply', {
            code,
            order_total: orderTotal,
        })
        return response.data
    },

    getCouponHistory: async (): Promise<UserCoupon[]> => {
        const response = await api.get('/api/coupons/history')
        return response.data
    },
}

export const usersApi = {
    getPreferences: async (): Promise<Record<string, unknown>> => {
        const response = await api.get('/api/users/preferences')
        return response.data
    },

    updatePreferences: async (preferences: Record<string, unknown>): Promise<ApiResponse> => {
        const response = await api.put('/api/users/preferences', preferences)
        return response.data
    },

    getPurchaseHistory: async (): Promise<Order[]> => {
        const response = await api.get('/api/users/purchase-history')
        return response.data
    },
}

export const cartApi = {
    addToCart: async (productId: string, quantity: number = 1): Promise<ApiResponse> => {
        const response = await api.post('/api/cart/add', {
            product_id: productId,
            quantity,
        })
        return response.data
    },
}

export const adminApi = {
    initializeData: async (): Promise<ApiResponse> => {
        const response = await api.post('/api/admin/initialize-data')
        return response.data
    },

    resetData: async (): Promise<ApiResponse> => {
        const response = await api.post('/api/admin/reset-data')
        return response.data
    },
}

// RecoEngine API for churn prediction
export const recoEngineApi = {
    predictChurn: async (userId: string): Promise<any> => {
        // Default to 8001 for local development (./run.sh local), 8000 for Docker
        const recoEngineUrl = (import.meta.env.VITE_RECO_ENGINE_URL as string) || 'http://localhost:8001'
        const response = await axios.post(`${recoEngineUrl}/predict/${userId}`)
        return response.data
    },
}

// User Messages API
export const messagesApi = {
    // Get user messages from nudge system
    getMessages: async (): Promise<{messages: any[], total_messages: number, unread_count: number}> => {
        const response = await api.get('/api/users/messages')
        return response.data
    },

    // Mark message as read
    markAsRead: async (messageId: string): Promise<ApiResponse> => {
        const response = await api.put(`/api/users/messages/${messageId}/mark-read`)
        return response.data
    },
}

// Health check
export const healthApi = {
    check: async (): Promise<Record<string, unknown>> => {
        const response = await api.get('/health')
        return response.data
    },
}

export default api
