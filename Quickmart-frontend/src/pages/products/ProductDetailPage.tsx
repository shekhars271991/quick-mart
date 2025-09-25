import { Minus, Plus, ShoppingBag, Star } from 'lucide-react'
import { useState } from 'react'
import { useQuery } from 'react-query'
import { useParams } from 'react-router-dom'
import { productsApi } from '../../lib/api'
import { useCartStore } from '../../stores/cartStore'

export default function ProductDetailPage() {
    const { id } = useParams<{ id: string }>()
    const { addItem } = useCartStore()
    const [quantity, setQuantity] = useState(1)

    const { data: product, isLoading, error } = useQuery(
        ['product', id],
        () => productsApi.getProduct(id!),
        {
            enabled: !!id,
        }
    )

    if (isLoading) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="animate-pulse">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <div className="aspect-square bg-gray-200 rounded-lg"></div>
                        <div className="space-y-4">
                            <div className="h-8 bg-gray-200 rounded"></div>
                            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                            <div className="h-6 bg-gray-200 rounded w-1/2"></div>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    if (error || !product) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-gray-900">Product not found</h1>
                    <p className="text-gray-600 mt-2">The product you're looking for doesn't exist.</p>
                </div>
            </div>
        )
    }

    const handleAddToCart = () => {
        addItem(product, quantity)
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Product Image */}
                <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                    {product.images && product.images.length > 0 ? (
                        <img
                            src={product.images[0]}
                            alt={product.name}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                                target.nextElementSibling?.classList.remove('hidden');
                            }}
                        />
                    ) : null}
                    <div className="w-full h-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center hidden">
                        <ShoppingBag className="w-24 h-24 text-gray-400" />
                    </div>
                </div>

                {/* Product Details */}
                <div className="space-y-6">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">{product.name}</h1>
                        <p className="text-lg text-gray-600 mt-2">{product.description}</p>
                    </div>

                    {/* Rating */}
                    <div className="flex items-center space-x-4">
                        <div className="flex items-center">
                            {[...Array(5)].map((_, i) => (
                                <Star
                                    key={i}
                                    className={`w-5 h-5 ${i < Math.floor(product.rating)
                                        ? 'text-yellow-400 fill-current'
                                        : 'text-gray-300'
                                        }`}
                                />
                            ))}
                        </div>
                        <span className="text-sm text-gray-600">
                            {product.rating.toFixed(1)} ({product.review_count} reviews)
                        </span>
                    </div>

                    {/* Price */}
                    <div className="flex items-center space-x-4">
                        <span className="text-3xl font-bold text-gray-900">
                            ${product.price.toFixed(2)}
                        </span>
                        {product.original_price && product.original_price > product.price && (
                            <>
                                <span className="text-xl text-gray-500 line-through">
                                    ${product.original_price.toFixed(2)}
                                </span>
                                <span className="badge-error">
                                    -{product.discount_percentage}% OFF
                                </span>
                            </>
                        )}
                    </div>

                    {/* Stock Status */}
                    <div>
                        {product.stock_quantity > 0 ? (
                            <span className="badge-success">
                                {product.stock_quantity} in stock
                            </span>
                        ) : (
                            <span className="badge-error">Out of stock</span>
                        )}
                    </div>

                    {/* Quantity Selector */}
                    <div className="flex items-center space-x-4">
                        <span className="text-sm font-medium text-gray-700">Quantity:</span>
                        <div className="flex items-center border border-gray-300 rounded-lg">
                            <button
                                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                                className="p-2 hover:bg-gray-100"
                                disabled={quantity <= 1}
                            >
                                <Minus className="w-4 h-4" />
                            </button>
                            <span className="px-4 py-2 border-x border-gray-300">{quantity}</span>
                            <button
                                onClick={() => setQuantity(Math.min(product.stock_quantity, quantity + 1))}
                                className="p-2 hover:bg-gray-100"
                                disabled={quantity >= product.stock_quantity}
                            >
                                <Plus className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    {/* Add to Cart Button */}
                    <button
                        onClick={handleAddToCart}
                        disabled={product.stock_quantity === 0}
                        className="w-full btn-primary btn-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {product.stock_quantity === 0 ? 'Out of Stock' : 'Add to Cart'}
                    </button>

                    {/* Product Specifications */}
                    {product.specifications && Object.keys(product.specifications).length > 0 && (
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900 mb-3">Specifications</h3>
                            <div className="space-y-2">
                                {Object.entries(product.specifications).map(([key, value]) => (
                                    <div key={key} className="flex justify-between py-2 border-b border-gray-200">
                                        <span className="text-gray-600 capitalize">{key.replace('_', ' ')}</span>
                                        <span className="text-gray-900 font-medium">{String(value)}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Tags */}
                    {product.tags && product.tags.length > 0 && (
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900 mb-3">Tags</h3>
                            <div className="flex flex-wrap gap-2">
                                {product.tags.map((tag) => (
                                    <span key={tag} className="badge-primary">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
