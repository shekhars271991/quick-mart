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
} from '../types'

// Create axios instance with base configuration
const api = axios.create({
    baseURL: (import.meta.env.VITE_API_URL as string) || 'http://localhost:3010',
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
            // Clear auth data on unauthorized
            localStorage.removeItem('access_token')
            localStorage.removeItem('user')
            window.location.href = '/login'
        } else if (error.response?.status >= 500) {
            toast.error('Server error. Please try again later.')
        } else if (error.response?.data?.detail) {
            toast.error(error.response.data.detail)
        } else if (error.message) {
            toast.error(error.message)
        }
        return Promise.reject(error)
    }
)

// API Methods
export const authApi = {
    login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
        const formData = new FormData()
        formData.append('username', credentials.email)
        formData.append('password', credentials.password)

        const response = await api.post('/api/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        })
        return response.data
    },

    register: async (data: RegisterData): Promise<ApiResponse<User>> => {
        const response = await api.post('/api/auth/register', data)
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
        return response.data
    },

    getProduct: async (id: string): Promise<Product> => {
        const response = await api.get(`/api/products/${id}`)
        return response.data
    },

    searchProducts: async (query: string, params?: SearchParams): Promise<PaginatedResponse<Product>> => {
        const response = await api.get('/api/products/search', {
            params: { q: query, ...params },
        })
        return response.data
    },

    getCategories: async (): Promise<Category[]> => {
        const response = await api.get('/api/products/categories')
        return response.data
    },

    getProductsByCategory: async (category: string, params?: SearchParams): Promise<PaginatedResponse<Product>> => {
        const response = await api.get(`/api/products/category/${category}`, { params })
        return response.data
    },
}

export const couponsApi = {
    getAvailableCoupons: async (): Promise<Coupon[]> => {
        const response = await api.get('/api/coupons/available')
        return response.data
    },

    getUserCoupons: async (): Promise<UserCoupon[]> => {
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

// Health check
export const healthApi = {
    check: async (): Promise<Record<string, unknown>> => {
        const response = await api.get('/health')
        return response.data
    },
}

export default api
