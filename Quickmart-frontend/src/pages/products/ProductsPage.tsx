import { Search, ShoppingBag, Star } from 'lucide-react'
import { useState } from 'react'
import { useQuery } from 'react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { productsApi } from '../../lib/api'
import { useCartStore } from '../../stores/cartStore'

export default function ProductsPage() {
    const [searchParams] = useSearchParams()
    const { addItem } = useCartStore()
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
            // Convert string filters to appropriate types for API
            const apiFilters = {
                ...filters,
                min_price: filters.min_price ? parseFloat(filters.min_price) : undefined,
                max_price: filters.max_price ? parseFloat(filters.max_price) : undefined,
            }
            return productsApi.getProducts(apiFilters)
        },
        {
            keepPreviousData: true,
        }
    )

    const { data: categories } = useQuery('categories', productsApi.getCategories)

    if (isLoading) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-gray-200 rounded w-1/4"></div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[...Array(8)].map((_, i) => (
                            <div key={i} className="card">
                                <div className="aspect-square bg-gray-200 rounded-t-lg"></div>
                                <div className="p-4 space-y-2">
                                    <div className="h-4 bg-gray-200 rounded"></div>
                                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Products</h1>
                <p className="text-gray-600 mt-2">
                    Discover our wide range of products with AI-powered recommendations
                </p>
            </div>

            {/* Filters */}
            <div className="mb-8 p-4 bg-white rounded-lg border border-gray-200">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Search
                        </label>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                            <input
                                type="text"
                                placeholder="Search products..."
                                value={filters.search}
                                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                                className="input pl-10"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Category
                        </label>
                        <select
                            value={filters.category}
                            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                            className="input"
                        >
                            <option value="">All Categories</option>
                            {categories?.map((category) => (
                                <option key={category.category_id} value={category.category_id}>
                                    {category.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Min Price
                        </label>
                        <input
                            type="number"
                            placeholder="$0"
                            value={filters.min_price}
                            onChange={(e) => setFilters({ ...filters, min_price: e.target.value })}
                            className="input"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Max Price
                        </label>
                        <input
                            type="number"
                            placeholder="$1000"
                            value={filters.max_price}
                            onChange={(e) => setFilters({ ...filters, max_price: e.target.value })}
                            className="input"
                        />
                    </div>
                </div>
            </div>

            {/* Products Grid */}
            {products?.items && products.items.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {products.items.map((product) => (
                        <div key={product.product_id} className="card hover:shadow-lg transition-shadow duration-300">
                            <Link to={`/products/${product.product_id}`}>
                                <div className="aspect-square bg-gray-100 rounded-t-lg overflow-hidden">
                                    <div className="w-full h-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center">
                                        <ShoppingBag className="w-12 h-12 text-gray-400" />
                                    </div>
                                </div>
                            </Link>

                            <div className="p-4">
                                <Link to={`/products/${product.product_id}`}>
                                    <h3 className="font-semibold text-gray-900 hover:text-primary-600 transition-colors line-clamp-2">
                                        {product.name}
                                    </h3>
                                </Link>

                                <div className="flex items-center mt-2">
                                    <div className="flex items-center">
                                        <Star className="w-4 h-4 text-yellow-400 fill-current" />
                                        <span className="text-sm text-gray-600 ml-1">
                                            {product.rating.toFixed(1)} ({product.review_count})
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between mt-3">
                                    <div className="flex items-center space-x-2">
                                        <span className="text-lg font-bold text-gray-900">
                                            ${product.price.toFixed(2)}
                                        </span>
                                        {product.original_price && product.original_price > product.price && (
                                            <span className="text-sm text-gray-500 line-through">
                                                ${product.original_price.toFixed(2)}
                                            </span>
                                        )}
                                    </div>

                                    {product.discount_percentage > 0 && (
                                        <span className="badge-error text-xs">
                                            -{product.discount_percentage}%
                                        </span>
                                    )}
                                </div>

                                <button
                                    onClick={() => addItem(product)}
                                    className="w-full btn-primary btn-sm mt-3"
                                    disabled={product.stock_quantity === 0}
                                >
                                    {product.stock_quantity === 0 ? 'Out of Stock' : 'Add to Cart'}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center py-12">
                    <ShoppingBag className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No products found</h3>
                    <p className="text-gray-600">Try adjusting your search or filter criteria</p>
                </div>
            )}
        </div>
    )
}
