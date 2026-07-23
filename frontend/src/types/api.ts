// =============================================================================
// ZAI API Types
// =============================================================================

export interface Summary {
  projects: number;
  active: number;
  completed: number;
  planning: number;
  countries: number;
  partners: number;
  beneficiaries: number;
  investment_aed_m: number;
  avg_completion: number;
  attention_required: number;
  high_risk: number;
}

export interface Distribution {
  label: string;
  value: number;
  percent: number;
}

export interface Distributions {
  budget_by_sector: Distribution[];
  projects_by_status: Distribution[];
  projects_by_risk: Distribution[];
  projects_by_region: Distribution[];
  beneficiaries_by_country: Distribution[];
}

export interface MapMarker {
  id: string;
  name: string;
  country: string;
  sector: string;
  status: string;
  risk: string;
  completion: number;
  investment: number;
  beneficiaries: number;
  lat: number;
  lon: number;
  featured: boolean;
}

export interface MapBounds {
  south: number;
  west: number;
  north: number;
  east: number;
}

export interface MapPayload {
  markers: MapMarker[];
  bounds: MapBounds | null;
  truncated: boolean;
}

export interface Insight {
  summary: Summary;
  recommendation: string;
  decision_note: string | null;
  risk_level: 'Low' | 'Medium' | 'High';
  follow_ups: string[];
}

export interface QueryResponse {
  session_id: string;
  language: string;
  intent: string;
  question: string;
  spoken_response: string;
  state: Record<string, unknown>;
  state_description: string;
  summary: Summary;
  distributions: Distributions;
  map: MapPayload;
  insight: Insight;
  comparison: unknown[] | null;
  projects: unknown[];
  map_action: 'fit' | 'world' | 'none';
  warnings: string[];
  unknown_values: string[];
  planner: string;
  elapsed_ms: number;
}

export interface OverviewResponse {
  summary: Summary;
  distributions: Distributions;
  map: MapPayload;
  vocabulary: Record<string, string[]>;
}

export interface BriefAttention {
  id: string;
  name: string;
  country: string;
  completion: number;
  risk: string;
  reasons: string[];
}

export interface BriefResponse {
  active_projects: number;
  projects_requiring_attention: number;
  new_or_updated: number;
  countries_with_recent_activity: string[];
  attention_list: BriefAttention[];
  portfolio: Summary;
}

export interface HealthResponse {
  status: string;
  environment: string;
  providers: {
    llm: string;
    stt: string;
    tts: string;
    avatar: string;
    documents: string;
  };
  llm_detail: Record<string, unknown>;
}

export interface VoiceConfig {
  stt_provider: string;
  tts_provider: string;
  client_side_stt: boolean;
  client_side_tts: boolean;
  languages: { code: string; label: string }[];
  boost_terms: string[];
}

export interface AvatarSession {
  mode: 'static' | 'stream' | 'model3d' | 'photo' | 'video' | 'webrtc';
  model_url?: string;
  model_zoom?: number;
  model_offset_y?: number;
  photo_url?: string;
  portrait_url?: string;
  idle_video?: string;
  speaking_video?: string;
  display_name?: string;
  url?: string;
  access_token?: string;
  session_id?: string;
  degraded_from?: string;
  language?: string;
  mouth?: { x: number; y: number; w: number; h: number; gain: number };
}

export interface SpeakResponse {
  mode: 'client' | 'audio';
  text?: string;
  language?: string;
  voice_hint?: string;
  mime?: string;
  audio_base64?: string;
}

export interface DocumentUploadResponse {
  session_id: string;
  document_id: string;
  filename: string;
  pages: number;
  language: string;
  summary: string;
  characters: number;
  provider: string;
}

export interface DocumentAskResponse {
  document_id: string;
  question: string;
  answer: string;
  language: string;
}

export type Language = 'en' | 'ar';
