export type Role = 'user' | 'assistant'

export interface Message {
  id: string
  role: Role
  text: string
  timestamp: string
  searchedSources?: number
  feedback?: 'up' | 'down' | null
}
