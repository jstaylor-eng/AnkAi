import { useState, useEffect } from 'react'
import { useAnki } from './hooks/useAnki'
import { DeckSelector } from './components/DeckSelector'
import { Reader } from './components/Reader'
import type { ProcessedArticle, VocabStats } from './types'

type AppState = 'loading' | 'error' | 'select-decks' | 'ready' | 'processing' | 'reading'

function App() {
  const [state, setState] = useState<AppState>('loading')
  const [vocabStats, setVocabStats] = useState<VocabStats | null>(null)
  const [article, setArticle] = useState<ProcessedArticle | null>(null)
  const [inputUrl, setInputUrl] = useState('')
  const [inputText, setInputText] = useState('')
  const [inputMode, setInputMode] = useState<'url' | 'text'>('text')
  const [useRewrite, setUseRewrite] = useState(true)

  const {
    error,
    checkHealth,
    getDecks,
    selectDecks,
    processArticle,
    submitReview,
    triggerSync,
    getCardIntervals,
  } = useAnki()

  useEffect(() => {
    checkConnection()
  }, [])

  const checkConnection = async () => {
    try {
      const health = await checkHealth()
      if (health.status === 'ok') {
        setState('select-decks')
      } else {
        setState('error')
      }
    } catch {
      setState('error')
    }
  }

  const handleDecksSelected = (stats: VocabStats) => {
    setVocabStats(stats)
    setState('ready')
  }

  const handleProcessArticle = async () => {
    setState('processing')
    try {
      const result = await processArticle({
        ...(inputMode === 'url' ? { url: inputUrl } : { text: inputText }),
        rewrite: useRewrite,
      })
      setArticle(result)
      setState('reading')
    } catch {
      setState('ready')
    }
  }

  const handleReview = async (cardId: number, ease: number) => {
    await submitReview(cardId, ease)
  }

  const handleBack = () => {
    setArticle(null)
    setState('ready')
  }

  const handleSync = async () => {
    try {
      await triggerSync()
      alert('Sync complete!')
    } catch (err) {
      alert('Sync failed: ' + (err instanceof Error ? err.message : 'Unknown error'))
    }
  }

  // Loading state
  if (state === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Connecting to Anki...</div>
      </div>
    )
  }

  // Error state
  if (state === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 mb-4">
            Cannot connect to Anki
          </div>
          <p className="text-gray-500 text-sm mb-4">
            Make sure Anki is running with AnkiConnect installed
          </p>
          <button
            onClick={checkConnection}
            className="text-blue-600 underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Deck selection
  if (state === 'select-decks') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-lg max-w-md w-full">
          <div className="p-4 border-b">
            <h1 className="text-xl font-bold">AnkAi</h1>
            <p className="text-sm text-gray-500">Learn Chinese with your Anki vocabulary</p>
          </div>
          <DeckSelector
            onDecksSelected={handleDecksSelected}
            getDecks={getDecks}
            selectDecks={selectDecks}
          />
        </div>
      </div>
    )
  }

  // Reading view
  if (state === 'reading' && article) {
    return (
      <div className="min-h-screen bg-white">
        <header className="border-b sticky top-0 bg-white z-10">
          <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-4">
            <button
              onClick={handleBack}
              className="text-gray-500 hover:text-gray-700"
            >
              &larr; Back
            </button>
            <h1 className="font-medium flex-1">{article.title || 'Article'}</h1>
          </div>
        </header>
        <main className="p-4">
          <Reader article={article} onReview={handleReview} getCardIntervals={getCardIntervals} />
        </main>
      </div>
    )
  }

  // Ready / input state
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="font-bold">AnkAi</h1>
            {vocabStats && (
              <p className="text-xs text-gray-500">
                {vocabStats.total} words loaded
                ({vocabStats.due} due, {vocabStats.new} new)
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSync}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              Sync
            </button>
            <button
              onClick={() => setState('select-decks')}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Change Decks
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto p-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h2 className="font-medium mb-3">Process Article</h2>

          {/* Input mode tabs */}
          <div className="flex gap-2 mb-3">
            <button
              onClick={() => setInputMode('text')}
              className={`px-3 py-1 text-sm rounded ${
                inputMode === 'text'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Paste Text
            </button>
            <button
              onClick={() => setInputMode('url')}
              className={`px-3 py-1 text-sm rounded ${
                inputMode === 'url'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              URL
            </button>
          </div>

          {/* Input field */}
          {inputMode === 'url' ? (
            <input
              type="url"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              placeholder="https://..."
              className="w-full p-3 border rounded-lg mb-3"
            />
          ) : (
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste Chinese text here..."
              rows={6}
              className="w-full p-3 border rounded-lg mb-3 chinese-text"
            />
          )}

          {/* Rewrite toggle */}
          <label className="flex items-center gap-2 mb-3 cursor-pointer">
            <input
              type="checkbox"
              checked={useRewrite}
              onChange={(e) => setUseRewrite(e.target.checked)}
              className="h-4 w-4"
            />
            <span className="text-sm">
              Simplify using my vocabulary
              <span className="text-gray-400 ml-1">(uses AI)</span>
            </span>
          </label>

          {/* Error message */}
          {error && (
            <div className="text-red-600 text-sm mb-3">{error}</div>
          )}

          {/* Submit button */}
          <button
            onClick={handleProcessArticle}
            disabled={state === 'processing' || (!inputUrl && !inputText)}
            className="w-full py-2 bg-blue-600 text-white rounded-lg
                       disabled:bg-gray-300 disabled:cursor-not-allowed
                       hover:bg-blue-700 transition-colors"
          >
            {state === 'processing' ? 'Processing...' : 'Analyze Text'}
          </button>
        </div>
      </main>
    </div>
  )
}

export default App
