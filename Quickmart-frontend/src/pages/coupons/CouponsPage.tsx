import { useEffect, useState } from 'react'
import { toast } from 'react-hot-toast'
import { couponsApi } from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import type { Coupon, UserCouponWithDetails } from '../../types'

interface CouponCardProps {
    coupon: Coupon | UserCouponWithDetails
    isUserSpecific?: boolean
}

function CouponCard({ coupon, isUserSpecific = false }: CouponCardProps) {
    // Handle both direct Coupon and UserCouponWithDetails
    const actualCoupon = 'coupon' in coupon ? coupon.coupon : coupon
    const userCoupon = 'user_coupon' in coupon ? coupon.user_coupon : null

    const isExpired = actualCoupon.valid_until ? new Date(actualCoupon.valid_until) < new Date() : false
    const isChurnPrevention = userCoupon?.source === 'nudge'

    const copyToClipboard = (code: string) => {
        navigator.clipboard.writeText(code)
        toast.success('Coupon code copied!')
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        })
    }

    const getDiscountText = () => {
        if (actualCoupon.discount_type === 'percentage') {
            return `${actualCoupon.discount_value}% OFF`
        } else {
            return `$${actualCoupon.discount_value} OFF`
        }
    }

    return (
        <div className={`bg-white rounded-lg shadow-md border-2 p-6 transition-all hover:shadow-lg ${isChurnPrevention ? 'border-purple-200 bg-gradient-to-br from-purple-50 to-pink-50' :
            isExpired ? 'border-gray-200 opacity-60' : 'border-green-200'
            }`}>
            {/* Header */}
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900">{actualCoupon.name}</h3>
                    {isChurnPrevention && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 mt-1">
                            🎯 Personalized Offer
                        </span>
                    )}
                </div>
                <div className={`text-2xl font-bold ${isChurnPrevention ? 'text-purple-600' :
                    isExpired ? 'text-gray-400' : 'text-green-600'
                    }`}>
                    {getDiscountText()}
                </div>
            </div>

            {/* Description */}
            {actualCoupon.description && (
                <p className="text-gray-600 text-sm mb-4">{actualCoupon.description}</p>
            )}

            {/* Coupon Code */}
            <div className="bg-gray-50 rounded-lg p-3 mb-4">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Coupon Code</p>
                        <p className="text-lg font-mono font-bold text-gray-900">{actualCoupon.code}</p>
                    </div>
                    <button
                        onClick={() => copyToClipboard(actualCoupon.code)}
                        className="px-3 py-1 bg-blue-100 text-blue-700 rounded-md text-sm font-medium hover:bg-blue-200 transition-colors"
                        disabled={isExpired}
                    >
                        Copy
                    </button>
                </div>
            </div>

            {/* Details */}
            <div className="space-y-2 text-sm text-gray-600">
                {actualCoupon.minimum_order_value > 0 && (
                    <p>• Minimum order: ${actualCoupon.minimum_order_value}</p>
                )}
                {actualCoupon.usage_limit && (
                    <p>• Usage limit: {actualCoupon.usage_limit} time{actualCoupon.usage_limit > 1 ? 's' : ''}</p>
                )}
                {actualCoupon.valid_until && (
                    <p className={isExpired ? 'text-red-500' : ''}>
                        • {isExpired ? 'Expired' : 'Valid until'}: {formatDate(actualCoupon.valid_until)}
                    </p>
                )}
                {isUserSpecific && (
                    <p className="text-purple-600">• Exclusively for you</p>
                )}
            </div>

            {/* Status */}
            <div className="mt-4 pt-4 border-t border-gray-200">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${isExpired ? 'bg-red-100 text-red-800' :
                    isChurnPrevention ? 'bg-purple-100 text-purple-800' :
                        'bg-green-100 text-green-800'
                    }`}>
                    {isExpired ? '❌ Expired' :
                        isChurnPrevention ? '🎁 Special Offer' :
                            '✅ Active'}
                </span>
            </div>
        </div>
    )
}

export default function CouponsPage() {
    const [availableCoupons, setAvailableCoupons] = useState<Coupon[]>([])
    const [userCoupons, setUserCoupons] = useState<UserCouponWithDetails[]>([])
    const [loading, setLoading] = useState(true)
    const { isAuthenticated } = useAuthStore()

    useEffect(() => {
        const fetchCoupons = async () => {
            if (!isAuthenticated) return

            try {
                setLoading(true)

                // Fetch both available and user-specific coupons
                const [available, userSpecific] = await Promise.all([
                    couponsApi.getAvailableCoupons(),
                    couponsApi.getUserCoupons()
                ])

                setAvailableCoupons(available)
                setUserCoupons(userSpecific)
            } catch (error) {
                console.error('Error fetching coupons:', error)
                toast.error('Failed to load coupons')
            } finally {
                setLoading(false)
            }
        }

        fetchCoupons()
    }, [isAuthenticated])

    if (!isAuthenticated) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="text-center py-12">
                    <p className="text-lg text-gray-600">Please log in to view your coupons.</p>
                </div>
            </div>
        )
    }

    if (loading) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="text-lg text-gray-600 mt-4">Loading your coupons...</p>
                </div>
            </div>
        )
    }

    // Separate churn prevention coupons from regular user coupons
    const churnPreventionCoupons = userCoupons.filter(userCouponWithDetails => userCouponWithDetails.user_coupon.source === 'nudge')
    const regularUserCoupons = userCoupons.filter(userCouponWithDetails => userCouponWithDetails.user_coupon.source !== 'nudge')

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">My Coupons</h1>
                <p className="text-gray-600 mt-2">Save money with your personalized offers and available discounts</p>
            </div>

            {/* Personalized Offers (Churn Prevention) */}
            {churnPreventionCoupons.length > 0 && (
                <div className="mb-8">
                    <div className="flex items-center mb-4">
                        <h2 className="text-2xl font-semibold text-purple-900">🎯 Personalized Just for You</h2>
                        <span className="ml-3 bg-purple-100 text-purple-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                            AI-Powered
                        </span>
                    </div>
                    <p className="text-gray-600 mb-6">Special offers created based on your shopping preferences</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {churnPreventionCoupons.map((userCouponWithDetails) => (
                            <CouponCard key={userCouponWithDetails.user_coupon.user_coupon_id} coupon={userCouponWithDetails} isUserSpecific={true} />
                        ))}
                    </div>
                </div>
            )}

            {/* Your Exclusive Coupons */}
            {regularUserCoupons.length > 0 && (
                <div className="mb-8">
                    <h2 className="text-2xl font-semibold text-gray-900 mb-4">🎁 Your Exclusive Coupons</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {regularUserCoupons.map((userCouponWithDetails) => (
                            <CouponCard key={userCouponWithDetails.user_coupon.user_coupon_id} coupon={userCouponWithDetails} isUserSpecific={true} />
                        ))}
                    </div>
                </div>
            )}

            {/* Available for Everyone */}
            {availableCoupons.length > 0 && (
                <div className="mb-8">
                    <h2 className="text-2xl font-semibold text-gray-900 mb-4">🏪 Available for Everyone</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {availableCoupons.map((coupon) => (
                            <CouponCard key={coupon.code} coupon={coupon} />
                        ))}
                    </div>
                </div>
            )}

            {/* Empty State */}
            {availableCoupons.length === 0 && userCoupons.length === 0 && (
                <div className="text-center py-12">
                    <div className="text-6xl mb-4">🎫</div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">No coupons available</h3>
                    <p className="text-gray-600 mb-6">Check back later for new offers and discounts!</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Refresh
                    </button>
                </div>
            )}

            {/* Help Text */}
            <div className="mt-12 bg-blue-50 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-blue-900 mb-2">💡 How to use your coupons</h3>
                <ul className="text-blue-800 space-y-1 text-sm">
                    <li>• Copy the coupon code by clicking the "Copy" button</li>
                    <li>• Add items to your cart and proceed to checkout</li>
                    <li>• Paste the coupon code in the discount field</li>
                    <li>• Enjoy your savings!</li>
                </ul>
            </div>
        </div>
    )
}
