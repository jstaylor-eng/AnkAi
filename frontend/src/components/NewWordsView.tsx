import { useState, useEffect, useCallback } from 'react'
import { useAnki } from '../hooks/useAnki'

interface NewWordsViewProps {
  onBack: () => void
}

interface WordContent {
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
}

type ViewState = 'setup' | 'learning'

export function NewWordsView({ onBack }: NewWordsViewProps) {
  const { introduceNewWord, submitReview, getCardIntervals, loading } = useAnki()

  // Setup state
  const [viewState, setViewState] = useState<ViewState>('setup')
  const [reviewWord, setReviewWord] = useState('')

  // Learning state
  const [content, setContent] = useState<WordContent | null>(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [showChinese, setShowChinese] = useState(false)
  const [showPinyin, setShowPinyin] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [intervals, setIntervals] = useState<{ again: string; hard: string; good: string; easy: string } | null>(null)
  const [reviewSubmitted, setReviewSubmitted] = useState(false)

  // Audio state
  const [isPlaying, setIsPlaying] = useState(false)
  const [rate, setRate] = useState(0.8)

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

  const loadWord = async (word?: string) => {
    setLoadError(null)
    stopAudio()
    setReviewSubmitted(false)
    try {
      const result = await introduceNewWord(word)
      setContent(result)
      setCurrentStep(0)
      setShowChinese(false)
      setShowPinyin(false)
      setViewState('learning')

      // Load intervals if we have a card ID
      if (result.card_id) {
        try {
          const intervalResult = await getCardIntervals(result.card_id)
          if (intervalResult.intervals) {
            setIntervals(intervalResult.intervals)
          }
        } catch {
          // Intervals are optional
        }
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load word')
    }
  }

  const handleIntroduceNew = () => {
    loadWord()
  }

  const handleReviewWord = () => {
    if (reviewWord.trim()) {
      loadWord(reviewWord.trim())
    }
  }

  const handleBackToSetup = () => {
    stopAudio()
    setViewState('setup')
    setContent(null)
    setCurrentStep(0)
    setShowChinese(false)
    setShowPinyin(false)
  }

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep(currentStep + 1)
      setShowChinese(false)
      setShowPinyin(false)
      stopAudio()
    }
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
      setShowChinese(false)
      setShowPinyin(false)
      stopAudio()
    }
  }

  const handlePlayAudio = (text: string) => {
    if (isPlaying) {
      stopAudio()
    } else {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'zh-CN'
      utterance.rate = rate

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

  const handleReview = async (ease: number) => {
    if (!content?.card_id || reviewSubmitted) return

    try {
      await submitReview(content.card_id, ease)
      setReviewSubmitted(true)
    } catch (err) {
      console.error('Review error:', err)
    }
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
            <h1 className="font-bold">New Words</h1>
          </div>
        </header>

        <main className="max-w-2xl mx-auto p-4">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-medium mb-2">Learn New Vocabulary</h2>
            <p className="text-sm text-gray-500 mb-6">
              Introduce new words with examples and recall practice
            </p>

            {/* Error message */}
            {loadError && (
              <div className="text-red-600 text-sm mb-4">{loadError}</div>
            )}

            {/* Introduce new word button */}
            <button
              onClick={handleIntroduceNew}
              disabled={loading}
              className="w-full py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium mb-6"
            >
              {loading ? 'Loading...' : 'Introduce a New Word'}
            </button>

            {/* Divider */}
            <div className="flex items-center gap-4 mb-6">
              <div className="flex-1 h-px bg-gray-200"></div>
              <span className="text-sm text-gray-400">or</span>
              <div className="flex-1 h-px bg-gray-200"></div>
            </div>

            {/* Review specific word */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Review a Specific Word
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={reviewWord}
                  onChange={(e) => setReviewWord(e.target.value)}
                  placeholder="Enter Chinese word..."
                  className="flex-1 p-3 border rounded-lg chinese-text"
                  onKeyDown={(e) => e.key === 'Enter' && handleReviewWord()}
                />
                <button
                  onClick={handleReviewWord}
                  disabled={loading || !reviewWord.trim()}
                  className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                  Go
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Loading state
  if (loading && !content) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-500 mb-2">Loading word content...</div>
        </div>
      </div>
    )
  }

  if (!content) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">No content available</div>
      </div>
    )
  }

  const stepLabels = ['Word', 'Example 1', 'Example 2', 'Recall 1', 'Recall 2']

  // Get current example or recall sentence
  const currentExample = currentStep === 1 ? content.example_sentences[0]
                       : currentStep === 2 ? content.example_sentences[1]
                       : null
  const currentRecall = currentStep === 3 ? content.recall_sentences[0]
                      : currentStep === 4 ? content.recall_sentences[1]
                      : null

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-4">
          <button
            onClick={handleBackToSetup}
            className="text-gray-500 hover:text-gray-700"
          >
            &larr; Back
          </button>
          <div className="flex-1">
            <h1 className="font-bold">New Words</h1>
            <p className="text-xs text-gray-500">
              Learning: {content.word.hanzi}
            </p>
          </div>
        </div>
      </header>

      {/* Progress dots */}
      <div className="bg-white border-b py-2">
        <div className="max-w-2xl mx-auto px-4">
          <div className="flex justify-between items-center">
            {stepLabels.map((label, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setCurrentStep(idx)
                  setShowChinese(false)
                  setShowPinyin(false)
                  stopAudio()
                }}
                className={`flex flex-col items-center gap-1 ${
                  idx === currentStep ? 'text-blue-600' : 'text-gray-400'
                }`}
              >
                <div
                  className={`w-3 h-3 rounded-full transition-colors ${
                    idx === currentStep
                      ? 'bg-blue-600'
                      : idx < currentStep
                      ? 'bg-blue-300'
                      : 'bg-gray-300'
                  }`}
                />
                <span className="text-xs">{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main content */}
      <main className="max-w-2xl mx-auto p-4">
        <div className="bg-white rounded-xl shadow-sm p-6">
          {/* Step 0: Word Display */}
          {currentStep === 0 && (
            <div className="text-center">
              <div className="text-5xl chinese-text mb-4">{content.word.hanzi}</div>
              <div className="text-xl text-gray-600 mb-2">{content.word.pinyin}</div>
              <div className="text-lg text-gray-800">{content.word.definition}</div>

              <button
                onClick={() => handlePlayAudio(content.word.hanzi)}
                className={`mt-6 flex items-center gap-2 mx-auto px-4 py-2 rounded-lg transition-colors ${
                  isPlaying
                    ? 'bg-red-100 hover:bg-red-200 text-red-700'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                <span className="text-lg">{isPlaying ? '⏹' : '▶'}</span>
                <span className="text-sm">{isPlaying ? 'Stop' : 'Play'}</span>
              </button>
            </div>
          )}

          {/* Steps 1-2: Example Sentences */}
          {currentExample && (
            <div>
              <div className="text-sm text-gray-500 mb-3">Example sentence:</div>

              {/* Chinese sentence */}
              <div className="text-2xl chinese-text leading-relaxed mb-4 p-4 bg-blue-50 rounded-lg">
                {showPinyin ? (
                  currentExample.chinese.split('').map((char: string, idx: number) => {
                    const pinyinParts = currentExample.pinyin.split(/\s+/)
                    if (/[\u4e00-\u9fff]/.test(char)) {
                      const py = pinyinParts[idx] || ''
                      return (
                        <ruby key={idx} className="mx-0.5">
                          {char}
                          <rp>(</rp>
                          <rt className="text-xs text-gray-500 font-normal">{py}</rt>
                          <rp>)</rp>
                        </ruby>
                      )
                    }
                    return <span key={idx}>{char}</span>
                  })
                ) : (
                  currentExample.chinese
                )}
              </div>

              {/* English translation */}
              <div className="text-gray-700 mb-4">{currentExample.english}</div>

              {/* Word highlight */}
              <div className="text-sm text-blue-600 bg-blue-50 p-3 rounded-lg">
                <strong>{content.word.hanzi}</strong>: {currentExample.word_highlight}
              </div>

              {/* Controls */}
              <div className="flex items-center gap-4 mt-6">
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
                  onClick={() => handlePlayAudio(currentExample.chinese)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                    isPlaying
                      ? 'bg-red-100 hover:bg-red-200 text-red-700'
                      : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                  }`}
                >
                  <span className="text-lg">{isPlaying ? '⏹' : '▶'}</span>
                  <span className="text-sm">{isPlaying ? 'Stop' : 'Play'}</span>
                </button>
              </div>
            </div>
          )}

          {/* Steps 3-4: Recall Sentences */}
          {currentRecall && (
            <div>
              <div className="text-sm text-gray-500 mb-3">Recall this in Chinese:</div>

              {/* English prompt */}
              <div className="text-lg text-gray-900 mb-6 p-4 bg-amber-50 rounded-lg border border-amber-100">
                {currentRecall.english}
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
                >
                  {showPinyin ? 'Hide Pinyin' : 'Pinyin'}
                </button>
              </div>

              {/* Revealed Chinese */}
              {showChinese && (
                <div className="p-4 bg-green-50 rounded-lg border border-green-100 mb-6">
                  <div className="text-sm text-green-700 mb-2">Chinese:</div>
                  <div className="text-2xl chinese-text leading-loose">
                    {showPinyin ? (
                      currentRecall.chinese.split('').map((char: string, idx: number) => {
                        const pinyinParts = currentRecall.pinyin.split(/\s+/)
                        if (/[\u4e00-\u9fff]/.test(char)) {
                          const py = pinyinParts[idx] || ''
                          return (
                            <ruby key={idx} className="mx-0.5">
                              {char}
                              <rp>(</rp>
                              <rt className="text-xs text-gray-500 font-normal">{py}</rt>
                              <rp>)</rp>
                            </ruby>
                          )
                        }
                        return <span key={idx}>{char}</span>
                      })
                    ) : (
                      currentRecall.chinese
                    )}
                  </div>
                </div>
              )}

              {/* Audio control */}
              {showChinese && (
                <div className="flex items-center gap-4 mb-6">
                  <button
                    onClick={() => handlePlayAudio(currentRecall.chinese)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      isPlaying
                        ? 'bg-red-100 hover:bg-red-200 text-red-700'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                    }`}
                  >
                    <span className="text-lg">{isPlaying ? '⏹' : '▶'}</span>
                    <span className="text-sm">{isPlaying ? 'Stop' : 'Play'}</span>
                  </button>
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
                </div>
              )}

              {/* Review buttons (only on last step with card) */}
              {currentStep === 4 && content.card_id && showChinese && (
                <div className="border-t pt-6">
                  <div className="text-sm text-gray-500 mb-3 text-center">
                    {reviewSubmitted ? 'Review submitted!' : 'How well did you remember?'}
                  </div>
                  {!reviewSubmitted ? (
                    <div className="grid grid-cols-4 gap-2">
                      <button
                        onClick={() => handleReview(1)}
                        className="py-3 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                      >
                        <div className="font-medium">Again</div>
                        <div className="text-xs opacity-75">{intervals?.again || ''}</div>
                      </button>
                      <button
                        onClick={() => handleReview(2)}
                        className="py-3 bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 transition-colors"
                      >
                        <div className="font-medium">Hard</div>
                        <div className="text-xs opacity-75">{intervals?.hard || ''}</div>
                      </button>
                      <button
                        onClick={() => handleReview(3)}
                        className="py-3 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                      >
                        <div className="font-medium">Good</div>
                        <div className="text-xs opacity-75">{intervals?.good || ''}</div>
                      </button>
                      <button
                        onClick={() => handleReview(4)}
                        className="py-3 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                      >
                        <div className="font-medium">Easy</div>
                        <div className="text-xs opacity-75">{intervals?.easy || ''}</div>
                      </button>
                    </div>
                  ) : (
                    <div className="text-center text-green-600 font-medium">
                      Review recorded!
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        <div className="flex justify-between mt-4">
          <button
            onClick={handlePrev}
            disabled={currentStep === 0}
            className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>

          {currentStep < 4 ? (
            <button
              onClick={handleNext}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleIntroduceNew}
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Loading...' : 'Next Word'}
            </button>
          )}
        </div>
      </main>
    </div>
  )
}
