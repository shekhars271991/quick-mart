import { Minus, Plus, ShoppingBag, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useCartStore } from '../../stores/cartStore'

export default function CartPage() {
    const { items, updateQuantity, removeItem, subtotal, discount, tax, shipping, total, applied_coupon, removeCoupon } = useCartStore()

    if (items.length === 0) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="text-center py-12">
                    <ShoppingBag className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h2 className="text-2xl font-semibold text-gray-900 mb-2">Your cart is empty</h2>
                    <p className="text-gray-600 mb-6">Start shopping to add items to your cart</p>
                    <Link to="/products" className="btn-primary btn-lg">
                        Continue Shopping
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">Shopping Cart</h1>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Cart Items */}
                <div className="lg:col-span-2 space-y-4">
                    {items.map((item) => (
                        <div key={item.product_id} className="card p-4">
                            <div className="flex items-center space-x-4">
                                <div className="w-20 h-20 bg-gray-100 rounded-lg flex items-center justify-center">
                                    <ShoppingBag className="w-8 h-8 text-gray-400" />
                                </div>

                                <div className="flex-1">
                                    <h3 className="font-semibold text-gray-900">{item.product.name}</h3>
                                    <p className="text-sm text-gray-600">{item.product.brand}</p>
                                    <p className="text-lg font-bold text-gray-900">${item.price.toFixed(2)}</p>
                                </div>

                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                                        className="p-1 hover:bg-gray-100 rounded"
                                    >
                                        <Minus className="w-4 h-4" />
                                    </button>
                                    <span className="px-3 py-1 border border-gray-300 rounded">{item.quantity}</span>
                                    <button
                                        onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                                        className="p-1 hover:bg-gray-100 rounded"
                                    >
                                        <Plus className="w-4 h-4" />
                                    </button>
                                </div>

                                <button
                                    onClick={() => removeItem(item.product_id)}
                                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                                >
                                    <Trash2 className="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Order Summary */}
                <div className="card p-6">
                    <h2 className="text-xl font-semibold text-gray-900 mb-4">Order Summary</h2>

                    <div className="space-y-3">
                        <div className="flex justify-between">
                            <span className="text-gray-600">Subtotal</span>
                            <span className="font-medium">${subtotal.toFixed(2)}</span>
                        </div>

                        {discount > 0 && (
                            <div className="flex justify-between text-green-600">
                                <span>Discount</span>
                                <span>-${discount.toFixed(2)}</span>
                            </div>
                        )}

                        <div className="flex justify-between">
                            <span className="text-gray-600">Tax</span>
                            <span className="font-medium">${tax.toFixed(2)}</span>
                        </div>

                        <div className="flex justify-between">
                            <span className="text-gray-600">Shipping</span>
                            <span className="font-medium">
                                {shipping === 0 ? 'Free' : `$${shipping.toFixed(2)}`}
                            </span>
                        </div>

                        <hr />

                        <div className="flex justify-between text-lg font-bold">
                            <span>Total</span>
                            <span>${total.toFixed(2)}</span>
                        </div>
                    </div>

                    {applied_coupon && (
                        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-green-800">
                                    Coupon: {applied_coupon.code}
                                </span>
                                <button
                                    onClick={removeCoupon}
                                    className="text-sm text-red-600 hover:text-red-800"
                                >
                                    Remove
                                </button>
                            </div>
                        </div>
                    )}

                    <Link
                        to="/checkout"
                        className="w-full btn-primary btn-lg mt-6"
                    >
                        Proceed to Checkout
                    </Link>

                    <Link
                        to="/products"
                        className="w-full btn-outline btn-md mt-3"
                    >
                        Continue Shopping
                    </Link>
                </div>
            </div>
        </div>
    )
}
