import { modeHelp, type UiMode } from './mode-meta.ts';

export const MODE_OPTIONS: Array<{ family: 'basic' | 'pingze' | 'synonym'; uiMode: UiMode; key: string }> = [
  { family: 'basic', uiMode: '0243', key: '0243' },
  { family: 'pingze', uiMode: 'pingze', key: 'P / Z' },
  { family: 'synonym', uiMode: 'synonym', key: '~ / !' },
];

export function modeMenuSelfCheck(): void {
  if (MODE_OPTIONS.length !== 3) {
    throw new Error('modeMenuSelfCheck: mode options');
  }
  if (MODE_OPTIONS.map((o) => o.family).join(',') !== 'basic,pingze,synonym') {
    throw new Error('modeMenuSelfCheck: family order');
  }
  if (modeHelp('394052', 'zh') !== '394052 六聲碼（三／五聲分明）') {
    throw new Error('modeMenuSelfCheck: m3 help');
  }
  if (modeHelp('synonym', 'zh') !== '近義、反義與語意相關') {
    throw new Error('modeMenuSelfCheck: syn help');
  }
  if (modeHelp('0243', 'en') !== 'Common 0243 codes & mixed queries') {
    throw new Error('modeMenuSelfCheck: en m1 help');
  }
}
