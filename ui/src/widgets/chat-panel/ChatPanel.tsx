import { useState } from 'react'
import { useChat } from '../../features/chat/useChat'
import { MessageList } from '../../features/chat/MessageList'
import { Composer } from '../../features/chat/Composer'
import { BotIcon, ChevronDownIcon, ChevronUpIcon, HeadsetIcon } from '../../shared/ui/icons'
import { useStickToBottom } from './useStickToBottom'
import './ChatPanel.css'

export function ChatPanel() {
  const { messages, isTyping, sendMessage, toggleFeedback } = useChat()
  const [supportOpen, setSupportOpen] = useState(true)
  const { ref: scrollRef, onScroll: handleScroll } = useStickToBottom<HTMLDivElement>()

  return (
    <div className="chat-panel" role="complementary" aria-label="OptiBot">
      <div className="chat-panel__body" data-testid="optibot-panel-body">
        <header className="chat-panel__header">
          <div className="chat-panel__brand">
            <div className="chat-panel__avatar" aria-hidden="true">
              <BotIcon size={16} />
            </div>
            <h2 className="chat-panel__title">OptiBot</h2>
          </div>
        </header>

        <section className="chat-support">
          <div className="chat-support__card">
            <div className="chat-support__row">
              <span className="chat-support__icon" aria-hidden="true">
                <HeadsetIcon size={16} />
              </span>
              {supportOpen && (
                <div className="chat-support__text">
                  <p className="chat-support__title">Contact Support Team</p>
                  <p className="chat-support__meta">
                    <a className="chat-support__link" href="mailto:support@optisigns.com">
                      support@optisigns.com
                    </a>
                    {' · Mon - Fri: 7AM - 7PM CDT'}
                  </p>
                </div>
              )}
            </div>
            <button
              type="button"
              className="chat-support__toggle"
              aria-label={supportOpen ? 'Collapse support info' : 'Expand support info'}
              aria-expanded={supportOpen}
              onClick={() => setSupportOpen((open) => !open)}
            >
              {supportOpen ? <ChevronUpIcon size={14} /> : <ChevronDownIcon size={14} />}
            </button>
          </div>
        </section>

        <div className="chat-panel__scroll" ref={scrollRef} onScroll={handleScroll}>
          <MessageList
            messages={messages}
            isTyping={isTyping}
            onToggleFeedback={toggleFeedback}
          />
        </div>

        <footer className="chat-panel__footer">
          <Composer onSend={sendMessage} />
        </footer>
      </div>
    </div>
  )
}

export default ChatPanel
