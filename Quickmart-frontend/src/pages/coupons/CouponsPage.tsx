import { Check, Clock, Copy, Gift, Sparkles, Tag, Ticket } from 'lucide-react'
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
    const [copied, setCopied] = useState(false)
    
    // Handle both direct Coupon and UserCouponWithDetails
    const actualCoupon = 'coupon' in coupon ? coupon.coupon : coupon
    const userCoupon = 'user_coupon' in coupon ? coupon.user_coupon : null

    const isExpired = actualCoupon.valid_until ? new Date(actualCoupon.valid_until) < new Date() : false
    const isChurnPrevention = userCoupon?.source === 'nudge'

    const copyToClipboard = (code: string) => {
        navigator.clipboard.writeText(code)
        setCopied(true)
        toast.success('Coupon code copied!')
        setTimeout(() => setCopied(false), 2000)
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
            return `${actualCoupon.discount_value}%`
        } else {
            return `$${actualCoupon.discount_value}`
        }
    }

    const daysUntilExpiry = () => {
        if (!actualCoupon.valid_until) return null
        const expiry = new Date(actualCoupon.valid_until)
        const now = new Date()
        const diff = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
        return diff
    }

    const days = daysUntilExpiry()

    return (
        <div className={`relative overflow-hidden bg-white rounded-2xl border-2 transition-all duration-300 hover:shadow-lg ${
            isChurnPrevention 
                ? 'border-purple-200 hover:border-purple-300' 
                : isExpired 
                    ? 'border-gray-200 opacity-60' 
                    : 'border-green-200 hover:border-green-300'
        }`}>
            {/* Top Banner */}
            <div className={`px-5 py-3 ${
                isChurnPrevention 
                    ? 'bg-gradient-to-r from-purple-500 to-pink-500' 
                    : isExpired 
                        ? 'bg-gray-400' 
                        : 'bg-gradient-to-r from-green-500 to-emerald-500'
            }`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-white">
                        {isChurnPrevention ? (
                            <>
                                <Sparkles className="w-4 h-4" />
                                <span className="text-sm font-medium">Personalized Offer</span>
                            </>
                        ) : (
                            <>
                                <Tag className="w-4 h-4" />
                                <span className="text-sm font-medium">
                                    {isExpired ? 'Expired' : 'Available'}
                                </span>
                            </>
                        )}
                    </div>
                    <span className="text-3xl font-bold text-white">
                        {getDiscountText()}
                        <span className="text-lg font-normal ml-1">OFF</span>
                    </span>
                </div>
            </div>

            <div className="p-5">
                {/* Title */}
                <h3 className="text-lg font-bold text-gray-900 mb-2">{actualCoupon.name}</h3>
                
                {/* Description */}
                {actualCoupon.description && (
                    <p className="text-gray-600 text-sm mb-4 line-clamp-2">{actualCoupon.description}</p>
                )}

                {/* Coupon Code */}
                <div className="bg-gray-50 rounded-xl p-4 mb-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Coupon Code</p>
                            <p className="text-xl font-mono font-bold text-gray-900 tracking-wider">{actualCoupon.code}</p>
                        </div>
                        <button
                            onClick={() => copyToClipboard(actualCoupon.code)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-all duration-200 ${
                                copied 
                                    ? 'bg-green-100 text-green-700' 
                                    : isExpired 
                                        ? 'bg-gray-200 text-gray-500 cursor-not-allowed' 
                                        : 'bg-primary-100 text-primary-700 hover:bg-primary-200'
                            }`}
                            disabled={isExpired}
                        >
                            {copied ? (
                                <>
                                    <Check className="w-4 h-4" />
                                    Copied!
                                </>
                            ) : (
                                <>
                                    <Copy className="w-4 h-4" />
                                    Copy
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Details */}
                <div className="space-y-2 text-sm">
                    {actualCoupon.minimum_order_value > 0 && (
                        <div className="flex items-center gap-2 text-gray-600">
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full" />
                            Min. order: ${actualCoupon.minimum_order_value}
                        </div>
                    )}
                    {actualCoupon.maximum_discount && (
                        <div className="flex items-center gap-2 text-gray-600">
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full" />
                            Max. discount: ${actualCoupon.maximum_discount}
                        </div>
                    )}
                    {isUserSpecific && (
                        <div className="flex items-center gap-2 text-purple-600">
                            <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" />
                            Exclusively for you
                        </div>
                    )}
                </div>

                {/* Expiry */}
                {actualCoupon.valid_until && (
                    <div className={`mt-4 pt-4 border-t border-gray-100 flex items-center gap-2 text-sm ${
                        isExpired ? 'text-red-500' : days && days <= 3 ? 'text-amber-600' : 'text-gray-500'
                    }`}>
                        <Clock className="w-4 h-4" />
                        {isExpired ? (
                            <span>Expired on {formatDate(actualCoupon.valid_until)}</span>
                        ) : days && days <= 3 ? (
                            <span className="font-medium">Expires in {days} day{days === 1 ? '' : 's'}!</span>
                        ) : (
                            <span>Valid until {formatDate(actualCoupon.valid_until)}</span>
                        )}
                    </div>
                )}
            </div>

            {/* Decorative elements */}
            <div className="absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-gray-50 rounded-full" />
            <div className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-gray-50 rounded-full" />
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
            <div className="min-h-[60vh] flex items-center justify-center">
                <div className="text-center max-w-md mx-auto px-4">
                    <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Ticket className="w-10 h-10 text-gray-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-3">Sign in to view coupons</h2>
                    <p className="text-gray-600">Log in to your account to see your personalized offers and available discounts.</p>
                </div>
            </div>
        )
    }

    if (loading) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="animate-pulse space-y-8">
                    <div className="h-10 bg-gray-200 rounded-xl w-1/3" />
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="bg-white rounded-2xl overflow-hidden">
                                <div className="h-16 bg-gray-200" />
                                <div className="p-5 space-y-4">
                                    <div className="h-5 bg-gray-200 rounded-full w-2/3" />
                                    <div className="h-4 bg-gray-200 rounded-full" />
                                    <div className="h-16 bg-gray-100 rounded-xl" />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    // Separate churn prevention coupons from regular user coupons
    const churnPreventionCoupons = userCoupons.filter(uc => uc.user_coupon.source === 'nudge')
    const regularUserCoupons = userCoupons.filter(uc => uc.user_coupon.source !== 'nudge')

    const hasCoupons = availableCoupons.length > 0 || userCoupons.length > 0

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="mb-10">
                <div className="flex items-center gap-3 mb-3">
                    <div className="p-2.5 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl">
                        <Gift className="w-6 h-6 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold text-gray-900">My Coupons</h1>
                </div>
                <p className="text-gray-600 text-lg">
                    Save money with your personalized offers and available discounts
                </p>
            </div>

            {/* Personalized Offers (Churn Prevention) */}
            {churnPreventionCoupons.length > 0 && (
                <div className="mb-12">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Personalized Just for You</h2>
                            <p className="text-gray-600 text-sm">AI-powered offers based on your shopping preferences</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {churnPreventionCoupons.map((userCouponWithDetails) => (
                            <CouponCard 
                                key={userCouponWithDetails.user_coupon.user_coupon_id} 
                                coupon={userCouponWithDetails} 
                                isUserSpecific={true} 
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Your Exclusive Coupons */}
            {regularUserCoupons.length > 0 && (
                <div className="mb-12">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-gradient-to-br from-green-500 to-emerald-500 rounded-xl">
                            <Ticket className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Your Exclusive Coupons</h2>
                            <p className="text-gray-600 text-sm">Special discounts assigned to your account</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {regularUserCoupons.map((userCouponWithDetails) => (
                            <CouponCard 
                                key={userCouponWithDetails.user_coupon.user_coupon_id} 
                                coupon={userCouponWithDetails} 
                                isUserSpecific={true} 
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Empty State */}
            {!hasCoupons && (
                <div className="text-center py-16">
                    <div className="w-24 h-24 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Ticket className="w-12 h-12 text-gray-400" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">No coupons available</h3>
                    <p className="text-gray-600 mb-8 max-w-md mx-auto">
                        Keep shopping to unlock personalized offers and exclusive discounts!
                    </p>
                    <button
                        onClick={() => window.location.reload()}
                        className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition-colors"
                    >
                        Refresh
                    </button>
                </div>
            )}
        </div>
    )
}
