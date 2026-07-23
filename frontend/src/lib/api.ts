import type {
  QueryResponse, OverviewResponse, BriefResponse,
  HealthResponse, VoiceConfig, AvatarSession,
  SpeakResponse, DocumentUploadResponse, DocumentAskResponse,
} from '@/types/api';

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export const api = {
  health: () => request<HealthResponse>('/health/ready'),
  overview: () => request<OverviewResponse>('/portfolio/overview'),
  brief: () => request<BriefResponse>('/portfolio/brief'),
  voiceConfig: () => request<VoiceConfig>('/voice/config'),

  query: (question: string, sessionId?: string) =>
    post<QueryResponse>('/query', { question, session_id: sessionId }),

  resetSession: (sessionId: string) =>
    post<{ session_id: string; reset: boolean }>(
      `/session/reset?session_id=${encodeURIComponent(sessionId)}`, {}),

  avatarSession: (language: string) =>
    post<AvatarSession>('/avatar/session', { language }),

  speak: (text: string, language: string) =>
    post<SpeakResponse>('/voice/speak', { text, language }),

  uploadDocument: async (file: File, sessionId: string): Promise<DocumentUploadResponse> => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('session_id', sessionId || '');
    return request<DocumentUploadResponse>('/documents/upload', { method: 'POST', body: fd });
  },

  askDocument: (sessionId: string, documentId: string, question: string) =>
    post<DocumentAskResponse>('/documents/ask', {
      session_id: sessionId, document_id: documentId, question,
    }),

  demoScript: () => request<{ beats: { beat: string; question: string }[] }>('/demo/script'),
};
