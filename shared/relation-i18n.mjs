import { selectUiCatalog } from './ui-locale.mjs';

const RELATION_COPY = {
  zh: {
    title: '關係補錄',
    lede: '為已收錄字面補近義或反義關係。種子字面為擴展起點；對端字面提供一跳鄰居來源。',
    seed: '種子字面',
    seedHint: '擴展從此字面出發（例如要補「快樂」的關係時填快樂）',
    opposite: '對端字面',
    oppositeHint: '與種子建立 direct 關係的另一字面',
    relationType: '關係類型',
    synonym: '近義',
    antonym: '反義',
    add: '補上關係',
    revoke: '撤回關係',
    cannotReach: '無法連線後端。請確認伺服器已啟動。',
    relationAdded: '已補上關係。',
    submitFailed: '提交失敗，請稍後再試。',
    relationRevoked: '已撤回關係。',
    revokeFailed: '撤回失敗，請稍後再試。',
  },
  zhHans: {
    title: '关系补录',
    lede: '为已收录字面补近义或反义关系。种子字面为扩展起点；对端字面提供一跳邻居来源。',
    seed: '种子字面',
    seedHint: '扩展从此字面出发（例如要补「快乐」的关系时填快乐）',
    opposite: '对端字面',
    oppositeHint: '与种子建立 direct 关系的另一字面',
    relationType: '关系类型',
    synonym: '近义',
    antonym: '反义',
    add: '补上关系',
    revoke: '撤回关系',
    cannotReach: '无法连接后端。请确认服务器已启动。',
    relationAdded: '已补上关系。',
    submitFailed: '提交失败，请稍后再试。',
    relationRevoked: '已撤回关系。',
    revokeFailed: '撤回失败，请稍后再试。',
  },
  en: {
    title: 'Add relations',
    lede: 'Add synonym or antonym links for lexicon entries. Seed is the expansion start; opposite is the one-hop neighbour.',
    seed: 'Seed',
    seedHint: 'Expansion starts here (e.g. 快樂 when adding links for 快樂)',
    opposite: 'Opposite',
    oppositeHint: 'The other literal linked directly to the seed',
    relationType: 'Relation type',
    synonym: 'Synonym',
    antonym: 'Antonym',
    add: 'Add relation',
    revoke: 'Revoke relation',
    cannotReach: 'Cannot reach the server. Is it running?',
    relationAdded: 'Relation added.',
    submitFailed: 'Submit failed.',
    relationRevoked: 'Relation revoked.',
    revokeFailed: 'Revoke failed.',
  },
};

export function getRelationCopy(lang = 'zh') {
  return selectUiCatalog(RELATION_COPY, lang);
}

export function relationI18nSelfCheck() {
  if (getRelationCopy('zh').title !== '關係補錄') throw new Error('relation zh');
  if (getRelationCopy('zh-Hans').title !== '关系补录') throw new Error('relation zh-Hans');
  if (getRelationCopy('en').add !== 'Add relation') throw new Error('relation en');
}
