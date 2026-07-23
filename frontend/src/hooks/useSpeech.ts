import { useCallback, useRef } from 'react';
import type { Language, VoiceConfig } from '@/types/api';
import { api } from '@/lib/api';

interface SpeakOptions {
  onStart?: (text: string) => void;
  onEnd?: () => void;
  onBoundary?: (source: string) => void;
  onAttachAudio?: (audio: HTMLAudioElement) => void;
}

export function useSpeech(voiceConfig: VoiceConfig | null) {
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const guardRef = useRef<number>(0);
  const timerRef = useRef<number>(0);
  const cachedVoices = useRef<{ en: SpeechSynthesisVoice | null; ar: SpeechSynthesisVoice | null }>({
    en: null, ar: null,
  });

  const cacheVoices = useCallback(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    const voices = speechSynthesis.getVoices();
    const FEMALE_EN = ['zira', 'heera', 'jenny', 'aria', 'sara', 'emma'];
    const FEMALE_AR = ['فاطمة', 'سلمى', 'ليلى', 'نورا', 'أمل'];

    if (!cachedVoices.current.en) {
      cachedVoices.current.en = voices.find(v => /zira/i.test(v.name))
        || voices.find(v => v.lang.startsWith('en') && FEMALE_EN.some(f => v.name.toLowerCase().includes(f)))
        || voices.find(v => v.lang.startsWith('en')) || null;
    }
    if (!cachedVoices.current.ar) {
      cachedVoices.current.ar = voices.find(v => v.lang === 'ar-AE' && FEMALE_AR.some(f => v.name.includes(f)))
        || voices.find(v => v.lang.startsWith('ar')) || null;
    }
  }, []);

  const speak = useCallback(async (text: string, lang: Language, opts: SpeakOptions = {}) => {
    if (!text) return;

    // Azure TTS path — returns real audio
    if (voiceConfig && !voiceConfig.client_side_tts) {
      try {
        const r = await api.speak(text, lang);
        if (r.mode === 'audio' && r.audio_base64 && r.mime) {
          const audio = new Audio(`data:${r.mime};base64,${r.audio_base64}`);
          opts.onAttachAudio?.(audio);
          audio.onplay = () => opts.onStart?.(text);
          audio.onended = () => opts.onEnd?.();
          audio.play().catch(() => opts.onEnd?.());
          return;
        }
      } catch {
        opts.onEnd?.();
        return;
      }
    }

    // Browser TTS path
    if (!window.speechSynthesis) { opts.onEnd?.(); return; }

    // Detach old utterance callbacks BEFORE cancel — otherwise cancel()
    // fires onerror("interrupted") on the old utterance, which calls
    // stopSpeaking() and kills the avatar right before the new speech starts.
    if (utteranceRef.current) {
      utteranceRef.current.onstart = null;
      utteranceRef.current.onend = null;
      utteranceRef.current.onerror = null;
      utteranceRef.current.onboundary = null;
    }
    clearInterval(timerRef.current);
    clearTimeout(guardRef.current);
    speechSynthesis.cancel();
    cacheVoices();

    const u = new SpeechSynthesisUtterance(text);
    const voice = lang === 'ar' ? cachedVoices.current.ar : cachedVoices.current.en;
    if (voice) { u.voice = voice; u.lang = voice.lang; }
    else { u.lang = lang === 'ar' ? 'ar-AE' : 'en-US'; }

    u.rate = 0.98;
    let started = false;
    u.onstart = () => {
      clearTimeout(guardRef.current);
      if (!started) { started = true; opts.onStart?.(text); }
    };
    u.onboundary = (e) => { if (e.name === 'word') opts.onBoundary?.('tts'); };
    u.onend = () => { clearInterval(timerRef.current); clearTimeout(guardRef.current); opts.onEnd?.(); };
    u.onerror = () => { clearInterval(timerRef.current); clearTimeout(guardRef.current); opts.onEnd?.(); };

    utteranceRef.current = u;
    speechSynthesis.speak(u);

    // Backup word timer
    clearInterval(timerRef.current);
    const ms = lang === 'ar' ? 380 : 340;
    timerRef.current = window.setInterval(() => opts.onBoundary?.('timer'), ms);

    guardRef.current = window.setTimeout(() => {
      if (!started) { started = true; opts.onStart?.(text); }
    }, 600);

    window.setTimeout(() => {
      clearInterval(timerRef.current);
      opts.onEnd?.();
    }, 2000 + text.length * 120);
  }, [voiceConfig, cacheVoices]);

  return { speak };
}
