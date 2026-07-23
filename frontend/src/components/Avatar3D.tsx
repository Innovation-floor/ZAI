import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import type { AvatarSession } from '@/types/api';
import { DigitalHuman } from '@/lib/avatar3d';

export interface AvatarHandle {
  emphasise: (source?: string) => void;
  startSpeaking: (text: string) => void;
  stopSpeaking: () => void;
  attachAudio: (audio: HTMLAudioElement) => void;
}

interface Props {
  session: AvatarSession | null;
}

export const Avatar3D = forwardRef<AvatarHandle, Props>(
  ({ session }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const humanRef = useRef<DigitalHuman | null>(null);

    // Expose all speech methods directly — no state indirection,
    // no re-render delay. The parent calls these imperatively.
    useImperativeHandle(ref, () => ({
      emphasise: (source?: string) => {
        humanRef.current?.emphasise(source);
      },
      startSpeaking: (text: string) => {
        humanRef.current?.startSpeaking(text);
      },
      stopSpeaking: () => {
        humanRef.current?.stopSpeaking();
      },
      attachAudio: (audio: HTMLAudioElement) => {
        humanRef.current?.attachAudio(audio);
      },
    }));

    // Load model
    useEffect(() => {
      if (!session?.model_url || !containerRef.current) return;
      if (!DigitalHuman.supported()) return;

      const human = new DigitalHuman(containerRef.current);
      human.load(session.model_url, {
        zoom: session.model_zoom || 1.0,
        offsetY: session.model_offset_y || 0,
      }).then(() => {
        humanRef.current = human;
        containerRef.current?.classList.add('mode-3d');
      }).catch((err: unknown) => {
        console.warn('[3D] load failed', err);
        human.dispose();
      });

      return () => {
        human.dispose();
        humanRef.current = null;
      };
    }, [session?.model_url]);

    return (
      <div
        ref={containerRef}
        className="avatar-stage"
        style={{ position: 'relative', width: '100%', aspectRatio: '3/4', maxHeight: 310 }}
      />
    );
  }
);

Avatar3D.displayName = 'Avatar3D';
