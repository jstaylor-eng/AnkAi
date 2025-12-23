import type { VocabStats } from '../types'

interface FeatureCard {
  id: string
  title: string
  description: string
  icon: string
  enabled: boolean
}

const FEATURE_CARDS: FeatureCard[] = [
  { id: 'read', title: 'Read Articles', description: 'Practice with news & stories', icon: '📖', enabled: true },
  { id: 'chat', title: 'Chat with AI', description: 'Conversation practice', icon: '💬', enabled: false },
  { id: 'recall', title: 'Recall Practice', description: 'English → Chinese drills', icon: '🔄', enabled: false },
]

interface LandingPageProps {
  vocabStats: VocabStats
  selectedDecks: string[]
  onSelectMode: (mode: string) => void
  onChangeDecks: () => void
  onSync: () => void
}

export function LandingPage({ vocabStats, selectedDecks, onSelectMode, onChangeDecks, onSync }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center">
          <h1 className="text-3xl font-bold text-gray-900">AnkAi</h1>
          <p className="text-gray-500 mt-1">Learn Chinese Your Way</p>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-4xl mx-auto px-4 py-8 w-full">
        {/* Feature cards grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURE_CARDS.map((card) => (
            <button
              key={card.id}
              onClick={() => card.enabled && onSelectMode(card.id)}
              disabled={!card.enabled}
              className={`
                relative p-6 rounded-xl text-left transition-all
                ${card.enabled
                  ? 'bg-white shadow-sm hover:shadow-md hover:scale-[1.02] cursor-pointer'
                  : 'bg-gray-100 opacity-60 cursor-not-allowed'
                }
              `}
            >
              {/* Coming Soon badge */}
              {!card.enabled && (
                <span className="absolute top-3 right-3 text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full">
                  Coming Soon
                </span>
              )}

              {/* Icon */}
              <div className="text-4xl mb-3">{card.icon}</div>

              {/* Title */}
              <h2 className="text-lg font-semibold text-gray-900">{card.title}</h2>

              {/* Description */}
              <p className="text-sm text-gray-500 mt-1">{card.description}</p>
            </button>
          ))}
        </div>

        {/* Stats footer */}
        <div className="mt-8 bg-white rounded-xl shadow-sm p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Decks:</span>{' '}
              <span className="text-gray-900">{selectedDecks.join(', ')}</span>
              <span className="mx-2 text-gray-300">|</span>
              <span className="font-medium">{vocabStats.total.toLocaleString()}</span> words loaded
              <span className="text-gray-400 ml-1">
                ({vocabStats.due} due, {vocabStats.new} new)
              </span>
            </div>
            <div className="flex gap-3">
              <button
                onClick={onSync}
                className="text-sm text-gray-600 hover:text-gray-800"
              >
                Sync
              </button>
              <button
                onClick={onChangeDecks}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Change Decks
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
