/**
 * Debug utilities for authentication issues
 */

export function debugAuthState() {
    console.log('=== AUTH DEBUG INFO ===')

    // Check localStorage contents
    const token = localStorage.getItem('access_token')
    const userStr = localStorage.getItem('user')

    console.log('🔑 Token exists:', !!token)
    console.log('👤 User data exists:', !!userStr)

    if (userStr) {
        try {
            const user = JSON.parse(userStr)
            console.log('📋 User object structure:', user)
            console.log('📋 User keys:', Object.keys(user))

            // Check for different possible name sources
            console.log('🏷️  Name sources:')
            console.log('  - user.profile?.name:', user.profile?.name)
            console.log('  - user.name:', user.name)
            console.log('  - user.email:', user.email)
            console.log('  - user._id:', user._id)
            console.log('  - user.user_id:', user.user_id)

        } catch (e) {
            console.error('❌ Error parsing user data:', e)
        }
    }

    // Check all localStorage keys
    console.log('🗄️  All localStorage keys:', Object.keys(localStorage))

    // Check for any auth-related keys
    const authKeys = Object.keys(localStorage).filter(key =>
        key.includes('auth') || key.includes('user') || key.includes('token')
    )
    console.log('🔐 Auth-related localStorage keys:', authKeys)

    console.log('=== END DEBUG INFO ===')
}

// Helper to clear all auth data
export function clearAllAuthData() {
    console.log('🧹 Clearing all auth data...')

    // Clear known auth keys
    const authKeys = [
        'access_token',
        'user',
        'auth-storage',
        'token',
        'authToken',
        'user_token'
    ]

    authKeys.forEach(key => {
        if (localStorage.getItem(key)) {
            console.log(`  Removing: ${key}`)
            localStorage.removeItem(key)
        }
    })

    // Clear any Firebase or other third-party auth
    const allKeys = Object.keys(localStorage)
    const thirdPartyKeys = allKeys.filter(key =>
        key.includes('firebase') ||
        key.includes('google') ||
        key.includes('auth0') ||
        key.includes('clerk')
    )

    thirdPartyKeys.forEach(key => {
        console.log(`  Removing third-party: ${key}`)
        localStorage.removeItem(key)
    })

    console.log('✅ Auth data cleared')
}

// Add to window for easy debugging
if (typeof window !== 'undefined') {
    (window as any).debugAuth = debugAuthState;
    (window as any).clearAuth = clearAllAuthData;
}
