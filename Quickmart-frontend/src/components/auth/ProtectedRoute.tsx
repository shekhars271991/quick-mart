import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

export default function ProtectedRoute() {
    const { isAuthenticated } = useAuthStore()
    const location = useLocation()

    if (!isAuthenticated) {
        // Redirect to login page with return url
        return <Navigate to="/login" state={{ from: location }} replace />
    }

    return <Outlet />
}
