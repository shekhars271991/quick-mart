import { useState } from 'react'
import { toast } from 'react-hot-toast'
import type { UserCouponWithDetails } from '../types'

interface RecentCouponDisplayProps {
    userCouponWithDetails: UserCouponWithDetails
}

export default function RecentCouponDisplay({ userCouponWithDetails }: RecentCouponDisplayProps) {
    const { coupon, user_coupon } = userCouponWithDetails
    const [copied, setCopied] = useState(false)

    const isChurnPrevention = user_coupon.source === 'nudge'

    const copyToClipboard = async (code: string) => {
        try {
            await navigator.clipboard.writeText(code)
            setCopied(true)
            toast.success('Coupon code copied!')
            setTimeout(() => setCopied(false), 2000)
        } catch (error) {
            toast.error('Failed to copy coupon code')
        }
    }

    const getDiscountText = () => {
        if (coupon.discount_type === 'percentage') {
            return `${coupon.discount_value}% OFF`
        } else {
            return `$${coupon.discount_value} OFF`
        }
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        })
    }

    return (
        <div className={`relative overflow-hidden rounded-xl border-2 p-6 ${isChurnPrevention
            ? 'border-purple-200 bg-gradient-to-br from-purple-50 via-pink-50 to-purple-100'
            : 'border-green-200 bg-gradient-to-br from-green-50 to-emerald-100'
            }`}>
            {/* Background decoration */}
            <div className="absolute top-0 right-0 -mt-4 -mr-4 h-20 w-20 rounded-full bg-white/20"></div>
            <div className="absolute bottom-0 left-0 -mb-6 -ml-6 h-16 w-16 rounded-full bg-white/10"></div>

            <div className="relative">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <div className="flex items-center gap-2 mb-2">

                            <h3 className={`text-lg font-semibold ${isChurnPrevention ? 'text-purple-900' : 'text-green-900'
                                }`}>
                                Here is a welcome gift for you!
                            </h3>
                        </div>
                        {isChurnPrevention && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-200 text-purple-800">
                                🎯 AI-Personalized Offer
                            </span>
                        )}
                    </div>
                    <div className={`text-3xl font-bold ${isChurnPrevention ? 'text-purple-600' : 'text-green-600'
                        }`}>
                        {getDiscountText()}
                    </div>
                </div>

                {/* Coupon Name and Description */}
                <div className="mb-4">
                    <h4 className={`text-xl font-bold mb-2 ${isChurnPrevention ? 'text-purple-800' : 'text-green-800'
                        }`}>
                        {coupon.name}
                    </h4>
                    {coupon.description && (
                        <p className={`text-sm ${isChurnPrevention ? 'text-purple-700' : 'text-green-700'
                            }`}>
                            {coupon.description}
                        </p>
                    )}
                </div>

                {/* Coupon Code Section */}
                <div className="bg-white/70 backdrop-blur-sm rounded-lg p-4 mb-4 border border-white/50">
                    <div className="flex items-center justify-between">
                        <div className="flex-1">
                            <p className="text-xs text-gray-600 uppercase tracking-wide font-medium mb-1">
                                Coupon Code
                            </p>
                            <p className="text-2xl font-mono font-bold text-gray-900 tracking-wider">
                                {coupon.code}
                            </p>
                        </div>
                        <button
                            onClick={() => copyToClipboard(coupon.code)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${copied
                                ? 'bg-green-100 text-green-700 border border-green-200'
                                : isChurnPrevention
                                    ? 'bg-purple-100 text-purple-700 hover:bg-purple-200 border border-purple-200'
                                    : 'bg-green-100 text-green-700 hover:bg-green-200 border border-green-200'
                                }`}
                        >
                            {copied ? '✓ Copied!' : 'Copy Code'}
                        </button>
                    </div>
                </div>

                {/* Details */}
                <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 text-sm ${isChurnPrevention ? 'text-purple-700' : 'text-green-700'
                    }`}>
                    {coupon.minimum_order_value > 0 && (
                        <div className="flex items-center gap-2">
                            <span className="text-lg">💰</span>
                            <span>Min. order: ${coupon.minimum_order_value}</span>
                        </div>
                    )}
                    {coupon.valid_until && (
                        <div className="flex items-center gap-2">
                            <span className="text-lg">⏰</span>
                            <span>Valid until: {formatDate(coupon.valid_until)}</span>
                        </div>
                    )}
                    <div className="flex items-center gap-2">
                        <span className="text-lg">✨</span>
                        <span>Exclusively for you</span>
                    </div>
                </div>


            </div>
        </div>
    )
}
