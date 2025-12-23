import { useState, useRef, useEffect } from 'react'
import { useAnki } from '../hooks/useAnki'
import { useTTS } from '../hooks/useTTS'
import { WordPopup } from './WordPopup'
import type { ChatMessage, Word } from '../types'

interface ChatViewProps {
  onBack: () => void
}

const wordStatusClass = {
  new: 'word-new cursor-pointer',
  due: 'word-due cursor-pointer',
  learned: 'word-learned',
  unknown: 'word-unknown',
}

export function ChatView({ onBack }: ChatViewProps) {
  const { sendChatMessage, submitReview, getCardIntervals, loading } = useAnki()
  const { speakWord, rate, setRate } = useTTS()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [showPinyin, setShowPinyin] = useState(true)
  const [showTranslation, setShowTranslation] = useState(false)
  const [selectedWord, setSelectedWord] = useState<Word | null>(null)
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!inputText.trim() || loading) return

    const messageText = inputText.trim()
    setInputText('')

    try {
      // Build history from existing messages
      const history = messages.map(msg => ({
        role: msg.role,
        text: msg.text
      }))

      const response = await sendChatMessage(messageText, history)

      // Add both messages to the chat
      setMessages(prev => [...prev, response.user_message, response.ai_message])
    } catch (err) {
      console.error('Failed to send message:', err)
      // Show error message in chat
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Sorry, I encountered an error. Please try again.',
        words: [],
        translation: undefined
      }])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleWordClick = (word: Word, event: React.MouseEvent) => {
    if (word.status === 'learned' && !word.definition) return

    const rect = (event.target as HTMLElement).getBoundingClientRect()
    setPopupPosition({ x: rect.left, y: rect.bottom })
    setSelectedWord(word)
    speakWord(word.hanzi)
  }

  const handleReview = async (ease: number) => {
    if (selectedWord?.card_id) {
      await submitReview(selectedWord.card_id, ease)
      setSelectedWord(null)
    }
  }

  const handlePlayMessage = (message: ChatMessage) => {
    if (message.role === 'assistant') {
      speakWord(message.text)
    }
  }

  // Render words with pinyin (for AI messages)
  const renderWords = (words: Word[]) => {
    return words.map((word, idx) => {
      const isPunctuation = /^[\s\p{P}]+$/u.test(word.hanzi)

      if (isPunctuation) {
        return <span key={idx}>{word.hanzi}</span>
      }

      return (
        <ruby
          key={idx}
          className={`${wordStatusClass[word.status]} transition-all`}
          onClick={(e) => handleWordClick(word, e)}
        >
          {word.hanzi}
          {showPinyin && <rp>(</rp>}
          {showPinyin && <rt className="pinyin">{word.pinyin}</rt>}
          {showPinyin && <rp>)</rp>}
        </ruby>
      )
    })
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-4">
          <button
            onClick={onBack}
            className="text-gray-500 hover:text-gray-700"
          >
            &larr; Back
          </button>
          <h1 className="font-bold flex-1">Chat with AI</h1>
        </div>
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <p className="text-lg mb-2">Start a conversation!</p>
              <p className="text-sm">Type in Chinese and I'll respond using your vocabulary.</p>
            </div>
          )}

          {messages.map((message, idx) => (
            <div
              key={idx}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white rounded-br-md'
                    : 'bg-white shadow-sm rounded-bl-md'
                }`}
              >
                {message.role === 'user' ? (
                  // User message - plain text
                  <div className="chinese-text">{message.text}</div>
                ) : (
                  // AI message - with word breakdown
                  <div>
                    {/* Chinese with pinyin */}
                    <div className="chinese-text text-lg leading-relaxed">
                      {renderWords(message.words)}
                    </div>

                    {/* Translation */}
                    {showTranslation && message.translation && (
                      <div className="text-gray-500 text-sm mt-2 pt-2 border-t border-gray-100 italic">
                        {message.translation}
                      </div>
                    )}

                    {/* Play button */}
                    <button
                      onClick={() => handlePlayMessage(message)}
                      className="mt-2 text-gray-400 hover:text-gray-600 text-sm flex items-center gap-1"
                    >
                      <span>&#128266;</span>
                      <span>Play</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white shadow-sm rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Controls bar */}
      <div className="bg-white border-t border-b">
        <div className="max-w-2xl mx-auto px-4 py-2 flex items-center gap-4 text-sm">
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              checked={showPinyin}
              onChange={(e) => setShowPinyin(e.target.checked)}
              className="h-3 w-3"
            />
            <span className="text-xs text-gray-600">Pinyin</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              checked={showTranslation}
              onChange={(e) => setShowTranslation(e.target.checked)}
              className="h-3 w-3"
            />
            <span className="text-xs text-gray-600">Translation</span>
          </label>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">{rate.toFixed(1)}x</span>
            <input
              type="range"
              min="0.5"
              max="1"
              step="0.1"
              value={rate}
              onChange={(e) => setRate(parseFloat(e.target.value))}
              className="w-16 h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Input area */}
      <div className="bg-white border-t sticky bottom-0">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type in Chinese..."
              rows={1}
              className="flex-1 px-4 py-2 border rounded-full resize-none chinese-text focus:outline-none focus:ring-2 focus:ring-blue-500"
              style={{ minHeight: '40px', maxHeight: '120px' }}
            />
            <button
              onClick={handleSend}
              disabled={!inputText.trim() || loading}
              className="px-6 py-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Word popup */}
      {selectedWord && (
        <WordPopup
          key={`${selectedWord.hanzi}-${selectedWord.card_id}`}
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
