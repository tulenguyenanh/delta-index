import { BotIcon } from '../../shared/ui/icons'
import './chat.css'

export function TypingIndicator() {
  return (
    <div className="chat-row chat-row--assistant" data-testid="typing-indicator">
      <div className="chat-avatar" aria-hidden="true">
        <BotIcon size={16} />
      </div>
      <div className="chat-bubble chat-bubble--bot chat-typing" aria-label="OptiBot is typing">
        <span className="chat-typing__dot" />
        <span className="chat-typing__dot" />
        <span className="chat-typing__dot" />
      </div>
    </div>
  )
}
