import { ArrowRight, Minus, Plus, ShoppingBag, Sparkles, Trash2, TruckIcon } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import RecentCouponDisplay from '../../components/RecentCouponDisplay'
import { useRecentCoupon } from '../../hooks/useRecentCoupon'
import { cartApi } from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import { useCartStore } from '../../stores/cartStore'

export default function CartPage() {
    const { items, updateQuantity, removeItem, subtotal, discount, tax, shipping, total, applied_coupon, removeCoupon } = useCartStore()
    const { isAuthenticated, user } = useAuthStore()
    const { recentCoupon, loading: couponLoading, refetch: refetchCoupon } = useRecentCoupon()

    // Notify backend when cart page loads (triggers churn prediction which may generate coupons)
    useEffect(() => {
        if (isAuthenticated && user?.user_id && items.length > 0) {
            // Prepare cart items for backend
            const cartItems = items.map(item => ({
                product_id: item.product_id,
                name: item.product.name,
                category: item.product.category,
                price: item.product.price,
                quantity: item.quantity
            }))

            // Trigger churn prediction - may generate personalized coupon
            cartApi.notifyCartLoad(cartItems, subtotal)
                .then(() => {
                    // After churn prediction completes, refetch coupons to show any new ones
                    setTimeout(() => refetchCoupon(), 2000) // Wait for coupon generation
                })
                .catch(err => {
                    // Silent fail - this is a background operation
                    console.log('Cart load notification failed:', err.message)
                })
        }
    }, [isAuthenticated, user?.user_id, items.length, subtotal, refetchCoupon])

    if (items.length === 0) {
        return (
            <div className="min-h-[70vh] flex items-center justify-center">
                <div className="text-center max-w-md mx-auto px-4">
                    <div className="w-24 h-24 bg-gradient-to-br from-primary-100 to-primary-200 rounded-full flex items-center justify-center mx-auto mb-6">
                        <ShoppingBag className="w-12 h-12 text-primary-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-3">Your cart is empty</h2>
                    <p className="text-gray-600 mb-8">Looks like you haven't added anything to your cart yet. Start shopping to discover amazing products!</p>
                    <Link
                        to="/products"
                        className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-primary-600 to-primary-700 text-white px-8 py-4 rounded-xl font-semibold hover:from-primary-700 hover:to-primary-800 transition-all duration-300 shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30"
                    >
                        <ShoppingBag className="w-5 h-5" />
                        Start Shopping
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Personalized Coupon Banner - shows when churn prediction generates an offer */}
            {isAuthenticated && !couponLoading && recentCoupon && (
                <div className="mb-6">
                    <RecentCouponDisplay userCouponWithDetails={recentCoupon} />
                </div>
            )}

            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Shopping Cart</h1>
                <p className="text-gray-600 mt-1">{items.length} {items.length === 1 ? 'item' : 'items'} in your cart</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Cart Items */}
                <div className="lg:col-span-2 space-y-4">
                    {items.map((item, index) => (
                        <div
                            key={item.product_id}
                            className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm hover:shadow-md transition-all duration-300"
                            style={{ animationDelay: `${index * 50}ms` }}
                        >
                            <div className="flex gap-5">
                                {/* Product Image */}
                                <Link to={`/products/${item.product_id}`} className="shrink-0">
                                    <div className="w-28 h-28 rounded-xl overflow-hidden bg-gradient-to-br from-gray-100 to-gray-200">
                                        {item.product.images && item.product.images.length > 0 ? (
                                            <img
                                                src={item.product.images[0]}
                                                alt={item.product.name}
                                                className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                                                onError={(e) => {
                                                    const target = e.target as HTMLImageElement
                                                    target.style.display = 'none'
                                                }}
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center">
                                                <ShoppingBag className="w-10 h-10 text-gray-400" />
                                            </div>
                                        )}
                                    </div>
                                </Link>

                                {/* Product Details */}
                                <div className="flex-1 min-w-0">
                                    <Link to={`/products/${item.product_id}`}>
                                        <h3 className="font-semibold text-gray-900 hover:text-primary-600 transition-colors line-clamp-2">
                                            {item.product.name}
                                        </h3>
                                    </Link>
                                    <p className="text-sm text-gray-500 mt-1">{item.product.brand}</p>

                                    <div className="flex items-center gap-4 mt-3">
                                        {/* Quantity Controls */}
                                        <div className="flex items-center bg-gray-100 rounded-lg">
                                            <button
                                                onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                                                className="p-2 hover:bg-gray-200 rounded-l-lg transition-colors"
                                                aria-label="Decrease quantity"
                                            >
                                                <Minus className="w-4 h-4 text-gray-600" />
                                            </button>
                                            <span className="px-4 py-2 font-medium text-gray-900 min-w-[3rem] text-center">
                                                {item.quantity}
                                            </span>
                                            <button
                                                onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                                                className="p-2 hover:bg-gray-200 rounded-r-lg transition-colors"
                                                aria-label="Increase quantity"
                                            >
                                                <Plus className="w-4 h-4 text-gray-600" />
                                            </button>
                                        </div>

                                        {/* Remove Button */}
                                        <button
                                            onClick={() => removeItem(item.product_id)}
                                            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                            aria-label="Remove item"
                                        >
                                            <Trash2 className="w-5 h-5" />
                                        </button>
                                    </div>
                                </div>

                                {/* Price */}
                                <div className="text-right">
                                    <p className="text-xl font-bold text-gray-900">
                                        ${(item.price * item.quantity).toFixed(2)}
                                    </p>
                                    {item.quantity > 1 && (
                                        <p className="text-sm text-gray-500">${item.price.toFixed(2)} each</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Free Shipping Banner */}
                    {subtotal < 50 && (
                        <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
                            <TruckIcon className="w-6 h-6 text-amber-600" />
                            <div className="flex-1">
                                <p className="text-amber-900 font-medium">
                                    Add ${(50 - subtotal).toFixed(2)} more for FREE shipping!
                                </p>
                                <div className="w-full bg-amber-200 rounded-full h-2 mt-2">
                                    <div
                                        className="bg-gradient-to-r from-amber-500 to-orange-500 h-2 rounded-full transition-all duration-500"
                                        style={{ width: `${Math.min((subtotal / 50) * 100, 100)}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Order Summary */}
                <div className="lg:col-span-1">
                    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sticky top-24">
                        <h2 className="text-xl font-bold text-gray-900 mb-6">Order Summary</h2>

                        <div className="space-y-4">
                            <div className="flex justify-between text-gray-600">
                                <span>Subtotal</span>
                                <span className="font-medium text-gray-900">${subtotal.toFixed(2)}</span>
                            </div>

                            {discount > 0 && (
                                <div className="flex justify-between text-green-600">
                                    <span className="flex items-center gap-1">
                                        <Sparkles className="w-4 h-4" />
                                        Discount
                                    </span>
                                    <span className="font-medium">-${discount.toFixed(2)}</span>
                                </div>
                            )}

                            <div className="flex justify-between text-gray-600">
                                <span>Estimated Tax</span>
                                <span className="font-medium text-gray-900">${tax.toFixed(2)}</span>
                            </div>

                            <div className="flex justify-between text-gray-600">
                                <span>Shipping</span>
                                <span className={`font-medium ${shipping === 0 ? 'text-green-600' : 'text-gray-900'}`}>
                                    {shipping === 0 ? 'FREE' : `$${shipping.toFixed(2)}`}
                                </span>
                            </div>

                            <div className="border-t border-gray-200 pt-4">
                                <div className="flex justify-between">
                                    <span className="text-lg font-bold text-gray-900">Total</span>
                                    <span className="text-2xl font-bold text-gray-900">${total.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Applied Coupon */}
                        {applied_coupon && (
                            <div className="mt-4 p-3 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl">
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-green-600" />
                                        <span className="text-sm font-medium text-green-800">
                                            {applied_coupon.code}
                                        </span>
                                    </div>
                                    <button
                                        onClick={removeCoupon}
                                        className="text-sm text-red-600 hover:text-red-800 font-medium"
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Checkout Button */}
                        <Link
                            to="/checkout"
                            className="w-full mt-6 inline-flex items-center justify-center gap-2 bg-gradient-to-r from-primary-600 to-primary-700 text-white px-6 py-4 rounded-xl font-semibold hover:from-primary-700 hover:to-primary-800 transition-all duration-300 shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30"
                        >
                            Proceed to Checkout
                            <ArrowRight className="w-5 h-5" />
                        </Link>

                        <Link
                            to="/products"
                            className="w-full mt-3 inline-flex items-center justify-center gap-2 bg-gray-100 text-gray-700 px-6 py-3 rounded-xl font-medium hover:bg-gray-200 transition-colors"
                        >
                            Continue Shopping
                        </Link>

                        {/* Trust Badges */}
                        <div className="mt-6 pt-6 border-t border-gray-100">
                            <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
                                <span className="flex items-center gap-1">
                                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                                    </svg>
                                    Secure Checkout
                                </span>
                                <span className="flex items-center gap-1">
                                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                    </svg>
                                    Money-back Guarantee
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
