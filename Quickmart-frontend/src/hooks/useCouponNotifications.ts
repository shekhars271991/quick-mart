import { useEffect, useState } from 'react'
import { couponsApi } from '../lib/api'
import { useAuthStore } from '../stores/authStore'

export function useCouponNotifications() {
    const [hasNewPersonalizedCoupons, setHasNewPersonalizedCoupons] = useState(false)
    const [personalizedCouponsCount, setPersonalizedCouponsCount] = useState(0)
    const { isAuthenticated, user } = useAuthStore()

    useEffect(() => {
        const checkForNewCoupons = async () => {
            if (!isAuthenticated || !user) return

            try {
                const userCoupons = await couponsApi.getUserCoupons()
                const churnPreventionCoupons = userCoupons.filter(
                    userCouponWithDetails => userCouponWithDetails.user_coupon.source === 'nudge' &&
                        userCouponWithDetails.coupon.is_active &&
                        (!userCouponWithDetails.coupon.valid_until || new Date(userCouponWithDetails.coupon.valid_until) > new Date())
                )

                setPersonalizedCouponsCount(churnPreventionCoupons.length)

                // Check if there are new coupons (created in the last 24 hours)
                const now = new Date()
                const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)

                const newCoupons = churnPreventionCoupons.filter(userCouponWithDetails => {
                    const assignedAt = new Date(userCouponWithDetails.user_coupon.assigned_at)
                    return assignedAt > oneDayAgo
                })

                setHasNewPersonalizedCoupons(newCoupons.length > 0)
            } catch (error) {
                console.error('Error checking coupon notifications:', error)
            }
        }

        checkForNewCoupons()

        // Check every 5 minutes for new coupons
        const interval = setInterval(checkForNewCoupons, 5 * 60 * 1000)

        return () => clearInterval(interval)
    }, [isAuthenticated, user])

    const markCouponsAsViewed = () => {
        setHasNewPersonalizedCoupons(false)
    }

    return {
        hasNewPersonalizedCoupons,
        personalizedCouponsCount,
        markCouponsAsViewed
    }
}
