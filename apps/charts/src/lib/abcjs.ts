import type * as Abcjs from 'abcjs';
import abcjsUrl from 'abcjs/dist/abcjs-basic-min.js?url';

/**
 * abcjs 6.4.4 is loaded as a classic <script>, exactly as the reference page
 * loads it from cdnjs. Bundling it as an ES module fails at runtime ("i is not
 * defined": the build assigns an undeclared variable, which only works in
 * sloppy mode). The file still comes from the pinned npm package, so the
 * version is locked and served from our own origin.
 */
export type AbcjsModule = typeof Abcjs;

declare global {
  interface Window {
    ABCJS?: AbcjsModule;
  }
}

let loading: Promise<AbcjsModule> | undefined;

export function loadAbcjs(): Promise<AbcjsModule> {
  if (window.ABCJS) return Promise.resolve(window.ABCJS);
  if (!loading) {
    loading = new Promise<AbcjsModule>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = abcjsUrl;
      script.async = true;
      script.onload = () =>
        window.ABCJS
          ? resolve(window.ABCJS)
          : reject(new Error('abcjs loaded but window.ABCJS is missing'));
      script.onerror = () => reject(new Error(`failed to load ${abcjsUrl}`));
      document.head.appendChild(script);
    });
  }
  return loading;
}
