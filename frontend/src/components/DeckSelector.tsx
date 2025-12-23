import { useState, useEffect } from 'react'
import type { VocabStats } from '../types'

interface DeckSelectorProps {
  onDecksSelected: (deckNames: string[], stats: VocabStats) => void
  getDecks: () => Promise<string[]>
  selectDecks: (deckNames: string[]) => Promise<{ selected: string[]; stats: VocabStats }>
}

export function DeckSelector({ onDecksSelected, getDecks, selectDecks }: DeckSelectorProps) {
  const [decks, setDecks] = useState<string[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDecks()
  }, [])

  const loadDecks = async () => {
    try {
      setLoading(true)
      const deckList = await getDecks()
      setDecks(deckList)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load decks')
    } finally {
      setLoading(false)
    }
  }

  const toggleDeck = (deck: string) => {
    const newSelected = new Set(selected)
    if (newSelected.has(deck)) {
      newSelected.delete(deck)
    } else {
      newSelected.add(deck)
    }
    setSelected(newSelected)
  }

  const handleConfirm = async () => {
    if (selected.size === 0) return
    try {
      setLoading(true)
      const result = await selectDecks(Array.from(selected))
      onDecksSelected(result.selected, result.stats)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select decks')
    } finally {
      setLoading(false)
    }
  }

  if (loading && decks.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        Loading decks...
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-600 mb-2">{error}</div>
        <button
          onClick={loadDecks}
          className="text-blue-600 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-3">Select Anki Decks</h2>
      <p className="text-sm text-gray-600 mb-4">
        Choose which decks to use as your vocabulary source
      </p>

      <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
        {decks.map((deck) => (
          <label
            key={deck}
            className="flex items-center p-2 rounded hover:bg-gray-50 cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.has(deck)}
              onChange={() => toggleDeck(deck)}
              className="mr-3 h-4 w-4"
            />
            <span className="text-sm">{deck}</span>
          </label>
        ))}
      </div>

      <button
        onClick={handleConfirm}
        disabled={selected.size === 0 || loading}
        className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg
                   disabled:bg-gray-300 disabled:cursor-not-allowed
                   hover:bg-blue-700 transition-colors"
      >
        {loading ? 'Loading vocabulary...' : `Load ${selected.size} deck(s)`}
      </button>
    </div>
  )
}
