import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function HomePage() {
    const { isAuthenticated } = useAuthStore()
    const navigate = useNavigate()

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!isAuthenticated) {
            navigate('/login', { replace: true })
        } else {
            // If authenticated, redirect to products catalog
            navigate('/products', { replace: true })
        }
    }, [isAuthenticated, navigate])

    // Show loading while redirecting
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Redirecting...</p>
            </div>
        </div>
    )
}
