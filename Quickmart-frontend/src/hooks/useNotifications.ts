import { useEffect, useState } from 'react'
import { messagesApi } from '../lib/api'

export interface UserMessage {
    user_id: string
    message_id: string
    message: string
    churn_probability: number
    churn_reasons: string[]
    created_at: string
    status: string
    read_at?: string
}

export function useNotifications() {
    const [messages, setMessages] = useState<UserMessage[]>([])
    const [unreadCount, setUnreadCount] = useState(0)
    const [isLoading, setIsLoading] = useState(false)

    const fetchMessages = async () => {
        setIsLoading(true)
        try {
            const data = await messagesApi.getMessages()
            setMessages(data.messages || [])
            setUnreadCount(data.unread_count || 0)
        } catch (error) {
            console.error('Failed to fetch messages:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const markMessageAsRead = async (messageId: string) => {
        try {
            await messagesApi.markAsRead(messageId)
            // Update local state
            setMessages(prev =>
                prev.map(msg =>
                    msg.message_id === messageId
                        ? { ...msg, status: 'read' }
                        : msg
                )
            )
            setUnreadCount(prev => Math.max(0, prev - 1))
        } catch (error) {
            console.error('Failed to mark message as read:', error)
        }
    }

    useEffect(() => {
        fetchMessages()
        // Poll for new messages every 2 minutes
        const interval = setInterval(fetchMessages, 120000)
        return () => clearInterval(interval)
    }, [])

    return {
        messages,
        unreadCount,
        isLoading,
        fetchMessages,
        markMessageAsRead,
    }
}

