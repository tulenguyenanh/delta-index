import type { Message } from '../../entities/message/message'
import { BotIcon } from '../../shared/ui/icons'
import { FeedbackButtons } from './FeedbackButtons'
import { TypingIndicator } from './TypingIndicator'
import './chat.css'

interface MessageListProps {
  messages: Message[]
  isTyping: boolean
  onToggleFeedback: (id: string, value: 'up' | 'down') => void
}

function sourceLabel(count: number): string {
  return `Searched ${count} ${count === 1 ? 'source' : 'sources'}`
}

function MessageText({ text }: { text: string }) {
  const paragraphs = text.split('\n').filter((line) => line.trim() !== '')
  return (
    <>
      {paragraphs.map((paragraph, index) => (
        <p key={index} className="chat-bubble__paragraph">
          {paragraph}
        </p>
      ))}
    </>
  )
}

export function MessageList({ messages, isTyping, onToggleFeedback }: MessageListProps) {
  return (
    <div className="chat-message-list">
      {messages.map((message) => {
        if (message.role === 'user') {
          return (
            <div key={message.id} className="chat-row chat-row--user" data-testid="user-message">
              <div className="chat-bubble chat-bubble--user">{message.text}</div>
              <span className="chat-timestamp chat-timestamp--right">{message.timestamp}</span>
            </div>
          )
        }

        if (message.text.trim() === '') {
          return null
        }

        return (
          <div
            key={message.id}
            className="chat-row chat-row--assistant"
            data-testid="assistant-message"
          >
            <div className="chat-avatar" aria-hidden="true">
              <BotIcon size={16} />
            </div>
            <div className="chat-assistant-body">
              {typeof message.searchedSources === 'number' && (
                <div className="chat-citation">
                  <span className="chat-citation__label">
                    {sourceLabel(message.searchedSources)}
                  </span>
                </div>
              )}
              <div className="chat-bubble chat-bubble--bot">
                <MessageText text={message.text} />
              </div>
              <div className="chat-assistant-meta">
                <FeedbackButtons
                  value={message.feedback ?? null}
                  onSelect={(value) => onToggleFeedback(message.id, value)}
                />
                <span className="chat-timestamp">{message.timestamp}</span>
              </div>
            </div>
          </div>
        )
      })}
      {isTyping && <TypingIndicator />}
    </div>
  )
}
