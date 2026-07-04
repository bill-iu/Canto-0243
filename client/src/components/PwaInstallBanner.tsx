import React from 'react';

interface PwaInstallBannerProps {
  hasNativePrompt: boolean;
  onTrigger: () => void;
  onDismiss: () => void;
}

export function PwaInstallBanner({ hasNativePrompt, onTrigger, onDismiss }: PwaInstallBannerProps) {
  const [showGuidance, setShowGuidance] = React.useState(false);

  const handleClick = () => {
    if (hasNativePrompt) {
      onTrigger();
    } else {
      setShowGuidance(true);
    }
  };

  const handleClose = (e: React.MouseEvent) => {
    e.stopPropagation();
    sessionStorage.setItem('canto-pwa-install-dismissed', '1');
    onDismiss();
  };

  if (showGuidance) {
    return (
      <div className="pwa-install-banner" role="button" tabIndex={0}>
        請按分享按鈕 → 加到主畫面
        <button
          type="button"
          className="pwa-install-banner__close"
          onClick={handleClose}
          aria-label="關閉"
        >
          ×
        </button>
      </div>
    );
  }

  return (
    <div
      className="pwa-install-banner"
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      將Canto-0243 加到主畫面
      <button
        type="button"
        className="pwa-install-banner__close"
        onClick={handleClose}
        aria-label="關閉"
      >
        ×
      </button>
    </div>
  );
}
