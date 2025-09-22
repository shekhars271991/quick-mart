import type { User } from '../types'

/**
 * Safely get the display name for a user from various possible sources
 */
export function getUserDisplayName(user: User | null | undefined): string {
    if (!user) return 'User'

    // Try different sources for the name
    if (user.profile?.name) return user.profile.name
    if ((user as any).name) return (user as any).name
    if (user.email) return user.email.split('@')[0]

    return 'User'
}

/**
 * Get user ID from various possible sources
 */
export function getUserId(user: User | null | undefined): string | null {
    if (!user) return null

    if (user.user_id) return user.user_id
    if ((user as any)._id) return (user as any)._id

    return null
}
