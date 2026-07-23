import { t } from '@/lib/i18n';
import type { Language } from '@/types/api';

interface Props {
  lang: Language;
  providers: { llm: string; stt: string; tts: string; avatar: string } | null;
  demoRunning: boolean;
  onToggleLang: () => void;
  onToggleDemo: () => void;
}

export function TopBar({ lang, providers, demoRunning, onToggleLang, onToggleDemo }: Props) {
  const isMock = providers?.llm === 'mock';

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <span className="mark">ZAI</span>
          <span className="tag">{t('tagline', lang)}</span>
        </div>
        <div className="topbar-actions">
          {providers && (
            <span className="chip" title="Active providers">
              llm:{providers.llm} · stt:{providers.stt} · avatar:{providers.avatar}
            </span>
          )}
          <button className="btn ghost" onClick={onToggleDemo}>
            {demoRunning ? t('stop', lang) : t('demo', lang)}
          </button>
          <button className="btn ghost" onClick={onToggleLang}>
            {lang === 'ar' ? 'English' : 'العربية'}
          </button>
        </div>
      </header>

      {isMock && (
        <div className="banner">
          <b>Deterministic planner active.</b>
          <span>
            Language understanding is keyword matching, not a model. Set{' '}
            <code>LLM_PROVIDER=azure</code> in <code>.env</code> and restart.
          </span>
        </div>
      )}
    </>
  );
}
