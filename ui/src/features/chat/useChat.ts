import { useCallback, useEffect, useRef, useState } from 'react'
import type { Message } from '../../entities/message/message'

const UNREACHABLE_MESSAGE =
  "I can't reach my brain right now — the assistant backend seems to be down. Please try again in a moment."
const EMPTY_ANSWER_MESSAGE =
  "I couldn't find an answer to that. Please try rephrasing your question."

function nowTimestamp(): string {
  return new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

function parseSseBlock(block: string): { event: string; data: string } {
  let event = ''
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart())
    }
  }
  return { event, data: dataLines.join('\n').trim() }
}

export interface UseChatResult {
  messages: Message[]
  isTyping: boolean
  sendMessage: (text: string) => void
  toggleFeedback: (id: string, value: 'up' | 'down') => void
}

export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const idRef = useRef(0)

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  const sendMessage = useCallback((text: string) => {
    const trimmed = text.trim()
    if (trimmed === '') {
      return
    }

    // One controller per send; aborting on unmount stops an in-flight stream
    // from touching state after teardown.
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    idRef.current += 1
    const userId = `user-${Date.now()}-${idRef.current}`
    idRef.current += 1
    const placeholderId = `assistant-${Date.now()}-${idRef.current}`

    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', text: trimmed, timestamp: nowTimestamp() },
      { id: placeholderId, role: 'assistant', text: '', timestamp: nowTimestamp() },
    ])
    setIsTyping(true)

    const updatePlaceholder = (updater: (message: Message) => Message) => {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === placeholderId ? updater(message) : message,
        ),
      )
    }

    // A finished reply must never stay blank: MessageList hides blank assistant text.
    const fillIfBlank = () => {
      updatePlaceholder((message) =>
        message.text.trim() === '' ? { ...message, text: EMPTY_ANSWER_MESSAGE } : message,
      )
    }

    const fail = () => {
      updatePlaceholder((message) => ({ ...message, text: UNREACHABLE_MESSAGE }))
      setIsTyping(false)
    }

    void (async () => {
      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: trimmed }),
          signal: controller.signal,
        })

        if (!response.ok || response.body === null) {
          fail()
          return
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let firstToken = true

        while (true) {
          const { done, value } = await reader.read()
          if (done) {
            break
          }
          buffer += decoder.decode(value, { stream: true })
          const blocks = buffer.split('\n\n')
          buffer = blocks.pop() ?? ''
          for (const block of blocks) {
            const { event, data } = parseSseBlock(block)
            if (event === 'token') {
              const fragment = JSON.parse(data) as string
              if (firstToken) {
                setIsTyping(false)
                firstToken = false
              }
              updatePlaceholder((message) => ({ ...message, text: message.text + fragment }))
            } else if (event === 'citations') {
              const urls = JSON.parse(data) as string[]
              updatePlaceholder((message) => ({ ...message, searchedSources: urls.length }))
            } else if (event === 'done') {
              fillIfBlank()
              setIsTyping(false)
              return
            } else if (event === 'error') {
              const message = JSON.parse(data) as string
              updatePlaceholder((m) => ({ ...m, text: message }))
              setIsTyping(false)
              return
            }
          }
        }

        // Stream ended without a `done` event — settle the typing state.
        fillIfBlank()
        setIsTyping(false)
      } catch {
        if (!controller.signal.aborted) {
          fail()
        }
      }
    })()
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
