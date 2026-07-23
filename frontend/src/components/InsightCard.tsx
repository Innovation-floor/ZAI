import type { Insight, Language } from '@/types/api';
import { t, fmt } from '@/lib/i18n';

interface Props {
  insight: Insight;
  stateDescription: string;
  lang: Language;
  onAsk: (question: string) => void;
  onReset: () => void;
}

export function InsightCard({ insight, stateDescription, lang, onAsk, onReset }: Props) {
  const s = insight.summary;
  const showReset = !/no filters applied/.test(stateDescription);

  return (
    <div className="card insight-card">
      <div className="card-head">
        <h2>{t('insightTitle', lang)}</h2>
        <span className={`chip risk-${insight.risk_level}`}>{insight.risk_level} risk</span>
      </div>

      <div className="head-actions" style={{ marginBottom: 12 }}>
        <span className="chip subtle">{stateDescription}</span>
        {showReset && (
          <button className="btn tiny" onClick={onReset}>{t('clearFilters', lang)}</button>
        )}
      </div>

      <div className="insight-figures">
        {[
          { v: fmt(s.projects, lang), l: t('projects', lang) },
          { v: `AED ${fmt(s.investment_aed_m, lang)}M`, l: t('investment', lang) },
          { v: fmt(s.beneficiaries, lang), l: t('beneficiaries', lang) },
          { v: `${s.avg_completion}%`, l: t('completion', lang) },
        ].map((fig, i) => (
          <div key={i} className="fig">
            <div className="v">{fig.v}</div>
            <div className="l">{fig.l}</div>
          </div>
        ))}
      </div>

      <p className="recommendation">{insight.recommendation}</p>
      {insight.decision_note && <p className="muted small">{insight.decision_note}</p>}

      <div className="chips">
        {insight.follow_ups.map((q, i) => (
          <button key={i} onClick={() => onAsk(q)}>{q}</button>
        ))}
      </div>
    </div>
  );
}
