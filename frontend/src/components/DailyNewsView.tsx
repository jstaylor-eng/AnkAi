import { useState, useEffect, useCallback } from 'react'
import { useAnki } from '../hooks/useAnki'

interface DailyNewsViewProps {
  onBack: () => void
}

interface Headline {
  original: string
  description: string
  link: string
  pubDate: string
  chinese: string
  pinyin: string
}

interface NewsData {
  headlines: Headline[]
  source: string
  fetch_time: string
}

export function DailyNewsView({ onBack }: DailyNewsViewProps) {
  const { getNewsHeadlines, loading } = useAnki()

  const [newsData, setNewsData] = useState<NewsData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)
  const [showPinyin, setShowPinyin] = useState(false)

  const loadHeadlines = useCallback(async () => {
    setLoadError(null)
    try {
      const result = await getNewsHeadlines()
      setNewsData(result)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load headlines')
    }
  }, [getNewsHeadlines])

  useEffect(() => {
    loadHeadlines()
  }, [loadHeadlines])

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  const renderChineseWithPinyin = (chinese: string, pinyin: string) => {
    if (!showPinyin) {
      return <span className="chinese-text">{chinese}</span>
    }

    // Split pinyin by spaces to match characters
    const pinyinParts = pinyin.split(/\s+/)
    const chars = chinese.split('')

    return (
      <span className="chinese-text">
        {chars.map((char, idx) => {
          // Skip punctuation for pinyin
          if (/[，。！？、：；""''（）\s]/.test(char)) {
            return <span key={idx}>{char}</span>
          }
          const py = pinyinParts[idx] || ''
          return (
            <ruby key={idx} className="mx-0.5">
              {char}
              <rp>(</rp>
              <rt className="text-xs text-gray-500 font-normal">{py}</rt>
              <rp>)</rp>
            </ruby>
          )
        })}
      </span>
    )
  }

  // Loading state
  if (loading && !newsData) {
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
            <h1 className="font-bold">Daily News</h1>
          </div>
        </header>
        <main className="max-w-2xl mx-auto p-4">
          <div className="text-center py-12 text-gray-500">
            Loading headlines...
          </div>
        </main>
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
            <h1 className="font-bold">Daily News</h1>
            {newsData && (
              <p className="text-xs text-gray-500">
                {newsData.source} - {formatDate(newsData.fetch_time)}
              </p>
            )}
          </div>
          <button
            onClick={() => setShowPinyin(!showPinyin)}
            className={`px-3 py-1 text-sm rounded-lg transition-colors ${
              showPinyin
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {showPinyin ? 'Hide Pinyin' : 'Pinyin'}
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto p-4">
        {/* Error message */}
        {loadError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <div className="text-red-700 font-medium">Error loading headlines</div>
            <div className="text-red-600 text-sm mt-1">{loadError}</div>
            <button
              onClick={loadHeadlines}
              className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
            >
              Retry
            </button>
          </div>
        )}

        {/* Headlines list */}
        {newsData && newsData.headlines.length > 0 && (
          <div className="space-y-3">
            {newsData.headlines.map((headline, index) => (
              <div
                key={index}
                className="bg-white rounded-xl shadow-sm overflow-hidden"
              >
                {/* Headline card */}
                <button
                  onClick={() => setExpandedIndex(expandedIndex === index ? null : index)}
                  className="w-full text-left p-4 hover:bg-gray-50 transition-colors"
                >
                  {/* Chinese translation */}
                  <div className="text-lg leading-relaxed mb-2">
                    {renderChineseWithPinyin(headline.chinese, headline.pinyin)}
                  </div>

                  {/* Original headline */}
                  <div className="text-sm text-gray-500">
                    {headline.original}
                  </div>

                  {/* Timestamp */}
                  <div className="text-xs text-gray-400 mt-2">
                    {formatDate(headline.pubDate)}
                  </div>
                </button>

                {/* Expanded content */}
                {expandedIndex === index && (
                  <div className="border-t bg-gray-50 p-4">
                    {/* Description */}
                    {headline.description && (
                      <div className="text-sm text-gray-600 mb-3">
                        {headline.description}
                      </div>
                    )}

                    {/* Link to full article */}
                    <a
                      href={headline.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
                    >
                      Read full article
                      <span className="text-xs">↗</span>
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {newsData && newsData.headlines.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No headlines available
          </div>
        )}

        {/* Refresh button */}
        {newsData && (
          <div className="mt-6 text-center">
            <button
              onClick={loadHeadlines}
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Refreshing...' : 'Refresh Headlines'}
            </button>
          </div>
        )}

        {/* Info tip */}
        <div className="mt-4 p-4 bg-amber-50 rounded-lg text-sm text-amber-800 border border-amber-100">
          <strong>Tip:</strong> Headlines are translated using your known vocabulary.
          Tap a headline to see the description and link to the full article.
        </div>
      </main>
    </div>
  )
}
