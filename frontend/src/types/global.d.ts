// =============================================================================
// Module declarations for untyped JS and browser APIs
// =============================================================================

// avatar3d.js is vanilla JS — declare it so TypeScript accepts the import
declare module '@/lib/avatar3d' {
  export class DigitalHuman {
    canvas: HTMLCanvasElement;
    speaking: boolean;
    driveMode: string;

    static supported(): boolean;
    constructor(container: HTMLElement);
    load(url: string, opts?: { zoom?: number; offsetY?: number }): Promise<DigitalHuman>;
    startSpeaking(text?: string): void;
    stopSpeaking(): void;
    emphasise(source?: string): void;
    attachAudio(audio: HTMLAudioElement): void;
    dispose(): void;
  }
}

// Web Speech API — Chrome/Edge types not in default lib
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  lang: string;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onend: (() => void) | null;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResultList {
  length: number;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface Window {
  SpeechRecognition: new () => SpeechRecognition;
  webkitSpeechRecognition: new () => SpeechRecognition;
}
