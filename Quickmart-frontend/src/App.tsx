import { useEffect } from 'react'
import { Route, Routes } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import './utils/debugAuth'; // Import debug utilities

// Layout Components
import ProtectedRoute from './components/auth/ProtectedRoute'
import Layout from './components/layout/Layout'

// Pages
import HomePage from './pages/HomePage'
import NotFoundPage from './pages/NotFoundPage'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import CartPage from './pages/cart/CartPage'
import CheckoutPage from './pages/checkout/CheckoutPage'
import CouponsPage from './pages/coupons/CouponsPage'
import OrdersPage from './pages/orders/OrdersPage'
import ProductDetailPage from './pages/products/ProductDetailPage'
import ProductsPage from './pages/products/ProductsPage'
import ProfilePage from './pages/profile/ProfilePage'

function App() {
    const { initializeAuth } = useAuthStore()

    useEffect(() => {
        // Initialize auth state from localStorage on app start
        initializeAuth()
    }, [initializeAuth])

    return (
        <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Layout />}>
                <Route index element={<HomePage />} />
                <Route path="login" element={<LoginPage />} />
                <Route path="register" element={<RegisterPage />} />
                <Route path="products" element={<ProductsPage />} />
                <Route path="products/:id" element={<ProductDetailPage />} />

                {/* Protected Routes */}
                <Route element={<ProtectedRoute />}>
                    <Route path="cart" element={<CartPage />} />
                    <Route path="checkout" element={<CheckoutPage />} />
                    <Route path="profile" element={<ProfilePage />} />
                    <Route path="coupons" element={<CouponsPage />} />
                    <Route path="orders" element={<OrdersPage />} />
                </Route>

                {/* 404 Page */}
                <Route path="*" element={<NotFoundPage />} />
            </Route>
        </Routes>
    )
}

export default App
