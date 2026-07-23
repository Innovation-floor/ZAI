import { useRef, useCallback, useState } from 'react';
import { api } from '@/lib/api';

export function useDemo(ask: (question: string) => Promise<void>) {
  const [running, setRunning] = useState(false);
  const cancelRef = useRef(false);

  const toggle = useCallback(async () => {
    if (running) {
      cancelRef.current = true;
      setRunning(false);
      return;
    }

    setRunning(true);
    cancelRef.current = false;

    try {
      const { beats } = await api.demoScript();
      for (const beat of beats) {
        if (cancelRef.current) break;
        await ask(beat.question);
        if (cancelRef.current) break;
        await new Promise((r) => setTimeout(r, 6500));
      }
    } catch (err) {
      console.error('Demo failed:', err);
    }

    setRunning(false);
  }, [running, ask]);

  return { running, toggle };
}
