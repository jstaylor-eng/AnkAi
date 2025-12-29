import { useState } from 'react'
import { useAnki } from '../hooks/useAnki'
import { useTTS } from '../hooks/useTTS'

interface ExtendedRecallViewProps {
  onBack: () => void
}

interface Passage {
  chinese: string
  english: string
  title: string
}

type ViewState = 'setup' | 'practice'

export function ExtendedRecallView({ onBack }: ExtendedRecallViewProps) {
  const { generateRecallPassage, loading } = useAnki()
  const { speakWord, rate, setRate } = useTTS()

  // Setup state
  const [viewState, setViewState] = useState<ViewState>('setup')
  const [topic, setTopic] = useState('')
  const [targetCharCount, setTargetCharCount] = useState(60)

  // Practice state
  const [passage, setPassage] = useState<Passage | null>(null)
  const [showChinese, setShowChinese] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadPassage = async () => {
    setLoadError(null)
    setShowChinese(false)
    try {
      const result = await generateRecallPassage(
        topic.trim() || undefined,
        targetCharCount
      )
      // Extract passage info from ProcessedArticle
      setPassage({
        chinese: result.sentences.map(s => s.simplified || s.original).join(''),
        english: result.stats.english_translation || '',
        title: result.title || 'Practice Passage',
      })
      setViewState('practice')
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to generate passage')
    }
  }

  const handleStart = () => {
    loadPassage()
  }

  const handleBackToSetup = () => {
    setViewState('setup')
    setPassage(null)
    setShowChinese(false)
  }

  const handlePlayAudio = () => {
    if (passage?.chinese) {
      speakWord(passage.chinese)
    }
  }

  const handleNewPassage = () => {
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
            <h2 className="text-lg font-medium mb-2">Configure Practice</h2>
            <p className="text-sm text-gray-500 mb-6">
              Practice recalling longer Chinese passages from English prompts
            </p>

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
                Passage will use your known vocabulary + proper nouns
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

  // Loading state
  if (loading && !passage) {
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

  if (!passage) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">No passage available</div>
      </div>
    )
  }

  // Practice screen - English prompt, recall Chinese
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-4">
          <button
            onClick={handleBackToSetup}
            className="text-gray-500 hover:text-gray-700"
          >
            &larr; Settings
          </button>
          <div className="flex-1">
            <h1 className="font-bold">Extended Recall</h1>
            <p className="text-xs text-gray-500">
              {passage.title}
              {loading && ' (loading...)'}
            </p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-2xl mx-auto p-4">
        <div className="bg-white rounded-xl shadow-sm p-6">
          {/* English prompt */}
          <div className="mb-6">
            <div className="text-sm text-gray-500 mb-3">Recall this in Chinese:</div>
            <div className="text-lg text-gray-900 leading-relaxed whitespace-pre-wrap p-4 bg-blue-50 rounded-lg border border-blue-100">
              {passage.english}
            </div>
          </div>

          {/* Reveal toggle */}
          <div className="mb-6">
            <button
              onClick={() => setShowChinese(!showChinese)}
              className={`w-full py-3 rounded-lg text-sm font-medium transition-colors ${
                showChinese
                  ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              {showChinese ? 'Hide Chinese Answer' : 'Show Chinese Answer'}
            </button>
          </div>

          {/* Revealed Chinese */}
          {showChinese && (
            <div className="p-4 bg-green-50 rounded-lg border border-green-100 mb-6">
              <div className="text-sm text-green-700 mb-2">Chinese:</div>
              <div className="text-2xl chinese-text leading-relaxed text-gray-900">
                {passage.chinese}
              </div>
            </div>
          )}

          {/* Audio and controls */}
          <div className="flex items-center justify-between border-t pt-4">
            <div className="flex items-center gap-4">
              {/* Play audio button */}
              <button
                onClick={handlePlayAudio}
                disabled={!showChinese}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  showChinese
                    ? 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
                title={showChinese ? 'Play audio' : 'Reveal Chinese first'}
              >
                <span className="text-lg">&#128266;</span>
                <span className="text-sm">Play</span>
              </button>

              {/* Speed control */}
              {showChinese && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <span>{rate.toFixed(1)}x</span>
                  <input
                    type="range"
                    min="0.5"
                    max="1"
                    step="0.1"
                    value={rate}
                    onChange={(e) => setRate(parseFloat(e.target.value))}
                    className="w-16"
                  />
                </div>
              )}
            </div>

            {/* New passage button */}
            <button
              onClick={handleNewPassage}
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Loading...' : 'New Passage'}
            </button>
          </div>
        </div>

        {/* Tips */}
        <div className="mt-4 p-4 bg-amber-50 rounded-lg text-sm text-amber-800 border border-amber-100">
          <strong>Tip:</strong> Try to recall the entire passage in Chinese before revealing.
          The passage uses only your known vocabulary plus any proper nouns.
        </div>
      </main>
    </div>
  )
}
