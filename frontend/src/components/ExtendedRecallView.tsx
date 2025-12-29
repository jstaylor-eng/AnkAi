import { useState, useEffect, useCallback } from 'react'
import { useAnki } from '../hooks/useAnki'

interface ExtendedRecallViewProps {
  onBack: () => void
}

interface WordWithPinyin {
  hanzi: string
  pinyin: string
}

interface Passage {
  chinese: string
  english: string
  words: WordWithPinyin[]
  title: string
}

type ViewState = 'setup' | 'practice'

export function ExtendedRecallView({ onBack }: ExtendedRecallViewProps) {
  const { generateRecallPassage, loading } = useAnki()

  // Setup state
  const [viewState, setViewState] = useState<ViewState>('setup')
  const [topic, setTopic] = useState('')
  const [targetCharCount, setTargetCharCount] = useState(60)

  // Practice state
  const [passage, setPassage] = useState<Passage | null>(null)
  const [showChinese, setShowChinese] = useState(false)
  const [showPinyin, setShowPinyin] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  // Audio state - managed locally for proper play/stop
  const [isPlaying, setIsPlaying] = useState(false)
  const [rate, setRate] = useState(0.8)

  // Stop audio function
  const stopAudio = useCallback(() => {
    speechSynthesis.cancel()
    setIsPlaying(false)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      speechSynthesis.cancel()
    }
  }, [])

  const loadPassage = async () => {
    setLoadError(null)
    setShowChinese(false)
    setShowPinyin(false)
    stopAudio()
    try {
      const result = await generateRecallPassage(
        topic.trim() || undefined,
        targetCharCount
      )
      // Extract words with pinyin for ruby display
      const words: WordWithPinyin[] = result.sentences.flatMap(s =>
        s.words.map(w => ({
          hanzi: w.hanzi,
          pinyin: w.pinyin || ''
        }))
      )

      setPassage({
        chinese: result.sentences.map(s => s.simplified || s.original).join(''),
        english: result.stats.english_translation || '',
        words,
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
    stopAudio()
    setViewState('setup')
    setPassage(null)
    setShowChinese(false)
    setShowPinyin(false)
  }

  const handleToggleAudio = () => {
    if (isPlaying) {
      stopAudio()
    } else if (passage?.chinese) {
      const utterance = new SpeechSynthesisUtterance(passage.chinese)
      utterance.lang = 'zh-CN'
      utterance.rate = rate

      // Get Chinese voice
      const voices = speechSynthesis.getVoices()
      const chineseVoice = voices.find(v =>
        v.lang.includes('zh') || v.lang.includes('cmn')
      )
      if (chineseVoice) utterance.voice = chineseVoice

      utterance.onend = () => setIsPlaying(false)
      utterance.onerror = () => setIsPlaying(false)

      speechSynthesis.speak(utterance)
      setIsPlaying(true)
    }
  }

  const handleNewPassage = () => {
    stopAudio()
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

          {/* Reveal toggles */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={() => setShowChinese(!showChinese)}
              className={`flex-1 py-3 rounded-lg text-sm font-medium transition-colors ${
                showChinese
                  ? 'bg-green-100 text-green-700 hover:bg-green-200'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              {showChinese ? 'Hide Chinese' : 'Show Chinese'}
            </button>
            <button
              onClick={() => setShowPinyin(!showPinyin)}
              disabled={!showChinese}
              className={`px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                !showChinese
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : showPinyin
                  ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={showChinese ? 'Toggle pinyin' : 'Reveal Chinese first'}
            >
              {showPinyin ? 'Hide Pinyin' : 'Pinyin'}
            </button>
          </div>

          {/* Revealed Chinese */}
          {showChinese && (
            <div className="p-4 bg-green-50 rounded-lg border border-green-100 mb-6">
              <div className="text-sm text-green-700 mb-2">Chinese:</div>
              <div className="text-2xl chinese-text leading-loose text-gray-900">
                {showPinyin ? (
                  // Ruby display with pinyin above each word
                  passage.words.map((word, idx) => (
                    <ruby key={idx} className="mx-0.5">
                      {word.hanzi}
                      <rp>(</rp>
                      <rt className="text-xs text-gray-500 font-normal">{word.pinyin}</rt>
                      <rp>)</rp>
                    </ruby>
                  ))
                ) : (
                  // Plain Chinese text
                  passage.chinese
                )}
              </div>
            </div>
          )}

          {/* Audio and controls */}
          <div className="flex items-center justify-between border-t pt-4">
            <div className="flex items-center gap-4">
              {/* Play/Stop audio button */}
              <button
                onClick={handleToggleAudio}
                disabled={!showChinese}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  !showChinese
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : isPlaying
                    ? 'bg-red-100 hover:bg-red-200 text-red-700'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
                title={!showChinese ? 'Reveal Chinese first' : isPlaying ? 'Stop audio' : 'Play audio'}
              >
                <span className="text-lg">{isPlaying ? '⏹' : '▶'}</span>
                <span className="text-sm">{isPlaying ? 'Stop' : 'Play'}</span>
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
