import { useState, useEffect } from 'react'
import type { Word } from '../types'

interface Intervals {
  again: string
  hard: string
  good: string
  easy: string
}

interface WordPopupProps {
  word: Word
  position: { x: number; y: number }
  onReview: (ease: number) => void
  onClose: () => void
  getIntervals?: (cardId: number) => Promise<{ intervals: Intervals | null }>
}

const statusLabels = {
  new: 'New',
  due: 'Due Today',
  learned: 'Learned',
  unknown: 'Unknown',
}

const statusColors = {
  new: 'text-blue-600 bg-blue-50',
  due: 'text-orange-600 bg-orange-50',
  learned: 'text-green-600 bg-green-50',
  unknown: 'text-gray-500 bg-gray-50',
}

export function WordPopup({ word, position, onReview, onClose, getIntervals }: WordPopupProps) {
  const canReview = word.card_id !== null && (word.status === 'due' || word.status === 'new')
  const [intervals, setIntervals] = useState<Intervals | null>(null)

  useEffect(() => {
    if (canReview && word.card_id && getIntervals) {
      console.log('WordPopup: Fetching intervals for card:', word.card_id, 'word:', word.hanzi)
      getIntervals(word.card_id)
        .then(data => {
          console.log('WordPopup: Intervals response:', JSON.stringify(data, null, 2))
          console.log('WordPopup: Setting intervals to:', data.intervals)
          setIntervals(data.intervals)
        })
        .catch((err) => {
          console.error('WordPopup: Intervals fetch error:', err)
          setIntervals(null)
        })
    } else {
      console.log('WordPopup: Skipping intervals fetch - canReview:', canReview, 'card_id:', word.card_id, 'getIntervals:', !!getIntervals)
    }
  }, [canReview, word.card_id, getIntervals])

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
      />

      {/* Popup */}
      <div
        className="fixed z-50 bg-white rounded-lg shadow-xl border border-gray-200 p-4 min-w-64 max-w-sm"
        style={{
          left: Math.min(position.x, window.innerWidth - 280),
          top: Math.min(position.y + 10, window.innerHeight - 200),
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-2">
          <div>
            <span className="text-2xl chinese-text font-medium">{word.hanzi}</span>
            <span className="ml-2 text-gray-500 pinyin">{word.pinyin}</span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* Definition */}
        <p className="text-gray-700 mb-3">{word.definition || '(No definition)'}</p>

        {/* Status badge */}
        <div className="mb-3">
          <span className={`text-xs px-2 py-1 rounded ${statusColors[word.status]}`}>
            {statusLabels[word.status]}
          </span>
          {word.deck_name && (
            <span className="ml-2 text-xs text-gray-400">{word.deck_name}</span>
          )}
        </div>

        {/* Review buttons */}
        {canReview && (
          <div className="border-t pt-3">
            <p className="text-xs text-gray-500 mb-2">How well did you know this?</p>
            <div className="flex gap-2">
              <button
                onClick={() => onReview(1)}
                className="flex-1 py-1.5 px-2 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 flex flex-col items-center"
              >
                <span className="font-medium">{intervals?.again || 'Again'}</span>
              </button>
              <button
                onClick={() => onReview(2)}
                className="flex-1 py-1.5 px-2 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200 flex flex-col items-center"
              >
                <span className="font-medium">{intervals?.hard || 'Hard'}</span>
              </button>
              <button
                onClick={() => onReview(3)}
                className="flex-1 py-1.5 px-2 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 flex flex-col items-center"
              >
                <span className="font-medium">{intervals?.good || 'Good'}</span>
              </button>
              <button
                onClick={() => onReview(4)}
                className="flex-1 py-1.5 px-2 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 flex flex-col items-center"
              >
                <span className="font-medium">{intervals?.easy || 'Easy'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
