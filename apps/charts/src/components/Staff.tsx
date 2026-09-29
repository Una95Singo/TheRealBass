import { useLayoutEffect, useRef } from 'react';
import { loadAbcjs } from '../lib/abcjs';
import { fontsReady } from '../lib/fonts';
import { RENDER_OPTIONS, dedupePartLabels } from '../lib/render';

export interface StaffProps {
  abc: string;
  staffwidth?: number;
  /** Called after each render, once fonts are loaded and the SVG is in the DOM. */
  onRendered?: (el: HTMLDivElement) => void;
}

export default function Staff({ abc, staffwidth, onRendered }: StaffProps) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    let cancelled = false;
    void Promise.all([loadAbcjs(), fontsReady()]).then(([abcjs]) => {
      if (cancelled || !ref.current) return;
      el.innerHTML = '';
      abcjs.renderAbc(el, abc, { ...RENDER_OPTIONS, ...(staffwidth ? { staffwidth } : {}) });
      dedupePartLabels(el);
      onRendered?.(el);
    });
    return () => {
      cancelled = true;
    };
  }, [abc, staffwidth, onRendered]);

  return <div ref={ref} className="staff" />;
}
