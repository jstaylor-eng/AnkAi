import { useState, useCallback } from 'react'
import type { ProcessedArticle, VocabStats, RecallSentence, ChatMessage } from '../types'

const API_BASE = '/api'

export function useAnki() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchApi = useCallback(async <T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
        },
        ...options,
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || `HTTP ${response.status}`)
      }
      return await response.json()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const checkHealth = useCallback(async () => {
    return fetchApi<{ status: string; anki_connect_version?: number }>('/health')
  }, [fetchApi])

  const getDecks = useCallback(async () => {
    const data = await fetchApi<{ decks: string[] }>('/decks')
    return data.decks
  }, [fetchApi])

  const selectDecks = useCallback(async (deckNames: string[]) => {
    const data = await fetchApi<{ selected: string[]; stats: VocabStats }>(
      '/decks/select',
      {
        method: 'POST',
        body: JSON.stringify({ deck_names: deckNames }),
      }
    )
    return data
  }, [fetchApi])

  const processArticle = useCallback(async (
    input: { url?: string; text?: string; rewrite?: boolean; max_new_words?: number }
  ): Promise<ProcessedArticle> => {
    return fetchApi<ProcessedArticle>('/article/process', {
      method: 'POST',
      body: JSON.stringify(input),
    })
  }, [fetchApi])

  const submitReview = useCallback(async (cardId: number, ease: number) => {
    return fetchApi<{ success: boolean }>('/review', {
      method: 'POST',
      body: JSON.stringify({ card_id: cardId, ease }),
    })
  }, [fetchApi])

  const triggerSync = useCallback(async () => {
    return fetchApi<{ status: string }>('/sync', { method: 'POST' })
  }, [fetchApi])

  const getCardIntervals = useCallback(async (cardId: number) => {
    return fetchApi<{
      intervals: { again: string; hard: string; good: string; easy: string } | null
    }>(`/card/${cardId}/intervals`)
  }, [fetchApi])

  const generateRecallSentences = useCallback(async (
    count: number = 5,
    topic?: string,
    targetWordCount?: number
  ) => {
    return fetchApi<{
      sentences: RecallSentence[]
      stats: { total_generated: number; due_words_available: number; new_words_available: number }
    }>('/recall/generate', {
      method: 'POST',
      body: JSON.stringify({
        count,
        topic: topic || null,
        target_word_count: targetWordCount || null
      }),
    })
  }, [fetchApi])

  const generateRecallPassage = useCallback(async (
    topic?: string,
    targetCharCount: number = 50
  ): Promise<ProcessedArticle> => {
    return fetchApi<ProcessedArticle>('/recall/generate-passage', {
      method: 'POST',
      body: JSON.stringify({
        topic: topic || null,
        target_char_count: targetCharCount
      }),
    })
  }, [fetchApi])

  const sendChatMessage = useCallback(async (
    message: string,
    history: Array<{ role: string; text: string }>
  ) => {
    return fetchApi<{
      user_message: ChatMessage
      ai_message: ChatMessage
    }>('/chat/send', {
      method: 'POST',
      body: JSON.stringify({ message, history }),
    })
  }, [fetchApi])

  const getNewsHeadlines = useCallback(async () => {
    return fetchApi<{
      headlines: Array<{
        original: string
        description: string
        link: string
        pubDate: string
        chinese: string
        pinyin: string
      }>
      source: string
      fetch_time: string
    }>('/news/headlines')
  }, [fetchApi])

  const introduceNewWord = useCallback(async (word?: string) => {
    return fetchApi<{
      word: {
        hanzi: string
        pinyin: string
        definition: string
        status: string
        card_id: number | null
      }
      example_sentences: Array<{
        chinese: string
        pinyin: string
        english: string
        word_highlight: string
      }>
      recall_sentences: Array<{
        english: string
        chinese: string
        pinyin: string
      }>
      card_id: number | null
    }>('/new-word/introduce', {
      method: 'POST',
      body: JSON.stringify({ word: word || null }),
    })
  }, [fetchApi])

  return {
    loading,
    error,
    checkHealth,
    getDecks,
    selectDecks,
    processArticle,
    submitReview,
    triggerSync,
    getCardIntervals,
    generateRecallSentences,
    generateRecallPassage,
    sendChatMessage,
    getNewsHeadlines,
    introduceNewWord,
  }
}
