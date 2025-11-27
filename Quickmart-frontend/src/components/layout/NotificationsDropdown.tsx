import { Bell, Check, X } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useNotifications } from '../../hooks/useNotifications'
import { format } from 'date-fns'

export default function NotificationsDropdown() {
    const [isOpen, setIsOpen] = useState(false)
    const { messages, unreadCount, isLoading, markMessageAsRead } = useNotifications()
    const dropdownRef = useRef<HTMLDivElement>(null)

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside)
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [isOpen])

    const handleMessageClick = (messageId: string, status: string) => {
        if (status === 'generated') {
            markMessageAsRead(messageId)
        }
    }

    const formatDate = (dateString: string) => {
        try {
            return format(new Date(dateString), 'MMM d, h:mm a')
        } catch {
            return dateString
        }
    }

    const getChurnColor = (probability: number) => {
        if (probability >= 0.8) return 'text-red-600 bg-red-50'
        if (probability >= 0.6) return 'text-orange-600 bg-orange-50'
        return 'text-yellow-600 bg-yellow-50'
    }

    return (
        <div className="relative" ref={dropdownRef}>
            {/* Notification Bell Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 text-gray-700 hover:text-primary-600 transition-colors rounded-lg hover:bg-gray-100"
                aria-label="Notifications"
            >
                <Bell className="w-6 h-6" />
                {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium animate-pulse">
                        {unreadCount}
                    </span>
                )}
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-[32rem] overflow-hidden flex flex-col">
                    {/* Header */}
                    <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between bg-gray-50">
                        <div>
                            <h3 className="text-sm font-semibold text-gray-900">
                                Notifications
                            </h3>
                            {unreadCount > 0 && (
                                <p className="text-xs text-gray-500 mt-0.5">
                                    {unreadCount} unread {unreadCount === 1 ? 'message' : 'messages'}
                                </p>
                            )}
                        </div>
                        <button
                            onClick={() => setIsOpen(false)}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Messages List */}
                    <div className="overflow-y-auto flex-1">
                        {isLoading ? (
                            <div className="flex items-center justify-center py-8">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                            </div>
                        ) : messages.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 px-4">
                                <Bell className="w-12 h-12 text-gray-300 mb-3" />
                                <p className="text-sm text-gray-500 text-center">
                                    No messages yet
                                </p>
                                <p className="text-xs text-gray-400 text-center mt-1">
                                    You'll see personalized messages here
                                </p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100">
                                {messages.map((message) => (
                                    <div
                                        key={message.message_id}
                                        onClick={() => handleMessageClick(message.message_id, message.status)}
                                        className={`p-4 hover:bg-gray-50 transition-colors cursor-pointer ${
                                            message.status === 'generated' ? 'bg-blue-50/30' : ''
                                        }`}
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex-1 min-w-0">
                                                {/* Message */}
                                                <p className="text-sm text-gray-900 mb-2 leading-relaxed">
                                                    {message.message}
                                                </p>

                                                {/* Churn Info */}
                                                <div className="flex items-center gap-2 mb-2">
                                                    <span
                                                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${getChurnColor(
                                                            message.churn_probability
                                                        )}`}
                                                    >
                                                        {(message.churn_probability * 100).toFixed(0)}% churn risk
                                                    </span>
                                                    {message.churn_reasons.length > 0 && (
                                                        <span className="text-xs text-gray-500">
                                                            {message.churn_reasons[0].replace(/_/g, ' ')}
                                                        </span>
                                                    )}
                                                </div>

                                                {/* Timestamp */}
                                                <p className="text-xs text-gray-400">
                                                    {formatDate(message.created_at)}
                                                </p>
                                            </div>

                                            {/* Read/Unread Indicator */}
                                            <div className="flex-shrink-0">
                                                {message.status === 'generated' ? (
                                                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                                ) : (
                                                    <Check className="w-4 h-4 text-green-500" />
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    {messages.length > 0 && (
                        <div className="px-4 py-2 border-t border-gray-200 bg-gray-50">
                            <p className="text-xs text-center text-gray-500">
                                Click on a message to mark it as read
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

