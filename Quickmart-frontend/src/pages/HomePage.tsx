import { ArrowRight, Shield, ShoppingBag, Star, Truck, Zap } from 'lucide-react'
import { useQuery } from 'react-query'
import { Link } from 'react-router-dom'
import { productsApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'

export default function HomePage() {
    const { isAuthenticated, user } = useAuthStore()

    // Fetch featured products
    const { data: featuredProducts } = useQuery(
        'featured-products',
        () => productsApi.getProducts({ is_featured: true, limit: 8 }),
        {
            staleTime: 5 * 60 * 1000, // 5 minutes
        }
    )

    return (
        <div className="space-y-16">
            {/* Hero Section */}
            <section className="relative bg-gradient-to-r from-primary-600 to-primary-800 text-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-8">
                            <h1 className="text-4xl md:text-6xl font-bold leading-tight">
                                Smart Shopping with{' '}
                                <span className="text-yellow-300">AI-Powered</span> Recommendations
                            </h1>
                            <p className="text-xl text-blue-100">
                                Discover personalized deals, get intelligent product suggestions, and enjoy a seamless shopping experience tailored just for you.
                            </p>

                            {isAuthenticated ? (
                                <div className="space-y-4">
                                    <p className="text-lg">
                                        Welcome back, <span className="font-semibold">{user?.profile.name}</span>!
                                        Ready to discover something amazing?
                                    </p>
                                    <div className="flex flex-col sm:flex-row gap-4">
                                        <Link
                                            to="/products"
                                            className="btn-secondary btn-lg inline-flex items-center"
                                        >
                                            Browse Products
                                            <ArrowRight className="ml-2 w-5 h-5" />
                                        </Link>
                                        <Link
                                            to="/coupons"
                                            className="btn-outline btn-lg text-white border-white hover:bg-white hover:text-primary-600"
                                        >
                                            View My Coupons
                                        </Link>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex flex-col sm:flex-row gap-4">
                                    <Link
                                        to="/register"
                                        className="btn-secondary btn-lg inline-flex items-center"
                                    >
                                        Get Started Free
                                        <ArrowRight className="ml-2 w-5 h-5" />
                                    </Link>
                                    <Link
                                        to="/products"
                                        className="btn-outline btn-lg text-white border-white hover:bg-white hover:text-primary-600"
                                    >
                                        Browse Products
                                    </Link>
                                </div>
                            )}
                        </div>

                        <div className="relative">
                            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
                                <div className="space-y-6">
                                    <div className="flex items-center space-x-4">
                                        <div className="w-12 h-12 bg-yellow-400 rounded-full flex items-center justify-center">
                                            <Zap className="w-6 h-6 text-yellow-900" />
                                        </div>
                                        <div>
                                            <h3 className="font-semibold">AI-Powered Recommendations</h3>
                                            <p className="text-blue-100">Personalized just for you</p>
                                        </div>
                                    </div>

                                    <div className="flex items-center space-x-4">
                                        <div className="w-12 h-12 bg-green-400 rounded-full flex items-center justify-center">
                                            <Shield className="w-6 h-6 text-green-900" />
                                        </div>
                                        <div>
                                            <h3 className="font-semibold">Smart Coupons</h3>
                                            <p className="text-blue-100">Automatic savings & deals</p>
                                        </div>
                                    </div>

                                    <div className="flex items-center space-x-4">
                                        <div className="w-12 h-12 bg-purple-400 rounded-full flex items-center justify-center">
                                            <Truck className="w-6 h-6 text-purple-900" />
                                        </div>
                                        <div>
                                            <h3 className="font-semibold">Fast Delivery</h3>
                                            <p className="text-blue-100">Free shipping over $50</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Featured Products */}
            {featuredProducts?.items && featuredProducts.items.length > 0 && (
                <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl font-bold text-gray-900 mb-4">Featured Products</h2>
                        <p className="text-lg text-gray-600">Discover our most popular and trending items</p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                        {featuredProducts.items.slice(0, 8).map((product) => (
                            <Link
                                key={product.product_id}
                                to={`/products/${product.product_id}`}
                                className="card hover:shadow-lg transition-shadow duration-300 group"
                            >
                                <div className="aspect-square bg-gray-100 rounded-t-lg overflow-hidden">
                                    <div className="w-full h-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center">
                                        <ShoppingBag className="w-12 h-12 text-gray-400" />
                                    </div>
                                </div>

                                <div className="p-4">
                                    <h3 className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors line-clamp-2">
                                        {product.name}
                                    </h3>

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
                                </div>
                            </Link>
                        ))}
                    </div>

                    <div className="text-center">
                        <Link
                            to="/products"
                            className="btn-primary btn-lg inline-flex items-center"
                        >
                            View All Products
                            <ArrowRight className="ml-2 w-5 h-5" />
                        </Link>
                    </div>
                </section>
            )}

            {/* Features Section */}
            <section className="bg-gray-100">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl font-bold text-gray-900 mb-4">Why Choose QuickMart?</h2>
                        <p className="text-lg text-gray-600">Experience the future of online shopping</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="text-center">
                            <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Zap className="w-8 h-8 text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">AI-Powered Recommendations</h3>
                            <p className="text-gray-600">
                                Our advanced AI analyzes your preferences and shopping behavior to suggest products you'll love.
                            </p>
                        </div>

                        <div className="text-center">
                            <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Shield className="w-8 h-8 text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Smart Savings</h3>
                            <p className="text-gray-600">
                                Automatically receive personalized coupons and deals based on your shopping patterns.
                            </p>
                        </div>

                        <div className="text-center">
                            <div className="w-16 h-16 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Truck className="w-8 h-8 text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Fast & Free Delivery</h3>
                            <p className="text-gray-600">
                                Enjoy free shipping on orders over $50 with our reliable and fast delivery network.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            {!isAuthenticated && (
                <section className="bg-primary-600 text-white">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
                        <h2 className="text-3xl font-bold mb-4">Ready to Start Shopping Smarter?</h2>
                        <p className="text-xl text-blue-100 mb-8">
                            Join thousands of satisfied customers who save money with our AI-powered recommendations.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Link
                                to="/register"
                                className="btn-secondary btn-lg inline-flex items-center"
                            >
                                Create Free Account
                                <ArrowRight className="ml-2 w-5 h-5" />
                            </Link>
                            <Link
                                to="/products"
                                className="btn-outline btn-lg text-white border-white hover:bg-white hover:text-primary-600"
                            >
                                Browse Products
                            </Link>
                        </div>
                    </div>
                </section>
            )}
        </div>
    )
}
