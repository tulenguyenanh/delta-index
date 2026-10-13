import { useCallback, useEffect, useRef, useState } from 'react'
import type { Message } from '../../entities/message/message'
import { CANNED_REPLY, initialMessages } from '../../entities/message/mockMessages'

const REPLY_DELAY_MS = 800

function nowTimestamp(): string {
  return new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

export interface UseChatResult {
  messages: Message[]
  isTyping: boolean
  sendMessage: (text: string) => void
  toggleFeedback: (id: string, value: 'up' | 'down') => void
}

export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [isTyping, setIsTyping] = useState(false)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const idRef = useRef(0)

  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
    }
  }, [])

  const sendMessage = useCallback((text: string) => {
    const trimmed = text.trim()
    if (trimmed === '') {
      return
    }

    idRef.current += 1
    const userId = `user-${Date.now()}-${idRef.current}`
    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', text: trimmed, timestamp: nowTimestamp() },
    ])
    setIsTyping(true)

    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current)
    }

    timeoutRef.current = setTimeout(() => {
      idRef.current += 1
      setMessages((prev) => [
        ...prev,
        {
          ...CANNED_REPLY,
          id: `assistant-${Date.now()}-${idRef.current}`,
          timestamp: nowTimestamp(),
        },
      ])
      setIsTyping(false)
      timeoutRef.current = null
    }, REPLY_DELAY_MS)
  }, [])

  const toggleFeedback = useCallback((id: string, value: 'up' | 'down') => {
    setMessages((prev) =>
      prev.map((message) =>
        message.id === id
          ? { ...message, feedback: message.feedback === value ? null : value }
          : message,
      ),
    )
  }, [])

  return { messages, isTyping, sendMessage, toggleFeedback }
}
