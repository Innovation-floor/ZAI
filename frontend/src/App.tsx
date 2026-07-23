import { useEffect, useState, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { t } from '@/lib/i18n';
import { AppProvider, useApp } from '@/lib/store';
import { TopBar } from '@/components/TopBar';
import { KpiBar } from '@/components/KpiBar';
import { WorldMap } from '@/components/WorldMap';
import { Charts } from '@/components/Charts';
import { InsightCard } from '@/components/InsightCard';
import { Avatar3D, type AvatarHandle } from '@/components/Avatar3D';
import { SvgAvatar } from '@/components/SvgAvatar';
import { ExecutiveBrief } from '@/components/ExecutiveBrief';
import { DocumentPanel } from '@/components/DocumentPanel';
import { Toast, toast } from '@/components/Toast';
import { useVoice } from '@/hooks/useVoice';
import { useSpeech } from '@/hooks/useSpeech';
import { useDemo } from '@/hooks/useDemo';
import type { Language } from '@/types/api';

function AppContent() {
  const { state, dispatch } = useApp();
  const [mapAction, setMapAction] = useState('world');
  const [transcript, setTranscript] = useState('');
  const [statusText, setStatusText] = useState('');
  const [busy, setBusy] = useState(false);
  const [avatarLoaded, setAvatarLoaded] = useState(false);
  const textInputRef = useRef<HTMLInputElement>(null);
  const avatarRef = useRef<AvatarHandle>(null);

  const { speak } = useSpeech(state.voiceConfig);

  const doSpeak = useCallback((text: string) => {
    // Clean stop before new speech — critical for demo mode where
    // queries fire rapidly and the previous speech may still be playing.
    avatarRef.current?.stopSpeaking();

    speak(text, state.lang, {
      onStart: (txt) => avatarRef.current?.startSpeaking(txt),
      onEnd: () => avatarRef.current?.stopSpeaking(),
      onBoundary: (source) => avatarRef.current?.emphasise(source),
      onAttachAudio: (audio) => avatarRef.current?.attachAudio(audio),
    });
  }, [speak, state.lang]);

  const ask = useCallback(async (question: string) => {
    if (!question.trim() || busy) return;
    setTranscript(question);
    setBusy(true);
    setStatusText(t('understanding', state.lang));

    const phase = setTimeout(() => setStatusText(t('consulting', state.lang)), 2500);

    try {
      const r = await api.query(question, state.sessionId || undefined);
      dispatch({ type: 'SET_SESSION', sessionId: r.session_id });
      dispatch({ type: 'SET_DASHBOARD', summary: r.summary, distributions: r.distributions, map: r.map });
      dispatch({ type: 'SET_INSIGHT', insight: r.insight, stateDescription: r.state_description });
      setMapAction(r.map_action);
      if (r.warnings?.length) toast(r.warnings[0]);
      setStatusText(t('answering', state.lang));
      doSpeak(r.spoken_response);
    } catch (err: any) {
      toast(`Query failed: ${err.message}`);
    } finally {
      clearTimeout(phase);
      setBusy(false);
      setStatusText('');
    }
  }, [busy, state.sessionId, state.lang, dispatch, doSpeak]);

  const voice = useVoice(ask);
  const demo = useDemo(ask);

  const handleReset = useCallback(async () => {
    if (state.sessionId) {
      await api.resetSession(state.sessionId).catch(() => {});
    }
    ask(state.lang === 'ar' ? 'أظهر المحفظة بالكامل' : 'show the entire portfolio');
  }, [state.sessionId, state.lang, ask]);

  const toggleLang = useCallback(() => {
    const next: Language = state.lang === 'ar' ? 'en' : 'ar';
    dispatch({ type: 'SET_LANG', lang: next });
    document.documentElement.lang = next;
    document.documentElement.dir = next === 'ar' ? 'rtl' : 'ltr';
  }, [state.lang, dispatch]);

  // Boot
  useEffect(() => {
    (async () => {
      try {
        const health = await api.health();
        dispatch({ type: 'SET_PROVIDERS', providers: health.providers });
        if (health.providers.llm === 'mock') {
          // mock banner shows automatically via TopBar
        }
      } catch {
        toast('API unreachable');
      }

      try {
        const vc = await api.voiceConfig();
        dispatch({ type: 'SET_VOICE_CONFIG', config: vc });

        // Preload TTS voices
        if (vc.client_side_tts && window.speechSynthesis) {
          await new Promise<void>((resolve) => {
            if (speechSynthesis.getVoices().length > 200) { resolve(); return; }
            speechSynthesis.onvoiceschanged = () => {
              if (speechSynthesis.getVoices().length > 0) resolve();
            };
            setTimeout(resolve, 2000);
          });
        }
      } catch {}

      try {
        const session = await api.avatarSession(state.lang);
        dispatch({ type: 'SET_AVATAR_SESSION', session });
        if (session.degraded_from) {
          toast('Avatar streaming unavailable — using the local avatar.');
        }
        if (session.mode === 'model3d' && session.model_url) {
          setAvatarLoaded(true);
        }
      } catch {}

      try {
        const overview = await api.overview();
        dispatch({
          type: 'SET_DASHBOARD',
          summary: overview.summary,
          distributions: overview.distributions,
          map: overview.map,
        });
      } catch (err: any) {
        toast(`Overview failed: ${err.message}`);
      }
    })();
  }, []);

  return (
    <>
      <TopBar
        lang={state.lang}
        providers={state.providers}
        demoRunning={demo.running}
        onToggleLang={toggleLang}
        onToggleDemo={demo.toggle}
      />

      <main className="layout">
        {/* ========== LEFT COLUMN ========== */}
        <section className="col-left">
          <div className="card avatar-card">
            {avatarLoaded && state.avatarSession ? (
              <Avatar3D
                ref={avatarRef}
                session={state.avatarSession}
              />
            ) : (
              <div className="avatar-stage">
                <SvgAvatar />
              </div>
            )}

            <div className="avatar-name">
              {state.avatarSession?.display_name || 'ZAI'}
            </div>

            <button
              className={`btn primary mic ${voice.listening ? 'listening' : ''}`}
              onClick={() => voice.listening ? voice.stop() : voice.start(state.lang)}
              disabled={busy}
            >
              <span className="dot" />
              <span>
                {voice.listening
                  ? t('listening', state.lang)
                  : busy
                    ? t('thinking', state.lang)
                    : t('speak', state.lang)}
              </span>
            </button>

            <p className="transcript" style={{ fontWeight: transcript ? 600 : 400 }}>
              {transcript || t('transcriptHint', state.lang)}
            </p>

            {statusText && (
              <div className="status">
                <span className="spinner" />
                <span>{statusText}</span>
                <span className="dots"><i /><i /><i /></span>
              </div>
            )}

            <div className="fallback-row">
              <input
                ref={textInputRef}
                type="text"
                placeholder={t('typeQ', state.lang)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && textInputRef.current) {
                    ask(textInputRef.current.value);
                    textInputRef.current.value = '';
                  }
                }}
              />
              <button
                className="btn small"
                disabled={busy}
                onClick={() => {
                  if (textInputRef.current) {
                    ask(textInputRef.current.value);
                    textInputRef.current.value = '';
                  }
                }}
              >
                Ask
              </button>
            </div>
          </div>

          <ExecutiveBrief lang={state.lang} />

          <DocumentPanel
            lang={state.lang}
            sessionId={state.sessionId}
            onSessionId={(id) => dispatch({ type: 'SET_SESSION', sessionId: id })}
            onSpeak={doSpeak}
          />
        </section>

        {/* ========== RIGHT COLUMN ========== */}
        <section className="col-right">
          {state.summary && (
            <KpiBar summary={state.summary} lang={state.lang} />
          )}

          {state.map && (
            <WorldMap data={state.map} action={mapAction} lang={state.lang} />
          )}

          {state.insight && (
            <InsightCard
              insight={state.insight}
              stateDescription={state.stateDescription}
              lang={state.lang}
              onAsk={ask}
              onReset={handleReset}
            />
          )}

          {state.distributions && (
            <Charts distributions={state.distributions} lang={state.lang} />
          )}
        </section>
      </main>

      <Toast />
    </>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
