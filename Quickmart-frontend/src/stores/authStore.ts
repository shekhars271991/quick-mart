import toast from 'react-hot-toast'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi } from '../lib/api'
import type { AuthResponse, LoginCredentials, RegisterData, User } from '../types'

interface AuthState {
    user: User | null
    token: string | null
    isAuthenticated: boolean
    isLoading: boolean

    // Actions
    login: (credentials: LoginCredentials) => Promise<boolean>
    register: (data: RegisterData) => Promise<boolean>
    logout: () => void
    updateProfile: (data: Partial<User>) => Promise<boolean>
    initializeAuth: () => void
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, _get) => ({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,

            login: async (credentials: LoginCredentials) => {
                set({ isLoading: true })
                try {
                    const response: AuthResponse = await authApi.login(credentials)

                    // Store token and user data
                    localStorage.setItem('access_token', response.access_token)

                    set({
                        user: response.user,
                        token: response.access_token,
                        isAuthenticated: true,
                        isLoading: false,
                    })

                    toast.success(`Welcome back, ${response.user.profile.name}!`)
                    return true
                } catch (error: unknown) {
                    set({ isLoading: false })

                    // Handle different error types
                    const errorObj = error as { response?: { data?: { detail?: string | object[] } } }
                    let message = 'Login failed'

                    if (errorObj.response?.data?.detail) {
                        const detail = errorObj.response.data.detail
                        if (typeof detail === 'string') {
                            message = detail
                        } else if (Array.isArray(detail) && detail.length > 0) {
                            // Handle validation errors array
                            const firstError = detail[0] as { msg?: string }
                            message = firstError?.msg || 'Validation error'
                        }
                    }

                    toast.error(message)
                    return false
                }
            },

            register: async (data: RegisterData) => {
                set({ isLoading: true })
                try {
                    await authApi.register(data)
                    set({ isLoading: false })

                    toast.success('Registration successful! Please log in.')
                    return true
                } catch (error: unknown) {
                    set({ isLoading: false })

                    // Handle different error types
                    const errorObj = error as { response?: { data?: { detail?: string | object[] } } }
                    let message = 'Registration failed'

                    if (errorObj.response?.data?.detail) {
                        const detail = errorObj.response.data.detail
                        if (typeof detail === 'string') {
                            message = detail
                        } else if (Array.isArray(detail) && detail.length > 0) {
                            // Handle validation errors array
                            const firstError = detail[0] as { msg?: string }
                            message = firstError?.msg || 'Validation error'
                        }
                    }

                    toast.error(message)
                    return false
                }
            },

            logout: () => {
                localStorage.removeItem('access_token')
                localStorage.removeItem('user')

                set({
                    user: null,
                    token: null,
                    isAuthenticated: false,
                })

                toast.success('Logged out successfully')
            },

            updateProfile: async (data: Partial<User>) => {
                try {
                    const response = await authApi.updateProfile(data)
                    const updatedUser = response.data

                    set((state) => ({
                        user: updatedUser || state.user,
                    }))

                    toast.success('Profile updated successfully')
                    return true
                } catch (error: unknown) {
                    // Handle different error types
                    const errorObj = error as { response?: { data?: { detail?: string | object[] } } }
                    let message = 'Profile update failed'

                    if (errorObj.response?.data?.detail) {
                        const detail = errorObj.response.data.detail
                        if (typeof detail === 'string') {
                            message = detail
                        } else if (Array.isArray(detail) && detail.length > 0) {
                            // Handle validation errors array
                            const firstError = detail[0] as { msg?: string }
                            message = firstError?.msg || 'Validation error'
                        }
                    }

                    toast.error(message)
                    return false
                }
            },

            initializeAuth: () => {
                const token = localStorage.getItem('access_token')
                const userStr = localStorage.getItem('user')

                if (token && userStr) {
                    try {
                        const user = JSON.parse(userStr)
                        set({
                            user,
                            token,
                            isAuthenticated: true,
                        })
                    } catch (error) {
                        // Clear invalid data
                        localStorage.removeItem('access_token')
                        localStorage.removeItem('user')
                    }
                }
            },
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                user: state.user,
                token: state.token,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
)
