// API Response Types
export interface ApiResponse<T = unknown> {
    data?: T
    message?: string
    error?: string
}

// User Types
export interface User {
    user_id?: string
    _id?: string  // Support for different ID formats
    email?: string
    name?: string  // Support for direct name property
    profile?: UserProfile
    preferences?: UserPreferences
    created_at?: string
    is_active?: boolean
    phoneNumber?: string  // Support for additional fields
    verified?: boolean
    nameProvided?: boolean
}

export interface UserProfile {
    name: string
    age?: number
    location?: string
    loyalty_tier: 'bronze' | 'silver' | 'gold' | 'platinum'
}

export interface UserPreferences {
    categories: string[]
    brands: string[]
    price_range: {
        min: number
        max: number
    }
}

export interface LoginCredentials {
    email: string
    password: string
}

export interface RegisterData {
    email: string
    password: string
    name: string
    age?: number
    location?: string
}

export interface AuthResponse {
    access_token: string
    token_type: string
    user: User
}

// Product Types
export interface Product {
    product_id: string
    name: string
    description: string
    category: string
    subcategory?: string
    price: number
    original_price?: number
    discount_percentage: number
    brand: string
    images: string[]
    specifications: Record<string, unknown>
    stock_quantity: number
    rating: number
    review_count: number
    tags: string[]
    is_featured: boolean
    is_active: boolean
    created_at: string
    updated_at: string
}

export interface Category {
    category_id: string
    name: string
    description: string
    is_active: boolean
    sort_order: number
}

export interface ProductFilter {
    category?: string
    min_price?: number
    max_price?: number
    brand?: string
    rating?: number
    in_stock?: boolean
    is_featured?: boolean
}

// Coupon Types
export interface Coupon {
    coupon_id: string
    code: string
    name: string
    description: string
    discount_type: 'percentage' | 'fixed' | 'free_shipping'
    discount_value: number
    minimum_order_value: number
    maximum_discount?: number
    usage_limit: number
    usage_count: number
    valid_from: string
    valid_until: string
    is_active: boolean
    applicable_categories: string[]
    applicable_products: string[]
    created_at: string
}

export interface UserCoupon {
    user_coupon_id: string
    user_id: string
    coupon_id: string
    coupon: Coupon
    assigned_at: string
    used_at?: string
    is_used: boolean
    source: 'general' | 'nudge' | 'loyalty' | 'promotion'
}

export interface CouponValidation {
    is_valid: boolean
    discount_amount: number
    message: string
    coupon?: Coupon
}

// Cart Types
export interface CartItem {
    product_id: string
    product: Product
    quantity: number
    price: number
    total: number
}

export interface Cart {
    items: CartItem[]
    subtotal: number
    discount: number
    tax: number
    shipping: number
    total: number
    applied_coupon?: Coupon
}

// Order Types
export interface OrderItem {
    product_id: string
    product_name: string
    quantity: number
    price: number
    total: number
}

export interface Order {
    order_id: string
    user_id: string
    items: OrderItem[]
    subtotal: number
    discount: number
    tax: number
    shipping: number
    total: number
    status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled'
    payment_status: 'pending' | 'paid' | 'failed' | 'refunded'
    applied_coupon?: string
    shipping_address: Address
    created_at: string
    updated_at: string
}

export interface Address {
    street: string
    city: string
    state: string
    zip_code: string
    country: string
}

// Search and Pagination Types
export interface SearchParams {
    query?: string
    category?: string
    page?: number
    limit?: number
    sort_by?: 'name' | 'price' | 'rating' | 'created_at'
    sort_order?: 'asc' | 'desc'
}

export interface PaginatedResponse<T> {
    items: T[]
    total: number
    page: number
    limit: number
    pages: number
}

// Error Types
export interface ApiError {
    message: string
    code?: string
    details?: unknown
}
