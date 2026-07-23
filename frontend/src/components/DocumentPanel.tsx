import { useState, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import { t } from '@/lib/i18n';
import type { Language } from '@/types/api';

interface Props {
  lang: Language;
  sessionId: string | null;
  onSessionId: (id: string) => void;
  onSpeak: (text: string) => void;
}

export function DocumentPanel({ lang, sessionId, onSessionId, onSpeak }: Props) {
  const [status, setStatus] = useState('');
  const [summary, setSummary] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const [busyText, setBusyText] = useState('');
  const questionRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(async (file: File) => {
    setStatus(file.name);
    setSummary('');
    setAnswer('');
    setBusy(true);
    setBusyText(t('reading', lang));

    const timer = setTimeout(() => setBusyText(t('summarising', lang)), 3000);

    try {
      const r = await api.uploadDocument(file, sessionId || '');
      onSessionId(r.session_id);
      setDocumentId(r.document_id);
      setStatus(`${r.filename} · ${r.pages} page(s) · ${r.language.toUpperCase()} · via ${r.provider}`);
      setSummary(r.summary);
      onSpeak(r.summary.slice(0, 320));
    } catch (err: any) {
      setStatus(`Upload failed: ${err.message}`);
    } finally {
      clearTimeout(timer);
      setBusy(false);
    }
  }, [lang, sessionId, onSessionId, onSpeak]);

  const handleAsk = useCallback(async () => {
    const q = questionRef.current?.value.trim();
    if (!q || !documentId) return;

    setAnswer('');
    setBusy(true);
    setBusyText(t('searchingDoc', lang));

    try {
      const r = await api.askDocument(sessionId || '', documentId, q);
      setAnswer(r.answer);
      onSpeak(r.answer.slice(0, 320));
    } catch (err: any) {
      setAnswer(`Failed: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }, [lang, sessionId, documentId, onSpeak]);

  return (
    <div className="card">
      <h2>{t('docTitle', lang)}</h2>

      <label className="upload" onClick={() => fileRef.current?.click()}>
        <span>{t('uploadLabel', lang)}</span>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt"
          hidden
          onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        />
      </label>

      {status && <div className="muted small" style={{ marginTop: 8 }}>{status}</div>}

      {busy && (
        <div className="status" style={{ marginTop: 8 }}>
          <span className="spinner" />
          <span>{busyText}</span>
          <span className="dots"><i /><i /><i /></span>
        </div>
      )}

      {summary && (
        <div className="doc-summary" style={{ marginTop: 12 }}>{summary}</div>
      )}

      {summary && (
        <div className="fallback-row" style={{ marginTop: 10 }}>
          <input
            ref={questionRef}
            type="text"
            placeholder={t('askDoc', lang)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
          />
          <button className="btn small" onClick={handleAsk} disabled={busy}>Ask</button>
        </div>
      )}

      {answer && (
        <div className="doc-answer" style={{ marginTop: 10 }}>{answer}</div>
      )}
    </div>
  );
}
