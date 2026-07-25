import React from 'react';

export type PortableUpdateInfo = {
  available: boolean;
  release_url?: string | null;
  download_hint?: string | null;
  remote?: { tag?: string } | null;
};

type Props = {
  info: PortableUpdateInfo;
  lang: 'zh' | 'zh-Hans' | 'en';
  onDismiss: () => void;
};

export function PortableUpdateBanner({ info, lang, onDismiss }: Props) {
  const tag = info.remote?.tag || '';
  const url = info.release_url || 'https://github.com/bill-iu/Canto-0243/releases/latest';
  const hint = info.download_hint || '';

  const copyHint = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!hint) return;
    try {
      await navigator.clipboard.writeText(hint);
    } catch {
      /* ignore */
    }
  };

  const title =
    lang === 'en'
      ? `Update available${tag ? `: ${tag}` : ''}`
      : `有新正式版${tag ? `：${tag}` : ''}`;
  const sub =
    lang === 'en'
      ? 'Download the full package, close this app, then extract over the old folder.'
      : '請下載完整套件，關閉本程式後解壓覆蓋舊資料夾。';
  const openLabel = lang === 'en' ? 'Open Release' : '前往 Release';
  const copyLabel = lang === 'en' ? 'Copy download cmd' : '複製下載指令';
  const laterLabel = lang === 'en' ? 'Later' : '稍後';

  return (
    <div className="portable-update-banner" role="status">
      <div className="portable-update-banner__text">
        <strong>{title}</strong>
        <span>{sub}</span>
      </div>
      <div className="portable-update-banner__actions">
        <a className="portable-update-banner__btn" href={url} target="_blank" rel="noreferrer">
          {openLabel}
        </a>
        {hint ? (
          <button type="button" className="portable-update-banner__btn" onClick={copyHint}>
            {copyLabel}
          </button>
        ) : null}
        <button
          type="button"
          className="portable-update-banner__close"
          onClick={onDismiss}
          aria-label={laterLabel}
        >
          {laterLabel}
        </button>
      </div>
    </div>
  );
}
