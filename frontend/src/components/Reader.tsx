import { useState } from 'react'
import type { ProcessedArticle, Word } from '../types'
import { WordPopup } from './WordPopup'

interface ReaderProps {
  article: ProcessedArticle
  onReview: (cardId: number, ease: number) => Promise<void>
}

const wordStatusClass = {
  new: 'word-new cursor-pointer',
  due: 'word-due cursor-pointer',
  learned: 'word-learned',
  unknown: 'word-unknown',
}

export function Reader({ article, onReview }: ReaderProps) {
  const [selectedWord, setSelectedWord] = useState<Word | null>(null)
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 })
  const [showPinyin, setShowPinyin] = useState(true)
  const [showTranslation, setShowTranslation] = useState(true)
  const [showOriginal, setShowOriginal] = useState(false)

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

  return (
    <div className="max-w-2xl mx-auto">
      {/* Stats bar */}
      <div className="bg-gray-50 rounded-lg p-3 mb-4 flex items-center gap-4 text-sm">
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

      {/* Sentences */}
      <div className="space-y-6">
        {article.sentences.map((sentence, sIdx) => (
          <div key={sIdx} className="leading-relaxed">
            {/* Chinese with pinyin */}
            <div className="chinese-text text-xl">
              {sentence.words.map((word, wIdx) => {
                const isPunctuation = /^[\s\p{P}]+$/u.test(word.hanzi)

                if (isPunctuation) {
                  return <span key={wIdx}>{word.hanzi}</span>
                }

                return (
                  <ruby
                    key={wIdx}
                    className={wordStatusClass[word.status]}
                    onClick={(e) => handleWordClick(word, e)}
                  >
                    {word.hanzi}
                    {showPinyin && (
                      <rp>(</rp>
                    )}
                    {showPinyin && (
                      <rt className="pinyin">{word.pinyin}</rt>
                    )}
                    {showPinyin && (
                      <rp>)</rp>
                    )}
                  </ruby>
                )
              })}
            </div>

            {/* Original text (if different from simplified) */}
            {showOriginal && sentence.original !== sentence.simplified && (
              <p className="text-gray-400 text-sm mt-1 chinese-text">
                <span className="text-gray-500 text-xs mr-1">Original:</span>
                {sentence.original}
              </p>
            )}

            {/* Translation */}
            {showTranslation && sentence.translation && (
              <p className="text-gray-500 text-sm mt-1 italic">
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
        />
      )}
    </div>
  )
}
