import { createContext, useContext, useReducer, type ReactNode } from 'react';
import type { Language, Summary, Distributions, MapPayload, Insight, VoiceConfig, AvatarSession } from '@/types/api';

interface AppState {
  lang: Language;
  sessionId: string | null;
  documentId: string | null;
  voiceConfig: VoiceConfig | null;
  avatarSession: AvatarSession | null;
  summary: Summary | null;
  distributions: Distributions | null;
  map: MapPayload | null;
  insight: Insight | null;
  stateDescription: string;
  speaking: boolean;
  listening: boolean;
  busy: boolean;
  transcript: string;
  providers: { llm: string; stt: string; tts: string; avatar: string } | null;
}

type Action =
  | { type: 'SET_LANG'; lang: Language }
  | { type: 'SET_SESSION'; sessionId: string }
  | { type: 'SET_VOICE_CONFIG'; config: VoiceConfig }
  | { type: 'SET_AVATAR_SESSION'; session: AvatarSession }
  | { type: 'SET_PROVIDERS'; providers: AppState['providers'] }
  | { type: 'SET_DASHBOARD'; summary: Summary; distributions: Distributions; map: MapPayload }
  | { type: 'SET_INSIGHT'; insight: Insight; stateDescription: string }
  | { type: 'SET_SPEAKING'; speaking: boolean }
  | { type: 'SET_LISTENING'; listening: boolean }
  | { type: 'SET_BUSY'; busy: boolean }
  | { type: 'SET_TRANSCRIPT'; transcript: string }
  | { type: 'SET_DOCUMENT'; documentId: string };

const initial: AppState = {
  lang: 'en', sessionId: null, documentId: null,
  voiceConfig: null, avatarSession: null,
  summary: null, distributions: null, map: null, insight: null,
  stateDescription: '', speaking: false, listening: false, busy: false,
  transcript: '', providers: null,
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_LANG': return { ...state, lang: action.lang };
    case 'SET_SESSION': return { ...state, sessionId: action.sessionId };
    case 'SET_VOICE_CONFIG': return { ...state, voiceConfig: action.config };
    case 'SET_AVATAR_SESSION': return { ...state, avatarSession: action.session };
    case 'SET_PROVIDERS': return { ...state, providers: action.providers };
    case 'SET_DASHBOARD': return { ...state, summary: action.summary, distributions: action.distributions, map: action.map };
    case 'SET_INSIGHT': return { ...state, insight: action.insight, stateDescription: action.stateDescription };
    case 'SET_SPEAKING': return { ...state, speaking: action.speaking };
    case 'SET_LISTENING': return { ...state, listening: action.listening };
    case 'SET_BUSY': return { ...state, busy: action.busy };
    case 'SET_TRANSCRIPT': return { ...state, transcript: action.transcript };
    case 'SET_DOCUMENT': return { ...state, documentId: action.documentId };
    default: return state;
  }
}

const Ctx = createContext<{ state: AppState; dispatch: React.Dispatch<Action> } | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initial);
  return <Ctx.Provider value={{ state, dispatch }}>{children}</Ctx.Provider>;
}

export function useApp() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useApp must be inside AppProvider');
  return ctx;
}
