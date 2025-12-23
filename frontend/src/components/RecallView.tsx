import { useState, useEffect } from 'react'
import { useAnki } from '../hooks/useAnki'
import { useTTS } from '../hooks/useTTS'
import type { RecallSentence } from '../types'

interface RecallViewProps {
  onBack: () => void
}

export function RecallView({ onBack }: RecallViewProps) {
  const { generateRecallSentences, loading } = useAnki()
  const { speakWord, rate, setRate } = useTTS()

  const [sentences, setSentences] = useState<RecallSentence[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showChinese, setShowChinese] = useState(false)
  const [showPinyin, setShowPinyin] = useState(false)
  const [showWordOrder, setShowWordOrder] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadSentences = async () => {
    setLoadError(null)
    try {
      const result = await generateRecallSentences(5)
      setSentences(result.sentences)
      setCurrentIndex(0)
      // Reset reveal states for new batch
      setShowChinese(false)
      setShowPinyin(false)
      setShowWordOrder(false)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load sentences')
    }
  }

  useEffect(() => {
    loadSentences()
  }, [])

  const currentSentence = sentences[currentIndex]

  const handleNext = () => {
    if (currentIndex < sentences.length - 1) {
      setCurrentIndex(currentIndex + 1)
      // Reset reveal states for next sentence
      setShowChinese(false)
      setShowPinyin(false)
      setShowWordOrder(false)
    } else {
      // Load more sentences when we reach the end
      loadSentences()
    }
  }

  const handlePlayAudio = () => {
    if (currentSentence?.chinese) {
      speakWord(currentSentence.chinese)
    }
  }

  // Loading state
  if (loading && sentences.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-500 mb-2">Generating practice sentences...</div>
          <div className="text-sm text-gray-400">Using your vocabulary</div>
        </div>
      </div>
    )
  }

  // Error state
  if (loadError && sentences.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center">
          <div className="text-red-600 mb-4">{loadError}</div>
          <div className="flex gap-4 justify-center">
            <button onClick={onBack} className="text-gray-600 hover:text-gray-800">
              &larr; Back
            </button>
            <button
              onClick={loadSentences}
              className="text-blue-600 hover:text-blue-800"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!currentSentence) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">No sentences available</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-4">
          <button
            onClick={onBack}
            className="text-gray-500 hover:text-gray-700"
          >
            &larr; Back
          </button>
          <div className="flex-1">
            <h1 className="font-bold">Recall Practice</h1>
            <p className="text-xs text-gray-500">
              {currentIndex + 1} / {sentences.length}
              {loading && ' (loading more...)'}
            </p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-2xl mx-auto p-4">
        <div className="bg-white rounded-xl shadow-sm p-6">
          {/* English prompt */}
          <div className="mb-6">
            <div className="text-sm text-gray-500 mb-2">Translate to Chinese:</div>
            <div className="text-xl font-medium text-gray-900">
              "{currentSentence.english}"
            </div>
          </div>

          {/* Reveal toggles */}
          <div className="flex flex-wrap gap-2 mb-6">
            <button
              onClick={() => setShowChinese(!showChinese)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                showChinese
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {showChinese ? 'Hide' : 'Show'} Chinese
            </button>
            <button
              onClick={() => setShowPinyin(!showPinyin)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                showPinyin
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {showPinyin ? 'Hide' : 'Show'} Pinyin
            </button>
            <button
              onClick={() => setShowWordOrder(!showWordOrder)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                showWordOrder
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {showWordOrder ? 'Hide' : 'Show'} Word Order
            </button>
          </div>

          {/* Revealed content */}
          <div className="space-y-4 mb-6">
            {showChinese && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">Chinese:</div>
                <div className="text-2xl chinese-text">{currentSentence.chinese}</div>
              </div>
            )}
            {showPinyin && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">Pinyin:</div>
                <div className="text-lg text-gray-700">{currentSentence.pinyin}</div>
              </div>
            )}
            {showWordOrder && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">Word Order:</div>
                <div className="text-lg text-gray-600 italic">{currentSentence.word_order_english}</div>
              </div>
            )}
          </div>

          {/* Audio and navigation controls */}
          <div className="flex items-center justify-between border-t pt-4">
            <div className="flex items-center gap-4">
              {/* Play audio button */}
              <button
                onClick={handlePlayAudio}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition-colors"
              >
                <span className="text-lg">&#128266;</span>
                <span className="text-sm">Play Audio</span>
              </button>

              {/* Speed control */}
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span>{rate.toFixed(1)}x</span>
                <input
                  type="range"
                  min="0.5"
                  max="1"
                  step="0.1"
                  value={rate}
                  onChange={(e) => setRate(parseFloat(e.target.value))}
                  className="w-20"
                />
              </div>
            </div>

            {/* Next button */}
            <button
              onClick={handleNext}
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {currentIndex < sentences.length - 1 ? 'Next' : 'More'}
            </button>
          </div>
        </div>

        {/* Progress dots */}
        <div className="flex justify-center gap-2 mt-4">
          {sentences.map((_, idx) => (
            <button
              key={idx}
              onClick={() => {
                setCurrentIndex(idx)
                setShowChinese(false)
                setShowPinyin(false)
                setShowWordOrder(false)
              }}
              className={`w-3 h-3 rounded-full transition-colors ${
                idx === currentIndex
                  ? 'bg-blue-600'
                  : idx < currentIndex
                  ? 'bg-blue-300'
                  : 'bg-gray-300'
              }`}
            />
          ))}
        </div>
      </main>
    </div>
  )
}
