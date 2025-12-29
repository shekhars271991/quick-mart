import { ChevronDown, Search, ShoppingBag, Star } from 'lucide-react'
import { useState } from 'react'
import { useQuery } from 'react-query'
import { Link, useSearchParams } from 'react-router-dom'
import RecentCouponDisplay from '../../components/RecentCouponDisplay'
import { useRecentCoupon } from '../../hooks/useRecentCoupon'
import { productsApi } from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import { useCartStore } from '../../stores/cartStore'
import { getUserDisplayName } from '../../utils/userUtils'

export default function ProductsPage() {
    const [searchParams] = useSearchParams()
    const { isAuthenticated, user } = useAuthStore()
    const { addItem } = useCartStore()
    const { recentCoupon, loading: couponLoading } = useRecentCoupon()
    const [filters, setFilters] = useState({
        category: searchParams.get('category') || '',
        search: searchParams.get('search') || '',
        min_price: '',
        max_price: '',
        sort_by: 'name' as 'name' | 'price' | 'rating' | 'created_at',
        sort_order: 'asc' as 'asc' | 'desc',
    })

    const { data: products, isLoading } = useQuery(
        ['products', filters],
        () => {
            const apiFilters = {
                ...filters,
                min_price: filters.min_price ? parseFloat(filters.min_price) : undefined,
                max_price: filters.max_price ? parseFloat(filters.max_price) : undefined,
            }
            return productsApi.getProducts(apiFilters)
        },
        { keepPreviousData: true }
    )

    const { data: categories } = useQuery('categories', productsApi.getCategories)

    const { data: featuredProducts } = useQuery(
        'featured-products',
        () => productsApi.getProducts({ is_featured: true, limit: 8 }),
        { enabled: isAuthenticated, staleTime: 5 * 60 * 1000 }
    )

    if (isLoading) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                    {[...Array(10)].map((_, i) => (
                        <div key={i} className="animate-pulse">
                            <div className="aspect-square bg-gray-100 rounded-lg mb-3" />
                            <div className="h-4 bg-gray-100 rounded w-3/4 mb-2" />
                            <div className="h-4 bg-gray-100 rounded w-1/2" />
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {/* Coupon Banner */}
            {isAuthenticated && !couponLoading && recentCoupon && (
                <div className="mb-6">
                    <RecentCouponDisplay userCouponWithDetails={recentCoupon} />
                </div>
            )}

            {/* Welcome Message */}
            {isAuthenticated && user && !recentCoupon && (
                <div className="mb-6">
                    <h1 className="text-xl font-medium text-gray-900">
                        Welcome back, {getUserDisplayName(user)}
                    </h1>
                </div>
            )}

            {/* Featured Products */}
            {isAuthenticated && featuredProducts?.items && featuredProducts.items.length > 0 && (
                <section className="mb-10">
                    <div className="flex items-baseline justify-between mb-4">
                        <h2 className="text-lg font-medium text-gray-900">Recommended for you</h2>
                        <Link to="/products?is_featured=true" className="text-sm text-primary-600 hover:text-primary-700">
                            See all
                        </Link>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                        {featuredProducts.items.slice(0, 5).map((product) => (
                            <ProductCard key={product.product_id} product={product} onAddToCart={addItem} />
                        ))}
                    </div>
                </section>
            )}

            {/* Filters Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-6 pb-4 border-b border-gray-200">
                <div className="relative flex-1 max-w-xs">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search products..."
                        value={filters.search}
                        onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                        className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
                    />
                </div>
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <select
                            value={filters.category}
                            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                            className="appearance-none pl-3 pr-8 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-gray-300 cursor-pointer"
                        >
                            <option value="">All Categories</option>
                            {categories?.map((category) => (
                                <option key={category.category_id} value={category.category_id}>
                                    {category.name}
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                    </div>
                    <input
                        type="number"
                        placeholder="Min $"
                        value={filters.min_price}
                        onChange={(e) => setFilters({ ...filters, min_price: e.target.value })}
                        className="w-20 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300"
                    />
                    <span className="text-gray-400">-</span>
                    <input
                        type="number"
                        placeholder="Max $"
                        value={filters.max_price}
                        onChange={(e) => setFilters({ ...filters, max_price: e.target.value })}
                        className="w-20 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300"
                    />
                </div>
                <div className="text-sm text-gray-500 ml-auto">
                    {products?.total || 0} products
                </div>
            </div>

            {/* Products Grid */}
            {products?.items && products.items.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                    {products.items.map((product) => (
                        <ProductCard key={product.product_id} product={product} onAddToCart={addItem} />
                    ))}
                </div>
            ) : (
                <div className="text-center py-16">
                    <ShoppingBag className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">No products found</p>
                    <button
                        onClick={() => setFilters({ category: '', search: '', min_price: '', max_price: '', sort_by: 'name', sort_order: 'asc' })}
                        className="mt-3 text-sm text-primary-600 hover:text-primary-700"
                    >
                        Clear filters
                    </button>
                </div>
            )}
        </div>
    )
}

// Separate ProductCard component for cleaner code
function ProductCard({ product, onAddToCart }: { product: any; onAddToCart: (product: any) => void }) {
    const [imageError, setImageError] = useState(false)
    const [isHovered, setIsHovered] = useState(false)

    return (
        <div 
            className="group"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <Link to={`/products/${product.product_id}`}>
                <div className="relative aspect-square bg-gray-50 rounded-lg overflow-hidden mb-3">
                    {!imageError && product.images && product.images.length > 0 ? (
                        <img
                            src={product.images[0]}
                            alt={product.name}
                            className="w-full h-full object-cover"
                            onError={() => setImageError(true)}
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center">
                            <ShoppingBag className="w-8 h-8 text-gray-300" />
                        </div>
                    )}
                    {product.discount_percentage > 0 && (
                        <span className="absolute top-2 left-2 bg-red-500 text-white text-xs font-medium px-1.5 py-0.5 rounded">
                            -{product.discount_percentage}%
                        </span>
                    )}
                    {product.stock_quantity === 0 && (
                        <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
                            <span className="text-sm text-gray-500 font-medium">Out of stock</span>
                        </div>
                    )}
                </div>
            </Link>

            <div className="space-y-1">
                <p className="text-xs text-gray-500">{product.brand}</p>
                <Link to={`/products/${product.product_id}`}>
                    <h3 className="text-sm text-gray-900 font-medium line-clamp-2 leading-tight group-hover:text-primary-600 transition-colors">
                        {product.name}
                    </h3>
                </Link>
                <div className="flex items-center gap-1">
                    <Star className="w-3 h-3 text-yellow-400 fill-current" />
                    <span className="text-xs text-gray-600">{product.rating.toFixed(1)}</span>
                    <span className="text-xs text-gray-400">({product.review_count})</span>
                </div>
                <div className="flex items-baseline gap-1.5">
                    <span className="text-sm font-semibold text-gray-900">${product.price.toFixed(2)}</span>
                    {product.original_price && product.original_price > product.price && (
                        <span className="text-xs text-gray-400 line-through">${product.original_price.toFixed(2)}</span>
                    )}
                </div>
            </div>

            {/* Add to Cart - Shows on hover */}
            <div className={`mt-2 transition-opacity duration-200 ${isHovered ? 'opacity-100' : 'opacity-0 sm:opacity-0'}`}>
                <button
                    onClick={(e) => {
                        e.preventDefault()
                        onAddToCart(product)
                    }}
                    disabled={product.stock_quantity === 0}
                    className="w-full py-2 text-xs font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                    Add to cart
                </button>
            </div>

            {/* Always visible on mobile */}
            <div className="mt-2 sm:hidden">
                <button
                    onClick={(e) => {
                        e.preventDefault()
                        onAddToCart(product)
                    }}
                    disabled={product.stock_quantity === 0}
                    className="w-full py-2 text-xs font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                    Add to cart
                </button>
            </div>
        </div>
    )
}
