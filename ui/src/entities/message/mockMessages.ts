import type { Message } from './message'

const INITIAL_TIMESTAMP = '07:35 PM'

// Content lifted verbatim from optibot.html (the OptiBot chat reference markup).
export const initialMessages: Message[] = [
  {
    id: 'greeting',
    role: 'assistant',
    text: "Hi! I'm OptiBot, your AI assistant for OptiSigns. I can help you with setup, troubleshooting, managing your screens, playlists, and schedules. How can I help you today?",
    timestamp: INITIAL_TIMESTAMP,
    feedback: null,
  },
  {
    id: 'user-capabilities',
    role: 'user',
    text: 'hi what can you do',
    timestamp: INITIAL_TIMESTAMP,
  },
  {
    id: 'assistant-capabilities',
    role: 'assistant',
    text: 'I can look at your screens, content and billing, make changes for you with your approval, and walk you through anything in the help centre. What would you like to do?',
    timestamp: INITIAL_TIMESTAMP,
    feedback: null,
  },
  {
    id: 'user-workflow',
    role: 'user',
    text: 'walk me through your work',
    timestamp: INITIAL_TIMESTAMP,
  },
  {
    id: 'assistant-workflow',
    role: 'assistant',
    text: `I check your account, screens, content or billing when a question touches them, then either explain from the help centre, suggest next steps, or propose changes (like renaming a screen or pushing a playlist) that you approve first.

For a screen problem I start with its status; for how-to questions I pull the exact article.

Tell me what you want to check or change and I'll get started.`,
    timestamp: INITIAL_TIMESTAMP,
    feedback: null,
  },
  {
    id: 'user-account',
    role: 'user',
    text: 'check my account',
    timestamp: INITIAL_TIMESTAMP,
  },
  {
    id: 'assistant-account',
    role: 'assistant',
    text: `Your account is on a Pro Plus trial with 2 screen licenses and 0 screens paired right now. No payment method is on file, so no charges will occur until you add one.

Next step: pair a screen or add a card if you want to keep the trial moving toward paid.`,
    timestamp: INITIAL_TIMESTAMP,
    searchedSources: 2,
    feedback: null,
  },
]

export const CANNED_REPLY: Message = {
  id: 'canned-reply',
  role: 'assistant',
  text: "I can help with that — ask me about your screens, content, billing, or anything in the help centre and I'll walk you through it.",
  timestamp: INITIAL_TIMESTAMP,
  searchedSources: 2,
  feedback: null,
}
