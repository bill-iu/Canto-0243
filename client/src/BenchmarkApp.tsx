import { useEffect, useState } from 'react';
import { formatBenchmarkSample, runDbBenchmark, type DbBenchmarkSample } from './db/db-benchmark';

export function BenchmarkApp() {
  const [sample, setSample] = useState<DbBenchmarkSample | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(true);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await runDbBenchmark({ resetFirst: true });
      setSample(result);
      console.log('[DB-5 benchmark]', result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    void run();
  }, []);

  return (
    <div style={{ fontFamily: 'monospace', padding: 16, maxWidth: 720 }}>
      <h1>DB-5 benchmark</h1>
      <p>冷啟 init + 探針查詢（{running ? '執行中…' : '完成'}）</p>
      <p style={{ opacity: 0.85 }}>
        實機：先完成離線就緒 → 殺掉 PWA 進程 → 飛航模式重開 → 再跑此頁。Safari 無
        performance.memory，請用 Web Inspector Memory。
      </p>
      <button type="button" onClick={() => void run()} disabled={running}>
        重跑（reset + init + probe）
      </button>
      {error && <pre style={{ color: 'crimson' }}>{error}</pre>}
      {sample && (
        <pre style={{ marginTop: 12, whiteSpace: 'pre-wrap' }}>{formatBenchmarkSample(sample)}</pre>
      )}
    </div>
  );
}
