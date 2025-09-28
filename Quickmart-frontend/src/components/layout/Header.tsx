import {
    Gift,
    LogOut,
    Menu,
    Package,
    Search,
    Settings,
    ShoppingCart,
    User,
    X,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCouponNotifications } from '../../hooks/useCouponNotifications'
import { useAuthStore } from '../../stores/authStore'
import { useCartStore } from '../../stores/cartStore'
import { getUserDisplayName } from '../../utils/userUtils'

export default function Header() {
    const navigate = useNavigate()
    const { user, isAuthenticated, logout } = useAuthStore()
    const { items } = useCartStore()
    const { hasNewPersonalizedCoupons, personalizedCouponsCount, markCouponsAsViewed } = useCouponNotifications()
    const [isMenuOpen, setIsMenuOpen] = useState(false)
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')

    const cartItemCount = items.reduce((total, item) => total + item.quantity, 0)

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (searchQuery.trim()) {
            navigate(`/products?search=${encodeURIComponent(searchQuery.trim())}`)
            setSearchQuery('')
        }
    }

    const handleLogout = () => {
        logout()
        setIsUserMenuOpen(false)
        navigate('/')
    }

    return (
        <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <div className="flex items-center">
                        <Link to="/" className="flex items-center space-x-2">
                            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                                <span className="text-white font-bold text-lg">Q</span>
                            </div>
                            <span className="text-xl font-bold text-gray-900">QuickMart</span>
                        </Link>
                    </div>

                    {/* Search Bar - Only show for authenticated users */}
                    {isAuthenticated && (
                        <div className="flex-1 max-w-lg mx-8">
                            <form onSubmit={handleSearch} className="relative">
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                    <input
                                        type="text"
                                        placeholder="Search products..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    />
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Navigation Links - Only show for authenticated users */}
                    {isAuthenticated && (
                        <nav className="hidden md:flex items-center space-x-8">
                            <Link
                                to="/products"
                                className="text-gray-700 hover:text-primary-600 font-medium transition-colors"
                            >
                                Products
                            </Link>
                            <Link
                                to="/coupons"
                                onClick={markCouponsAsViewed}
                                className="relative text-gray-700 hover:text-primary-600 font-medium transition-colors"
                            >
                                Coupons
                                {hasNewPersonalizedCoupons && (
                                    <span className="absolute -top-1 -right-1 bg-purple-500 text-white text-xs rounded-full w-2 h-2 animate-pulse"></span>
                                )}
                                {personalizedCouponsCount > 0 && (
                                    <span className="ml-1 bg-purple-100 text-purple-800 text-xs font-medium px-1.5 py-0.5 rounded-full">
                                        {personalizedCouponsCount}
                                    </span>
                                )}
                            </Link>
                        </nav>
                    )}

                    {/* Right Side Actions */}
                    <div className="flex items-center space-x-4">
                        {/* Cart */}
                        <Link
                            to="/cart"
                            className="relative p-2 text-gray-700 hover:text-primary-600 transition-colors"
                        >
                            <ShoppingCart className="w-6 h-6" />
                            {cartItemCount > 0 && (
                                <span className="absolute -top-1 -right-1 bg-primary-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                                    {cartItemCount}
                                </span>
                            )}
                        </Link>

                        {/* User Menu */}
                        {isAuthenticated ? (
                            <div className="relative">
                                <button
                                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                                    className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
                                >
                                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                                        <User className="w-5 h-5 text-primary-600" />
                                    </div>
                                    <span className="hidden sm:block text-sm font-medium text-gray-700">
                                        {getUserDisplayName(user)}
                                    </span>
                                </button>

                                {/* User Dropdown */}
                                {isUserMenuOpen && (
                                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                                        <Link
                                            to="/profile"
                                            onClick={() => setIsUserMenuOpen(false)}
                                            className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                        >
                                            <Settings className="w-4 h-4" />
                                            <span>Profile</span>
                                        </Link>
                                        <Link
                                            to="/orders"
                                            onClick={() => setIsUserMenuOpen(false)}
                                            className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                        >
                                            <Package className="w-4 h-4" />
                                            <span>Orders</span>
                                        </Link>
                                        <Link
                                            to="/coupons"
                                            onClick={() => {
                                                setIsUserMenuOpen(false)
                                                markCouponsAsViewed()
                                            }}
                                            className="flex items-center justify-between px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                        >
                                            <div className="flex items-center space-x-2">
                                                <Gift className="w-4 h-4" />
                                                <span>Coupons</span>
                                            </div>
                                            <div className="flex items-center space-x-1">
                                                {personalizedCouponsCount > 0 && (
                                                    <span className="bg-purple-100 text-purple-800 text-xs font-medium px-1.5 py-0.5 rounded-full">
                                                        {personalizedCouponsCount}
                                                    </span>
                                                )}
                                                {hasNewPersonalizedCoupons && (
                                                    <span className="bg-purple-500 text-white text-xs rounded-full w-2 h-2 animate-pulse"></span>
                                                )}
                                            </div>
                                        </Link>
                                        <hr className="my-1" />
                                        <button
                                            onClick={handleLogout}
                                            className="flex items-center space-x-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                        >
                                            <LogOut className="w-4 h-4" />
                                            <span>Logout</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="flex items-center space-x-2">
                                <Link
                                    to="/login"
                                    className="text-gray-700 hover:text-primary-600 font-medium transition-colors"
                                >
                                    Login
                                </Link>
                                <Link
                                    to="/register"
                                    className="btn-primary btn-sm"
                                >
                                    Sign Up
                                </Link>
                            </div>
                        )}

                        {/* Mobile Menu Button - Only show for authenticated users */}
                        {isAuthenticated && (
                            <button
                                onClick={() => setIsMenuOpen(!isMenuOpen)}
                                className="md:hidden p-2 text-gray-700 hover:text-primary-600 transition-colors"
                            >
                                {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                            </button>
                        )}
                    </div>
                </div>

                {/* Mobile Menu - Only show for authenticated users */}
                {isMenuOpen && isAuthenticated && (
                    <div className="md:hidden border-t border-gray-200 py-4">
                        <div className="flex flex-col space-y-4">
                            <Link
                                to="/products"
                                onClick={() => setIsMenuOpen(false)}
                                className="text-gray-700 hover:text-primary-600 font-medium transition-colors"
                            >
                                Products
                            </Link>
                            <Link
                                to="/coupons"
                                onClick={() => {
                                    setIsMenuOpen(false)
                                    markCouponsAsViewed()
                                }}
                                className="flex items-center justify-between text-gray-700 hover:text-primary-600 font-medium transition-colors"
                            >
                                <span>Coupons</span>
                                <div className="flex items-center space-x-1">
                                    {personalizedCouponsCount > 0 && (
                                        <span className="bg-purple-100 text-purple-800 text-xs font-medium px-1.5 py-0.5 rounded-full">
                                            {personalizedCouponsCount}
                                        </span>
                                    )}
                                    {hasNewPersonalizedCoupons && (
                                        <span className="bg-purple-500 text-white text-xs rounded-full w-2 h-2 animate-pulse"></span>
                                    )}
                                </div>
                            </Link>
                        </div>
                    </div>
                )}
            </div>
        </header>
    )
}
