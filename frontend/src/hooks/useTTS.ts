import { useState, useEffect, useCallback, useRef } from 'react'

export interface TTSState {
  isPlaying: boolean
  currentSentenceIndex: number
  currentWordIndex: number
  rate: number
}

export function useTTS() {
  const [state, setState] = useState<TTSState>({
    isPlaying: false,
    currentSentenceIndex: -1,
    currentWordIndex: -1,
    rate: 0.8,
  })

  const rateRef = useRef(state.rate)
  const sentencesRef = useRef<{ words: { hanzi: string }[] }[]>([])
  const queueIndexRef = useRef(0)
  const stoppedRef = useRef(false)
  const wordTimersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  // Learn actual speech rate from completed sentences
  const learnedMsPerCharRef = useRef<number | null>(null)
  const sentenceStartTimeRef = useRef<number>(0)

  useEffect(() => {
    rateRef.current = state.rate
    // Reset learned rate when speed changes
    learnedMsPerCharRef.current = null
  }, [state.rate])

  const getChineseVoice = useCallback(() => {
    const voices = speechSynthesis.getVoices()
    const preferredVoices = [
      'Microsoft Xiaoxiao Online (Natural)',
      'Google 普通话（中国大陆）',
      'Ting-Ting',
    ]
    for (const preferred of preferredVoices) {
      const voice = voices.find(v => v.name.includes(preferred))
      if (voice) return voice
    }
    return voices.find(v =>
      v.lang.includes('zh') || v.lang.includes('cmn') || v.name.toLowerCase().includes('chinese')
    ) || null
  }, [])

  const clearTimers = useCallback(() => {
    wordTimersRef.current.forEach(t => clearTimeout(t))
    wordTimersRef.current = []
  }, [])

  const scheduleWordHighlights = useCallback((
    words: { hanzi: string }[],
    sentenceIdx: number,
    msPerChar: number
  ) => {
    clearTimers()

    let charsSoFar = 0
    words.forEach((word, wordIdx) => {
      const delay = charsSoFar * msPerChar
      const timer = setTimeout(() => {
        if (!stoppedRef.current) {
          setState(s => ({ ...s, currentSentenceIndex: sentenceIdx, currentWordIndex: wordIdx }))
        }
      }, delay)
      wordTimersRef.current.push(timer)
      charsSoFar += word.hanzi.length
    })
  }, [clearTimers])

  const speakSentence = useCallback((sentenceIdx: number) => {
    if (stoppedRef.current) return

    const sentences = sentencesRef.current
    if (sentenceIdx >= sentences.length) {
      setState(s => ({
        ...s,
        isPlaying: false,
        currentSentenceIndex: -1,
        currentWordIndex: -1
      }))
      return
    }

    const sentence = sentences[sentenceIdx]
    const words = sentence.words
    const text = words.map(w => w.hanzi).join('')
    const totalChars = text.length

    // Use learned rate or default estimate
    // Default: ~280ms per char at rate 1.0, adjusted for current rate
    const defaultMsPerChar = 280 / rateRef.current
    const msPerChar = learnedMsPerCharRef.current ?? defaultMsPerChar

    // Schedule word highlights
    scheduleWordHighlights(words, sentenceIdx, msPerChar)
    setState(s => ({ ...s, currentSentenceIndex: sentenceIdx, currentWordIndex: 0 }))

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    utterance.rate = rateRef.current

    const voice = getChineseVoice()
    if (voice) utterance.voice = voice

    utterance.onstart = () => {
      sentenceStartTimeRef.current = Date.now()
    }

    utterance.onend = () => {
      if (stoppedRef.current) return

      // Learn actual speech rate from this sentence
      const actualDuration = Date.now() - sentenceStartTimeRef.current
      if (totalChars > 0 && actualDuration > 0) {
        const actualMsPerChar = actualDuration / totalChars
        // Smooth the learning with previous value
        if (learnedMsPerCharRef.current) {
          learnedMsPerCharRef.current = (learnedMsPerCharRef.current + actualMsPerChar) / 2
        } else {
          learnedMsPerCharRef.current = actualMsPerChar
        }
      }

      clearTimers()
      queueIndexRef.current++
      setTimeout(() => speakSentence(queueIndexRef.current), 300)
    }

    utterance.onerror = (event) => {
      clearTimers()
      if (event.error !== 'interrupted') {
        console.error('TTS error:', event.error)
      }
      setState(s => ({
        ...s,
        isPlaying: false,
        currentSentenceIndex: -1,
        currentWordIndex: -1
      }))
    }

    speechSynthesis.speak(utterance)
  }, [getChineseVoice, clearTimers, scheduleWordHighlights])

  const speak = useCallback((
    sentences: { text: string; words: { hanzi: string }[] }[],
    startIndex = 0
  ) => {
    speechSynthesis.cancel()
    clearTimers()
    stoppedRef.current = false
    sentencesRef.current = sentences
    queueIndexRef.current = startIndex
    setState(s => ({ ...s, isPlaying: true }))
    speakSentence(startIndex)
  }, [speakSentence, clearTimers])

  const pause = useCallback(() => {
    speechSynthesis.pause()
    clearTimers()
    setState(s => ({ ...s, isPlaying: false }))
  }, [clearTimers])

  const resume = useCallback(() => {
    speechSynthesis.resume()
    setState(s => ({ ...s, isPlaying: true }))
    // Note: highlighting won't resume properly, but that's a limitation
  }, [])

  const stop = useCallback(() => {
    stoppedRef.current = true
    speechSynthesis.cancel()
    clearTimers()
    setState(s => ({
      ...s,
      isPlaying: false,
      currentSentenceIndex: -1,
      currentWordIndex: -1
    }))
  }, [clearTimers])

  const setRate = useCallback((rate: number) => {
    setState(s => ({ ...s, rate }))
  }, [])

  const speakWord = useCallback((text: string) => {
    if (speechSynthesis.speaking && state.currentSentenceIndex >= 0) return
    speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    utterance.rate = rateRef.current
    const voice = getChineseVoice()
    if (voice) utterance.voice = voice
    speechSynthesis.speak(utterance)
  }, [getChineseVoice, state.currentSentenceIndex])

  useEffect(() => {
    const loadVoices = () => speechSynthesis.getVoices()
    loadVoices()
    speechSynthesis.addEventListener('voiceschanged', loadVoices)
    return () => speechSynthesis.removeEventListener('voiceschanged', loadVoices)
  }, [])

  useEffect(() => {
    return () => {
      stoppedRef.current = true
      speechSynthesis.cancel()
      clearTimers()
    }
  }, [clearTimers])

  return {
    ...state,
    speak,
    pause,
    resume,
    stop,
    setRate,
    speakWord,
  }
}
