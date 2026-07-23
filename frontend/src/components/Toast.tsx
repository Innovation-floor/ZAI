import { useEffect, useState } from 'react';

let showToastFn: ((msg: string, ms?: number) => void) | null = null;

export function toast(msg: string, ms = 4000) {
  showToastFn?.(msg, ms);
}

export function Toast() {
  const [message, setMessage] = useState('');
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    showToastFn = (msg, ms = 4000) => {
      setMessage(msg);
      setVisible(true);
      setTimeout(() => setVisible(false), ms);
    };
    return () => { showToastFn = null; };
  }, []);

  if (!visible) return null;
  return <div className="toast">{message}</div>;
}
