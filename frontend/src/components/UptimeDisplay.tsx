import { useState, useEffect, useCallback } from 'react';
import type { UptimeInfo } from '../types/config';

interface UptimeDisplayProps {
  uptimeInfo: UptimeInfo | null;
  hostName?: string;
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  const parts: string[] = [];
  if (days > 0) parts.push(`${days}日`);
  if (hours > 0 || days > 0) parts.push(`${hours}時間`);
  parts.push(`${minutes}分`);

  return parts.join(' ');
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
        <span className="tag is-light">
          <span className="icon is-small mr-1">⏱️</span>
          <span className="is-size-7">Uptime: 取得中...</span>
        </span>
      </div>
    );
  }

  if (uptimeInfo.status === 'stopped') {
    return (
      <div className="uptime-display">
        <span className="tag is-danger">
          <span className="icon is-small mr-1">⚠️</span>
          <span className="is-size-7">停止中</span>
        </span>
      </div>
    );
  }

  return (
    <div className="uptime-display">
      <span className="tag is-success is-light">
        <span className="icon is-small mr-1">⏱️</span>
        <span className="is-size-7">
          Uptime: {displaySeconds !== null ? formatUptime(displaySeconds) : '計算中...'}
        </span>
      </span>
    </div>
  );
}
