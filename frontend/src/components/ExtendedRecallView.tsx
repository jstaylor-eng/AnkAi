import { useState } from 'react'
import { useAnki } from '../hooks/useAnki'
import { Reader } from './Reader'
import type { ProcessedArticle } from '../types'

interface ExtendedRecallViewProps {
  onBack: () => void
}

type ViewState = 'setup' | 'reading'

export function ExtendedRecallView({ onBack }: ExtendedRecallViewProps) {
  const { generateRecallPassage, submitReview, getCardIntervals, loading } = useAnki()

  // Setup state
  const [viewState, setViewState] = useState<ViewState>('setup')
  const [topic, setTopic] = useState('')
  const [targetCharCount, setTargetCharCount] = useState(50)

  // Reading state
  const [article, setArticle] = useState<ProcessedArticle | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadPassage = async () => {
    setLoadError(null)
    try {
      const result = await generateRecallPassage(
        topic.trim() || undefined,
        targetCharCount
      )
      setArticle(result)
      setViewState('reading')
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to generate passage')
    }
  }

  const handleStart = () => {
    loadPassage()
  }

  const handleBackToSetup = () => {
    setViewState('setup')
    setArticle(null)
  }

  const handleReview = async (cardId: number, ease: number) => {
    await submitReview(cardId, ease)
  }

  const handleGenerateMore = () => {
    loadPassage()
  }

  // Setup screen
  if (viewState === 'setup') {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-4">
            <button
              onClick={onBack}
              className="text-gray-500 hover:text-gray-700"
            >
              &larr; Back
            </button>
            <h1 className="font-bold">Extended Recall</h1>
          </div>
        </header>

        <main className="max-w-2xl mx-auto p-4">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-medium mb-4">Configure Practice</h2>

            {/* Topic input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Topic / Notes (optional)
              </label>
              <textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., ordering food at a restaurant, talking about hobbies, describing my family..."
                rows={3}
                className="w-full p-3 border rounded-lg text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">
                The passage will be focused on this topic
              </p>
            </div>

            {/* Character count slider */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Passage Length: ~{targetCharCount} characters
              </label>
              <input
                type="range"
                min="30"
                max="150"
                step="10"
                value={targetCharCount}
                onChange={(e) => setTargetCharCount(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Short (30)</span>
                <span>Medium (90)</span>
                <span>Long (150)</span>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Multiple sentences totaling this length (+/- 15%)
              </p>
            </div>

            {/* Error message */}
            {loadError && (
              <div className="text-red-600 text-sm mb-4">{loadError}</div>
            )}

            {/* Start button */}
            <button
              onClick={handleStart}
              disabled={loading}
              className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {loading ? 'Generating...' : 'Generate Passage'}
            </button>
          </div>
        </main>
      </div>
    )
  }

  // Loading state (shouldn't normally show since we go to reading after load)
  if (loading && !article) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-500 mb-2">Generating practice passage...</div>
          <div className="text-sm text-gray-400">
            {topic ? `Topic: ${topic}` : 'Using your vocabulary'}
          </div>
        </div>
      </div>
    )
  }

  if (!article) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">No passage available</div>
      </div>
    )
  }

  // Reading screen - uses Reader component
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b sticky top-0 bg-white z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-4">
          <button
            onClick={handleBackToSetup}
            className="text-gray-500 hover:text-gray-700"
          >
            &larr; Settings
          </button>
          <div className="flex-1">
            <h1 className="font-medium">{article.title || 'Practice Passage'}</h1>
            <p className="text-xs text-gray-500">
              {topic && `Topic: ${topic.slice(0, 30)}${topic.length > 30 ? '...' : ''}`}
              {loading && ' (generating more...)'}
            </p>
          </div>
          <button
            onClick={handleGenerateMore}
            disabled={loading}
            className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Loading...' : 'New Passage'}
          </button>
        </div>
      </header>

      {/* Reader content */}
      <main className="p-4">
        <Reader
          article={article}
          onReview={handleReview}
          getCardIntervals={getCardIntervals}
        />

        {/* English translation toggle (for generated passages) */}
        {article.stats.english_translation && (
          <details className="mt-6 bg-gray-50 rounded-lg p-4 max-w-2xl mx-auto">
            <summary className="cursor-pointer text-sm text-gray-600 font-medium">
              Show English Translation
            </summary>
            <p className="mt-3 text-gray-700 italic">
              {article.stats.english_translation}
            </p>
          </details>
        )}
      </main>
    </div>
  )
}
