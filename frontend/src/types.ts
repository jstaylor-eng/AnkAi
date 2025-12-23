export type VocabStatus = 'new' | 'due' | 'learned' | 'unknown'

export interface Word {
  hanzi: string
  pinyin: string
  definition: string
  status: VocabStatus
  card_id: number | null
  deck_name: string | null
}

export interface Sentence {
  original: string
  simplified: string
  words: Word[]
  translation: string
}

export interface ProcessedArticle {
  title: string
  sentences: Sentence[]
  due_words: Word[]
  new_words: Word[]
  stats: {
    total_words: number
    known_words: number
    comprehension_percent: number
    due_count: number
    new_count: number
    unknown_count: number
    english_translation?: string  // For generated passages
    is_generated_passage?: boolean
  }
}

export interface VocabStats {
  total: number
  new: number
  due: number
  learned: number
}

export interface RecallSentence {
  english: string
  chinese: string
  pinyin: string
  word_order_english: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  words: Word[]
  translation?: string
}
