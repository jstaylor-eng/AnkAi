import { useState } from 'react'
import type { ProcessedArticle, Word } from '../types'
import { WordPopup } from './WordPopup'
import { useTTS } from '../hooks/useTTS'

interface Intervals {
  again: string
  hard: string
  good: string
  easy: string
}

interface ReaderProps {
  article: ProcessedArticle
  onReview: (cardId: number, ease: number) => Promise<void>
  getCardIntervals?: (cardId: number) => Promise<{ intervals: Intervals | null }>
}

const wordStatusClass = {
  new: 'word-new cursor-pointer',
  due: 'word-due cursor-pointer',
  learned: 'word-learned',
  unknown: 'word-unknown',
}

export function Reader({ article, onReview, getCardIntervals }: ReaderProps) {
  const [selectedWord, setSelectedWord] = useState<Word | null>(null)
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 })
  const [showPinyin, setShowPinyin] = useState(true)
  const [showTranslation, setShowTranslation] = useState(true)
  const [showOriginal, setShowOriginal] = useState(false)

  const {
    isPlaying,
    currentSentenceIndex,
    currentWordIndex,
    rate,
    speak,
    pause,
    resume,
    stop,
    setRate,
    speakWord,
  } = useTTS()

  const handleWordClick = (word: Word, event: React.MouseEvent) => {
    if (word.status === 'learned' && !word.definition) return

    const rect = (event.target as HTMLElement).getBoundingClientRect()
    setPopupPosition({ x: rect.left, y: rect.bottom })
    setSelectedWord(word)
  }

  const handleReview = async (ease: number) => {
    if (selectedWord?.card_id) {
      await onReview(selectedWord.card_id, ease)
      setSelectedWord(null)
    }
  }

  const handlePlayPause = () => {
    if (isPlaying) {
      pause()
    } else if (currentSentenceIndex >= 0) {
      resume()
    } else {
      // Start from beginning
      speak(article.sentences.map(s => ({
        text: s.simplified,
        words: s.words
      })))
    }
  }

  const handlePlaySentence = (sentenceIndex: number) => {
    stop()
    speak(
      article.sentences.map(s => ({ text: s.simplified, words: s.words })),
      sentenceIndex
    )
  }

  const handleStop = () => {
    stop()
  }

  // Check if a word should be highlighted
  const isWordHighlighted = (sentenceIdx: number, wordIdx: number) => {
    return currentSentenceIndex === sentenceIdx && currentWordIndex === wordIdx
  }

  const isSentenceActive = (sentenceIdx: number) => {
    return currentSentenceIndex === sentenceIdx
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Stats bar */}
      <div className="bg-gray-50 rounded-lg p-3 mb-4 text-sm">
        <div className="flex items-center gap-4 mb-2">
          <span className="text-gray-600">
            Comprehension: <strong>{article.stats.comprehension_percent}%</strong>
          </span>
          <span className="text-orange-600">
            Due: <strong>{article.stats.due_count}</strong>
          </span>
          <span className="text-blue-600">
            New: <strong>{article.stats.new_count}</strong>
          </span>
          <div className="flex-1" />
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              checked={showPinyin}
              onChange={(e) => setShowPinyin(e.target.checked)}
              className="h-3 w-3"
            />
            <span className="text-xs">Pinyin</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              checked={showTranslation}
              onChange={(e) => setShowTranslation(e.target.checked)}
              className="h-3 w-3"
            />
            <span className="text-xs">Translation</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              checked={showOriginal}
              onChange={(e) => setShowOriginal(e.target.checked)}
              className="h-3 w-3"
            />
            <span className="text-xs">Original</span>
          </label>
        </div>

        {/* TTS Controls */}
        <div className="flex items-center gap-3 pt-2 border-t border-gray-200">
          <button
            onClick={handlePlayPause}
            className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-500 text-white hover:bg-blue-600 transition-colors"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
              </svg>
            ) : (
              <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
            )}
          </button>

          {isPlaying && (
            <button
              onClick={handleStop}
              className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 text-gray-600 hover:bg-gray-300 transition-colors"
              title="Stop"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 6h12v12H6z"/>
              </svg>
            </button>
          )}

          <div className="flex items-center gap-2 flex-1">
            <span className="text-xs text-gray-500 w-10">{rate.toFixed(1)}x</span>
            <input
              type="range"
              min="0.5"
              max="1.0"
              step="0.1"
              value={rate}
              onChange={(e) => setRate(parseFloat(e.target.value))}
              className="flex-1 h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <span className="text-xs text-gray-400">Speed</span>
          </div>
        </div>
      </div>

      {/* Sentences */}
      <div className="space-y-6">
        {article.sentences.map((sentence, sIdx) => (
          <div
            key={sIdx}
            className={`leading-relaxed p-2 -mx-2 rounded-lg transition-colors ${
              isSentenceActive(sIdx) ? 'bg-blue-50' : ''
            }`}
          >
            {/* Chinese with pinyin */}
            <div className="chinese-text text-xl flex items-start gap-1">
              {/* Play sentence button */}
              <button
                onClick={() => handlePlaySentence(sIdx)}
                className="flex-shrink-0 mt-1 w-6 h-6 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 hover:text-gray-700 flex items-center justify-center transition-colors"
                title="Play this sentence"
              >
                <svg className="w-3 h-3 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </button>

              <div className="flex-1">
                {sentence.words.map((word, wIdx) => {
                  const isPunctuation = /^[\s\p{P}]+$/u.test(word.hanzi)

                  if (isPunctuation) {
                    return <span key={wIdx}>{word.hanzi}</span>
                  }

                  const highlighted = isWordHighlighted(sIdx, wIdx)

                  return (
                    <ruby
                      key={wIdx}
                      className={`${wordStatusClass[word.status]} ${
                        highlighted ? 'tts-highlight' : ''
                      } transition-all`}
                      onClick={(e) => {
                        speakWord(word.hanzi)
                        handleWordClick(word, e)
                      }}
                    >
                      {word.hanzi}
                      {showPinyin && <rp>(</rp>}
                      {showPinyin && <rt className="pinyin">{word.pinyin}</rt>}
                      {showPinyin && <rp>)</rp>}
                    </ruby>
                  )
                })}
              </div>
            </div>

            {/* Original text (if different from simplified) */}
            {showOriginal && sentence.original !== sentence.simplified && (
              <p className="text-gray-400 text-sm mt-1 chinese-text ml-7">
                <span className="text-gray-500 text-xs mr-1">Original:</span>
                {sentence.original}
              </p>
            )}

            {/* Translation */}
            {showTranslation && sentence.translation && (
              <p className="text-gray-500 text-sm mt-1 italic ml-7">
                {sentence.translation}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Word popup */}
      {selectedWord && (
        <WordPopup
          word={selectedWord}
          position={popupPosition}
          onReview={handleReview}
          onClose={() => setSelectedWord(null)}
          getIntervals={getCardIntervals}
        />
      )}
    </div>
  )
}
