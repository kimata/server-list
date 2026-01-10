import { useState, useEffect, useCallback } from 'react';
import type { UptimeInfo } from '../types/config';
import { formatUptime } from '../utils/formatters';

interface UptimeDisplayProps {
  uptimeInfo: UptimeInfo | null;
  hostName?: string;
}

export function UptimeDisplay({ uptimeInfo }: UptimeDisplayProps) {
  const [displaySeconds, setDisplaySeconds] = useState<number | null>(null);

  // Calculate initial uptime from server data
  const calculateCurrentUptime = useCallback(() => {
    if (!uptimeInfo?.uptime_seconds || !uptimeInfo?.collected_at) {
      return null;
    }

    const collectedTime = new Date(uptimeInfo.collected_at).getTime();
    const now = Date.now();
    const elapsedSinceCollection = (now - collectedTime) / 1000;

    return uptimeInfo.uptime_seconds + elapsedSinceCollection;
  }, [uptimeInfo]);

  // Update display every second
  useEffect(() => {
    if (!uptimeInfo || uptimeInfo.status !== 'running') {
      setDisplaySeconds(null);
      return;
    }

    // Initial calculation
    setDisplaySeconds(calculateCurrentUptime());

    // Update every second
    const interval = setInterval(() => {
      setDisplaySeconds((prev) => (prev !== null ? prev + 1 : calculateCurrentUptime()));
    }, 1000);

    return () => clearInterval(interval);
  }, [uptimeInfo, calculateCurrentUptime]);

  // Reset when uptimeInfo changes (SSE update)
  useEffect(() => {
    if (uptimeInfo?.uptime_seconds) {
      setDisplaySeconds(calculateCurrentUptime());
    }
  }, [uptimeInfo?.uptime_seconds, uptimeInfo?.collected_at, calculateCurrentUptime]);

  if (!uptimeInfo) {
    return (
      <div className="uptime-display">
        <span className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm">
          <span className="mr-1">⏱️</span>
          <span>Uptime: 取得中...</span>
        </span>
      </div>
    );
  }

  if (uptimeInfo.status === 'stopped') {
    return (
      <div className="uptime-display">
        <span className="inline-flex items-center px-2 py-1 bg-red-500 text-white rounded text-sm">
          <span className="mr-1">⚠️</span>
          <span>停止中</span>
        </span>
      </div>
    );
  }

  if (uptimeInfo.status === 'unknown') {
    return (
      <div className="uptime-display">
        <span className="inline-flex items-center px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-sm">
          <span className="mr-1">❓</span>
          <span>状態不明</span>
        </span>
      </div>
    );
  }

  return (
    <div className="uptime-display">
      <span className="inline-flex items-center px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
        <span className="mr-1">⏱️</span>
        <span>
          Uptime: {displaySeconds !== null ? formatUptime(displaySeconds) : '計算中...'}
        </span>
      </span>
    </div>
  );
}
