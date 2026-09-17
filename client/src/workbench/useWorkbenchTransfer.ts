import { useCallback, useEffect } from 'react';
import type { Last0243SearchMode, UiMode } from '../mode-meta.ts';
import {
  WorkbenchBridgeError, consumeNavigate, consumeOpenSearch, hasWorkbenchDraft, writeIngest,
} from './workbench-bridge.ts';

interface TransferOptions {
  openWorkbench: () => void;
  offerReplace: (literal: string) => void;
  last0243Mode: Last0243SearchMode;
  setMode: (mode: UiMode) => void;
  openGuide: () => void;
  openAbout: () => void;
  openSearch: (literal: string) => void;
  hydrateSearch: (literal: string) => void;
}

/** Search/workbench handoff owns the one-shot bridge and replacement decision. */
export function useWorkbenchTransfer(options: TransferOptions) {
  const { openWorkbench, offerReplace } = options;
  const navigateWithIngest = useCallback((literal: string, mode: 'replace' | 'insert') => {
    try {
      writeIngest(sessionStorage, { literal, mode });
      openWorkbench();
    } catch (error) {
      window.alert(error instanceof WorkbenchBridgeError ? error.message : '無法放入句格。');
    }
  }, [openWorkbench]);

  const handlePutInWorkbench = useCallback((literal: string) => {
    const text = literal.trim();
    if (!text) return;
    if (!hasWorkbenchDraft(localStorage)) navigateWithIngest(text, 'replace');
    else offerReplace(text);
  }, [navigateWithIngest, offerReplace]);

  useEffect(() => {
    const nav = consumeNavigate(sessionStorage);
    if (nav?.kind === 'mode') {
      options.setMode(nav.family === 'basic' ? options.last0243Mode
        : nav.family === 'pingze' ? 'pingze' : 'synonym');
    } else if (nav?.kind === 'guide') options.openGuide();
    else if (nav?.kind === 'about') options.openAbout();
    const payload = consumeOpenSearch(sessionStorage);
    if (payload) {
      options.openSearch(payload.literal);
      options.hydrateSearch(payload.literal);
    }
    // One-shot bridge consumption belongs to the search shell mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { navigateWithIngest, handlePutInWorkbench };
}
