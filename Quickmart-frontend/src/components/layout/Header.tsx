import {
    Gift,
    LogOut,
    Menu,
    Package,
    Search,
    Settings,
    ShoppingCart,
    Sparkles,
    User,
    X,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCouponNotifications } from '../../hooks/useCouponNotifications'
import { useAuthStore } from '../../stores/authStore'
import { useCartStore } from '../../stores/cartStore'
import { getUserDisplayName } from '../../utils/userUtils'
import NotificationsDropdown from './NotificationsDropdown'

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

    const handleLogout = async () => {
        await logout()
        setIsUserMenuOpen(false)
        navigate('/')
    }

    return (
        <header className="bg-white/80 backdrop-blur-lg border-b border-gray-200/50 sticky top-0 z-50 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <div className="flex items-center">
                        <Link to="/" className="flex items-center space-x-3 group">
                            <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-primary-700 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25 group-hover:shadow-xl group-hover:shadow-primary-500/30 transition-all duration-300">
                                <span className="text-white font-bold text-xl">Q</span>
                            </div>
                            <span className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                                QuickMart
                            </span>
                        </Link>
                    </div>

                    {/* Search Bar - Only show for authenticated users */}
                    {isAuthenticated && (
                        <div className="flex-1 max-w-xl mx-8 hidden md:block">
                            <form onSubmit={handleSearch} className="relative">
                                <div className="relative">
                                    <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                    <input
                                        type="text"
                                        placeholder="Search for products, brands, and more..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full pl-12 pr-4 py-2.5 bg-gray-100 border-0 rounded-xl focus:ring-2 focus:ring-primary-500 focus:bg-white transition-all duration-200 text-sm"
                                    />
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Navigation Links - Only show for authenticated users */}
                    {isAuthenticated && (
                        <nav className="hidden lg:flex items-center space-x-1">
                            <Link
                                to="/products"
                                className="px-4 py-2 text-gray-700 hover:text-primary-600 font-medium transition-colors rounded-lg hover:bg-gray-100"
                            >
                                Products
                            </Link>
                            <Link
                                to="/coupons"
                                onClick={markCouponsAsViewed}
                                className="relative px-4 py-2 text-gray-700 hover:text-primary-600 font-medium transition-colors rounded-lg hover:bg-gray-100 flex items-center gap-2"
                            >
                                <Gift className="w-4 h-4" />
                                Coupons
                                {hasNewPersonalizedCoupons && (
                                    <span className="absolute top-1 right-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs rounded-full w-2 h-2 animate-pulse"></span>
                                )}
                                {personalizedCouponsCount > 0 && (
                                    <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-medium px-2 py-0.5 rounded-full">
                                        {personalizedCouponsCount}
                                    </span>
                                )}
                            </Link>
                        </nav>
                    )}

                    {/* Right Side Actions */}
                    <div className="flex items-center space-x-2">
                        {/* Notifications - Only show for authenticated users */}
                        {isAuthenticated && <NotificationsDropdown />}

                        {/* Cart */}
                        <Link
                            to="/cart"
                            className="relative p-2.5 text-gray-700 hover:text-primary-600 hover:bg-gray-100 rounded-xl transition-all duration-200"
                        >
                            <ShoppingCart className="w-6 h-6" />
                            {cartItemCount > 0 && (
                                <span className="absolute -top-0.5 -right-0.5 bg-gradient-to-r from-primary-600 to-primary-700 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shadow-lg animate-scale-in">
                                    {cartItemCount > 9 ? '9+' : cartItemCount}
                                </span>
                            )}
                        </Link>

                        {/* User Menu */}
                        {isAuthenticated ? (
                            <div className="relative">
                                <button
                                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                                    className="flex items-center space-x-2 p-2 rounded-xl hover:bg-gray-100 transition-all duration-200"
                                >
                                    <div className="w-9 h-9 bg-gradient-to-br from-primary-100 to-primary-200 rounded-xl flex items-center justify-center">
                                        <User className="w-5 h-5 text-primary-700" />
                                    </div>
                                    <span className="hidden sm:block text-sm font-medium text-gray-700 max-w-[100px] truncate">
                                        {getUserDisplayName(user)}
                                    </span>
                                </button>

                                {/* User Dropdown */}
                                {isUserMenuOpen && (
                                    <>
                                        <div 
                                            className="fixed inset-0 z-40" 
                                            onClick={() => setIsUserMenuOpen(false)}
                                        />
                                        <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-xl border border-gray-100 py-2 z-50 animate-scale-in">
                                            <div className="px-4 py-3 border-b border-gray-100">
                                                <p className="text-sm font-semibold text-gray-900">{getUserDisplayName(user)}</p>
                                                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                                            </div>
                                            <div className="py-1">
                                                <Link
                                                    to="/profile"
                                                    onClick={() => setIsUserMenuOpen(false)}
                                                    className="flex items-center space-x-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                                                >
                                                    <Settings className="w-4 h-4 text-gray-400" />
                                                    <span>Profile Settings</span>
                                                </Link>
                                                <Link
                                                    to="/orders"
                                                    onClick={() => setIsUserMenuOpen(false)}
                                                    className="flex items-center space-x-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                                                >
                                                    <Package className="w-4 h-4 text-gray-400" />
                                                    <span>My Orders</span>
                                                </Link>
                                                <Link
                                                    to="/coupons"
                                                    onClick={() => {
                                                        setIsUserMenuOpen(false)
                                                        markCouponsAsViewed()
                                                    }}
                                                    className="flex items-center justify-between px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                                                >
                                                    <div className="flex items-center space-x-3">
                                                        <Sparkles className="w-4 h-4 text-gray-400" />
                                                        <span>My Coupons</span>
                                                    </div>
                                                    {personalizedCouponsCount > 0 && (
                                                        <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-medium px-2 py-0.5 rounded-full">
                                                            {personalizedCouponsCount}
                                                        </span>
                                                    )}
                                                </Link>
                                            </div>
                                            <div className="border-t border-gray-100 py-1">
                                                <button
                                                    onClick={handleLogout}
                                                    className="flex items-center space-x-3 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50"
                                                >
                                                    <LogOut className="w-4 h-4" />
                                                    <span>Sign Out</span>
                                                </button>
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>
                        ) : (
                            <div className="flex items-center space-x-2">
                                <Link
                                    to="/login"
                                    className="px-4 py-2 text-gray-700 hover:text-primary-600 font-medium transition-colors"
                                >
                                    Sign In
                                </Link>
                                <Link
                                    to="/register"
                                    className="px-5 py-2.5 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-xl font-medium hover:from-primary-700 hover:to-primary-800 transition-all duration-300 shadow-lg shadow-primary-500/25"
                                >
                                    Get Started
                                </Link>
                            </div>
                        )}

                        {/* Mobile Menu Button - Only show for authenticated users */}
                        {isAuthenticated && (
                            <button
                                onClick={() => setIsMenuOpen(!isMenuOpen)}
                                className="lg:hidden p-2.5 text-gray-700 hover:text-primary-600 hover:bg-gray-100 rounded-xl transition-all duration-200"
                            >
                                {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                            </button>
                        )}
                    </div>
                </div>

                {/* Mobile Menu - Only show for authenticated users */}
                {isMenuOpen && isAuthenticated && (
                    <div className="lg:hidden border-t border-gray-100 py-4 animate-slide-down">
                        {/* Mobile Search */}
                        <form onSubmit={handleSearch} className="mb-4">
                            <div className="relative">
                                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                <input
                                    type="text"
                                    placeholder="Search products..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pl-12 pr-4 py-3 bg-gray-100 border-0 rounded-xl focus:ring-2 focus:ring-primary-500"
                                />
                            </div>
                        </form>
                        
                        <div className="flex flex-col space-y-1">
                            <Link
                                to="/products"
                                onClick={() => setIsMenuOpen(false)}
                                className="px-4 py-3 text-gray-700 hover:text-primary-600 hover:bg-gray-50 font-medium transition-colors rounded-xl"
                            >
                                Products
                            </Link>
                            <Link
                                to="/coupons"
                                onClick={() => {
                                    setIsMenuOpen(false)
                                    markCouponsAsViewed()
                                }}
                                className="flex items-center justify-between px-4 py-3 text-gray-700 hover:text-primary-600 hover:bg-gray-50 font-medium transition-colors rounded-xl"
                            >
                                <span className="flex items-center gap-2">
                                    <Gift className="w-4 h-4" />
                                    Coupons
                                </span>
                                {personalizedCouponsCount > 0 && (
                                    <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-medium px-2 py-0.5 rounded-full">
                                        {personalizedCouponsCount}
                                    </span>
                                )}
                            </Link>
                        </div>
                    </div>
                )}
            </div>
        </header>
    )
}
