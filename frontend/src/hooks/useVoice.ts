import { useRef, useCallback, useState } from 'react';
import type { Language } from '@/types/api';

export function useVoice(onResult: (text: string) => void) {
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [listening, setListening] = useState(false);

  const init = useCallback(() => {
    const Impl = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Impl) return;
    const r = new Impl();
    r.continuous = false;
    r.interimResults = true;
    r.maxAlternatives = 1;
    r.onresult = (e: SpeechRecognitionEvent) => {
      const results = e.results;
      const parts: string[] = [];
      for (let i = 0; i < results.length; i++) {
        parts.push(results[i][0].transcript);
      }
      const text = parts.join('');
      if (results[results.length - 1].isFinal) {
        onResult(text);
      }
    };
    r.onerror = () => setListening(false);
    r.onend = () => setListening(false);
    recognitionRef.current = r;
  }, [onResult]);

  const start = useCallback((lang: Language) => {
    if (!recognitionRef.current) init();
    const r = recognitionRef.current;
    if (!r) return;
    r.lang = lang === 'ar' ? 'ar-AE' : 'en-GB';
    try { r.start(); } catch { /* already started */ }
    setListening(true);
  }, [init]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  const supported = typeof window !== 'undefined' &&
    !!(window.SpeechRecognition || window.webkitSpeechRecognition);

  return { listening, start, stop, supported };
}
