import { useState, useCallback } from 'react'
import type { ProcessedArticle, VocabStats } from '../types'

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

  return {
    loading,
    error,
    checkHealth,
    getDecks,
    selectDecks,
    processArticle,
    submitReview,
    triggerSync,
  }
}
