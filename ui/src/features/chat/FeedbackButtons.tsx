import { ThumbsDownIcon, ThumbsUpIcon } from '../../shared/ui/icons'
import './chat.css'

interface FeedbackButtonsProps {
  value: 'up' | 'down' | null
  onSelect: (value: 'up' | 'down') => void
}

export function FeedbackButtons({ value, onSelect }: FeedbackButtonsProps) {
  return (
    <div className="chat-feedback" data-testid="feedback-buttons">
      <button
        type="button"
        className={'chat-icon-button chat-icon-button--sm' + (value === 'up' ? ' is-active' : '')}
        aria-label="Helpful"
        aria-pressed={value === 'up'}
        onClick={() => onSelect('up')}
      >
        <ThumbsUpIcon size={14} />
      </button>
      <button
        type="button"
        className={'chat-icon-button chat-icon-button--sm' + (value === 'down' ? ' is-active' : '')}
        aria-label="Not helpful"
        aria-pressed={value === 'down'}
        onClick={() => onSelect('down')}
      >
        <ThumbsDownIcon size={14} />
      </button>
    </div>
  )
}
