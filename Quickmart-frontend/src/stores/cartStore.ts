import toast from 'react-hot-toast'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Cart, CartItem, Coupon, Product } from '../types'

interface CartState extends Cart {
    // Actions
    addItem: (product: Product, quantity?: number) => void
    removeItem: (productId: string) => void
    updateQuantity: (productId: string, quantity: number) => void
    clearCart: () => void
    applyCoupon: (coupon: Coupon) => void
    removeCoupon: () => void
    calculateTotals: () => void
}

const TAX_RATE = 0.08 // 8% tax
const FREE_SHIPPING_THRESHOLD = 50
const SHIPPING_COST = 9.99

export const useCartStore = create<CartState>()(
    persist(
        (set, get) => ({
            items: [],
            subtotal: 0,
            discount: 0,
            tax: 0,
            shipping: 0,
            total: 0,
            applied_coupon: undefined,

            addItem: (product: Product, quantity = 1) => {
                const state = get()
                const existingItem = state.items.find(item => item.product_id === product.product_id)

                if (existingItem) {
                    // Update existing item quantity
                    const newQuantity = existingItem.quantity + quantity
                    if (newQuantity > product.stock_quantity) {
                        toast.error(`Only ${product.stock_quantity} items available`)
                        return
                    }

                    set({
                        items: state.items.map(item =>
                            item.product_id === product.product_id
                                ? {
                                    ...item,
                                    quantity: newQuantity,
                                    total: newQuantity * item.price,
                                }
                                : item
                        ),
                    })
                } else {
                    // Add new item
                    if (quantity > product.stock_quantity) {
                        toast.error(`Only ${product.stock_quantity} items available`)
                        return
                    }

                    const newItem: CartItem = {
                        product_id: product.product_id,
                        product,
                        quantity,
                        price: product.price,
                        total: quantity * product.price,
                    }

                    set({
                        items: [...state.items, newItem],
                    })
                }

                get().calculateTotals()
                toast.success(`${product.name} added to cart`)
            },

            removeItem: (productId: string) => {
                const state = get()
                const item = state.items.find(item => item.product_id === productId)

                set({
                    items: state.items.filter(item => item.product_id !== productId),
                })

                get().calculateTotals()

                if (item) {
                    toast.success(`${item.product.name} removed from cart`)
                }
            },

            updateQuantity: (productId: string, quantity: number) => {
                const state = get()
                const item = state.items.find(item => item.product_id === productId)

                if (!item) return

                if (quantity <= 0) {
                    get().removeItem(productId)
                    return
                }

                if (quantity > item.product.stock_quantity) {
                    toast.error(`Only ${item.product.stock_quantity} items available`)
                    return
                }

                set({
                    items: state.items.map(cartItem =>
                        cartItem.product_id === productId
                            ? {
                                ...cartItem,
                                quantity,
                                total: quantity * cartItem.price,
                            }
                            : cartItem
                    ),
                })

                get().calculateTotals()
            },

            clearCart: () => {
                set({
                    items: [],
                    subtotal: 0,
                    discount: 0,
                    tax: 0,
                    shipping: 0,
                    total: 0,
                    applied_coupon: undefined,
                })
                toast.success('Cart cleared')
            },

            applyCoupon: (coupon: Coupon) => {
                set({ applied_coupon: coupon })
                get().calculateTotals()
                toast.success(`Coupon "${coupon.code}" applied!`)
            },

            removeCoupon: () => {
                const state = get()
                if (state.applied_coupon) {
                    set({ applied_coupon: undefined })
                    get().calculateTotals()
                    toast.success('Coupon removed')
                }
            },

            calculateTotals: () => {
                const state = get()

                // Calculate subtotal
                const subtotal = state.items.reduce((sum, item) => sum + item.total, 0)

                // Calculate discount
                let discount = 0
                if (state.applied_coupon) {
                    const coupon = state.applied_coupon

                    if (subtotal >= coupon.minimum_order_value) {
                        if (coupon.discount_type === 'percentage') {
                            discount = (subtotal * coupon.discount_value) / 100
                            if (coupon.maximum_discount) {
                                discount = Math.min(discount, coupon.maximum_discount)
                            }
                        } else if (coupon.discount_type === 'fixed') {
                            discount = Math.min(coupon.discount_value, subtotal)
                        }
                    }
                }

                // Calculate tax (on subtotal after discount)
                const taxableAmount = subtotal - discount
                const tax = taxableAmount * TAX_RATE

                // Calculate shipping
                let shipping = 0
                if (state.applied_coupon?.discount_type === 'free_shipping') {
                    shipping = 0
                } else if (subtotal < FREE_SHIPPING_THRESHOLD) {
                    shipping = SHIPPING_COST
                }

                // Calculate total
                const total = subtotal - discount + tax + shipping

                set({
                    subtotal,
                    discount,
                    tax,
                    shipping,
                    total,
                })
            },
        }),
        {
            name: 'cart-storage',
            partialize: (state) => ({
                items: state.items,
                applied_coupon: state.applied_coupon,
            }),
        }
    )
)
