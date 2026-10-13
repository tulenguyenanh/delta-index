import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { AttachIcon, SendIcon } from '../../shared/ui/icons'
import './chat.css'

interface ComposerProps {
  onSend: (text: string) => void
}

export function Composer({ onSend }: ComposerProps) {
  const [value, setValue] = useState('')
  const canSend = value.trim() !== ''

  function submit() {
    if (!canSend) {
      return
    }
    onSend(value)
    setValue('')
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="chat-composer">
      <textarea
        className="chat-composer__input"
        placeholder="Ask me anything..."
        maxLength={2000}
        rows={1}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <div className="chat-composer__toolbar">
        <button type="button" className="chat-icon-button" aria-label="Attach images" disabled>
          <AttachIcon size={16} />
        </button>
        <button
          type="button"
          className="chat-send-button"
          aria-label="Send"
          onClick={submit}
          disabled={!canSend}
        >
          <SendIcon size={16} />
        </button>
      </div>
    </div>
  )
}
