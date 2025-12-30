import { ChevronDown, Clock, Search, ShoppingBag, Sparkles, Star, Tag } from 'lucide-react'
import { useRef, useState } from 'react'
import { useQuery } from 'react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { productsApi, recoEngineApi, RecommendedProduct } from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import { useCartStore } from '../../stores/cartStore'
import { getUserDisplayName } from '../../utils/userUtils'

export default function ProductsPage() {
    const [searchParams] = useSearchParams()
    const { isAuthenticated, user } = useAuthStore()
    const { addItem, items: cartItems } = useCartStore()
    const [filters, setFilters] = useState({
        category: searchParams.get('category') || '',
        search: searchParams.get('search') || '',
        min_price: '',
        max_price: '',
        sort_by: 'name' as 'name' | 'price' | 'rating' | 'created_at',
        sort_order: 'asc' as 'asc' | 'desc',
    })

    // Track recommendation load time
    const [recoLoadTime, setRecoLoadTime] = useState<number | null>(null)
    const recoStartTime = useRef<number | null>(null)

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

    // Fetch personalized recommendations from RecoEngine (vector search + churn-based discounts)
    // Pass cart items to get better recommendations based on current cart
    const { data: recommendations, isLoading: recoLoading } = useQuery(
        ['recommendations', user?.user_id, cartItems.length], // Re-fetch when cart changes
        async () => {
            if (!user?.user_id) return null
            console.log('Fetching recommendations for user:', user.user_id, 'with', cartItems.length, 'cart items')
            recoStartTime.current = Date.now()
            setRecoLoadTime(null) // Reset on new fetch

            // Transform cart items to the format expected by the API
            const cartItemsForApi = cartItems.map(item => ({
                product_id: item.product_id,
                name: item.product?.name || '',
                category: item.product?.category || '',
                brand: item.product?.brand || '',
                price: item.price,
                quantity: item.quantity
            }))

            const result = await recoEngineApi.getRecommendations(user.user_id, cartItemsForApi)
            const elapsed = Date.now() - recoStartTime.current
            setRecoLoadTime(elapsed)
            console.log(`Recommendations loaded in ${elapsed}ms`)
            return result
        },
        {
            enabled: isAuthenticated && !!user?.user_id,
            staleTime: 0, // Always consider stale
            cacheTime: 1000, // Keep in cache for 1 second only (prevents StrictMode double-fetch)
            refetchOnWindowFocus: false,
            refetchOnMount: 'always', // Always fetch on mount
            refetchOnReconnect: false,
            retry: 2,
            retryDelay: 2000,
            onError: (err) => {
                console.log('Recommendations error:', err)
                setRecoLoadTime(null)
            }
        }
    )

    // Featured products - fallback for auth users without recommendations, or for non-auth users
    const { data: featuredProducts } = useQuery(
        'featured-products',
        () => productsApi.getProducts({ is_featured: true, limit: 8 }),
        {
            enabled: !isAuthenticated || !recommendations?.recommendations?.length,
            staleTime: 5 * 60 * 1000
        }
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
            {/* Welcome Message */}
            {isAuthenticated && user && (
                <div className="mb-6">
                    <h1 className="text-xl font-medium text-gray-900">
                        Welcome back, {getUserDisplayName(user)}
                    </h1>
                </div>
            )}

            {/* AI-Powered Recommendations (from vector search) */}
            {isAuthenticated && (
                <section className="mb-10">
                    <div className="flex items-baseline justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-amber-500" />
                            <h2 className="text-lg font-medium text-gray-900">Recommended for you</h2>
                            {recommendations?.churn_risk && recommendations.churn_risk !== 'low_risk' && (
                                <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full font-medium">
                                    Special offers
                                </span>
                            )}
                            {/* Load time indicator */}
                            {recoLoadTime !== null && !recoLoading && (
                                <span className="flex items-center gap-1 text-xs text-gray-400 ml-2">
                                    <Clock className="w-3 h-3" />
                                    {recoLoadTime < 1000
                                        ? `${recoLoadTime}ms`
                                        : `${(recoLoadTime / 1000).toFixed(1)}s`
                                    }
                                </span>
                            )}
                        </div>
                        {!recoLoading && recommendations?.recommendations && recommendations.recommendations.length > 0 && (
                            <Link to="/products?personalized=true" className="text-sm text-primary-600 hover:text-primary-700">
                                See all
                            </Link>
                        )}
                    </div>

                    {/* Loading State */}
                    {recoLoading && (
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                            {[...Array(5)].map((_, i) => (
                                <div key={i} className="animate-pulse">
                                    <div className="aspect-square bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl mb-3 flex items-center justify-center">
                                        <div className="text-center">
                                            <Sparkles className="w-6 h-6 text-amber-300 mx-auto mb-2 animate-pulse" />
                                            <span className="text-xs text-amber-400">AI curating...</span>
                                        </div>
                                    </div>
                                    <div className="h-4 bg-gray-100 rounded w-3/4 mb-2" />
                                    <div className="h-4 bg-gray-100 rounded w-1/2" />
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Recommendations Loaded */}
                    {!recoLoading && recommendations?.recommendations && recommendations.recommendations.length > 0 && (
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                            {recommendations.recommendations.slice(0, 5).map((product) => (
                                <RecommendedProductCard
                                    key={product.product_id}
                                    product={product}
                                    onAddToCart={addItem}
                                    showDiscount={product.discount_percentage > 0}
                                />
                            ))}
                        </div>
                    )}

                    {/* Fallback to Featured Products */}
                    {!recoLoading && (!recommendations?.recommendations || recommendations.recommendations.length === 0) && featuredProducts?.items && featuredProducts.items.length > 0 && (
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                            {featuredProducts.items.slice(0, 5).map((product) => (
                                <ProductCard key={product.product_id} product={product} onAddToCart={addItem} />
                            ))}
                        </div>
                    )}
                </section>
            )}

            {/* Featured Products for non-authenticated users */}
            {!isAuthenticated && featuredProducts?.items && featuredProducts.items.length > 0 && (
                <section className="mb-10">
                    <div className="flex items-baseline justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Tag className="w-5 h-5 text-primary-500" />
                            <h2 className="text-lg font-medium text-gray-900">Featured Products</h2>
                        </div>
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

// Recommended Product Card with personalized pricing
function RecommendedProductCard({
    product,
    onAddToCart,
    showDiscount
}: {
    product: RecommendedProduct
    onAddToCart: (product: any) => void
    showDiscount: boolean
}) {
    const [imageError, setImageError] = useState(false)
    const [isHovered, setIsHovered] = useState(false)

    // Convert RecommendedProduct to cart-compatible format
    const cartProduct = {
        product_id: product.product_id,
        name: product.name,
        price: product.discounted_price, // Use discounted price
        original_price: product.price,
        images: product.image ? [product.image] : [],
        category: product.category,
        brand: product.brand,
        rating: product.rating,
        review_count: product.review_count,
        stock_quantity: 100 // Assume in stock
    }

    return (
        <div
            className="group relative"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <Link to={`/products/${product.product_id}`}>
                <div className="relative aspect-square bg-gray-50 rounded-lg overflow-hidden mb-3">
                    {!imageError && product.image ? (
                        <img
                            src={product.image}
                            alt={product.name}
                            className="w-full h-full object-cover"
                            onError={() => setImageError(true)}
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center">
                            <ShoppingBag className="w-8 h-8 text-gray-300" />
                        </div>
                    )}
                    {/* Personalized Discount Badge */}
                    {showDiscount && product.discount_percentage > 0 && (
                        <span className="absolute top-2 left-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-medium px-2 py-0.5 rounded flex items-center gap-1">
                            <Tag className="w-3 h-3" />
                            -{product.discount_percentage}%
                        </span>
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
                {/* Pricing with discount */}
                <div className="flex items-baseline gap-1.5">
                    {showDiscount && product.discount_percentage > 0 ? (
                        <>
                            <span className="text-sm font-semibold text-amber-600">${product.discounted_price.toFixed(2)}</span>
                            <span className="text-xs text-gray-400 line-through">${product.price.toFixed(2)}</span>
                        </>
                    ) : (
                        <span className="text-sm font-semibold text-gray-900">${product.price.toFixed(2)}</span>
                    )}
                </div>
                {/* Recommendation reason */}
                {product.recommendation_reason && (
                    <p className="text-xs text-gray-500 italic line-clamp-1">{product.recommendation_reason}</p>
                )}
            </div>

            {/* Add to Cart - Shows on hover */}
            <div className={`mt-2 transition-opacity duration-200 ${isHovered ? 'opacity-100' : 'opacity-0 sm:opacity-0'}`}>
                <button
                    onClick={(e) => {
                        e.preventDefault()
                        onAddToCart(cartProduct)
                    }}
                    className="w-full py-2 text-xs font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
                >
                    Add to cart
                </button>
            </div>

            {/* Always visible on mobile */}
            <div className="mt-2 sm:hidden">
                <button
                    onClick={(e) => {
                        e.preventDefault()
                        onAddToCart(cartProduct)
                    }}
                    className="w-full py-2 text-xs font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
                >
                    Add to cart
                </button>
            </div>
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
