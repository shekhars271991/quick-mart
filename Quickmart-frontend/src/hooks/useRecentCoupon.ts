import { useEffect, useState } from 'react'
import { couponsApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import type { UserCouponWithDetails } from '../types'

export function useRecentCoupon() {
    const [recentCoupon, setRecentCoupon] = useState<UserCouponWithDetails | null>(null)
    const [loading, setLoading] = useState(true)
    const { isAuthenticated, user } = useAuthStore()

    useEffect(() => {
        const fetchRecentCoupon = async () => {
            if (!isAuthenticated || !user) {
                setRecentCoupon(null)
                setLoading(false)
                return
            }

            try {
                setLoading(true)
                const userCoupons = await couponsApi.getUserCoupons()

                // Filter for active coupons (not expired, not used)
                const activeCoupons = userCoupons.filter(userCouponWithDetails => {
                    const coupon = userCouponWithDetails.coupon
                    const userCoupon = userCouponWithDetails.user_coupon

                    return (
                        userCoupon.status === 'available' &&
                        coupon.is_active &&
                        (!coupon.valid_until || new Date(coupon.valid_until) > new Date())
                    )
                })

                if (activeCoupons.length > 0) {
                    // Sort by assigned date (most recent first)
                    activeCoupons.sort((a, b) =>
                        new Date(b.user_coupon.assigned_at).getTime() - new Date(a.user_coupon.assigned_at).getTime()
                    )

                    // Get the most recent coupon
                    setRecentCoupon(activeCoupons[0])
                } else {
                    setRecentCoupon(null)
                }
            } catch (error) {
                console.error('Error fetching recent coupon:', error)
                setRecentCoupon(null)
            } finally {
                setLoading(false)
            }
        }

        fetchRecentCoupon()
    }, [isAuthenticated, user])

    return {
        recentCoupon,
        loading,
        hasRecentCoupon: !!recentCoupon
    }
}
