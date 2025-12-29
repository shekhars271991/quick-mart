import { Copy, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'react-hot-toast'
import type { UserCouponWithDetails } from '../types'

interface RecentCouponDisplayProps {
    userCouponWithDetails: UserCouponWithDetails
}

export default function RecentCouponDisplay({ userCouponWithDetails }: RecentCouponDisplayProps) {
    const { coupon } = userCouponWithDetails
    const [copied, setCopied] = useState(false)
    const [dismissed, setDismissed] = useState(false)

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
            return `${coupon.discount_value}% off`
        } else {
            return `$${coupon.discount_value} off`
        }
    }

    if (dismissed) return null

    return (
        <div className="flex items-center justify-between gap-6 bg-gradient-to-r from-slate-800 to-slate-900 rounded-xl px-5 py-4">
            <div className="flex items-center gap-4">
                <div className="hidden sm:flex items-center justify-center w-10 h-10 bg-amber-500/20 rounded-full">
                    <span className="text-lg">🎁</span>
                </div>
                <div>
                    <p className="text-white text-sm">
                        You have a special offer! Get <span className="text-amber-400">{getDiscountText()}</span> your order
                    </p>
                    <p className="text-slate-400 text-xs mt-0.5">
                        Use code <span className="text-slate-200 font-mono">{coupon.code}</span> at checkout
                    </p>
                </div>
            </div>
            <div className="flex items-center gap-2">
                <button
                    onClick={() => copyToClipboard(coupon.code)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all ${
                        copied
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-white/10 text-white hover:bg-white/20'
                    }`}
                >
                    <Copy className="w-3.5 h-3.5" />
                    {copied ? 'Copied!' : 'Copy code'}
                </button>
                <button
                    onClick={() => setDismissed(true)}
                    className="p-1.5 text-slate-500 hover:text-slate-300 rounded-lg hover:bg-white/10 transition-colors"
                    aria-label="Dismiss"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>
        </div>
    )
}
