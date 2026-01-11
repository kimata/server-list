import { useEffect, useState, useCallback } from 'react';
import type { ZfsPoolInfo } from '../types/config';
import { useEventSource } from '../hooks/useEventSource';

interface ZfsStorageInfoProps {
  hostName: string;
}

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
}

function getHealthStatus(health: number | null): { text: string; color: string } {
  if (health === null) return { text: '不明', color: 'gray' };
  // health: 0 = ONLINE, 1 = DEGRADED, 2 = FAULTED, etc.
  switch (health) {
    case 0:
      return { text: 'ONLINE', color: 'green' };
    case 1:
      return { text: 'DEGRADED', color: 'yellow' };
    case 2:
      return { text: 'FAULTED', color: 'red' };
    default:
      return { text: '不明', color: 'gray' };
  }
}

export function ZfsStorageInfo({ hostName }: ZfsStorageInfoProps) {
  const [pools, setPools] = useState<ZfsPoolInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchZfsData = useCallback(async () => {
    try {
      const response = await fetch(`/server-list/api/storage/zfs/${encodeURIComponent(hostName)}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          setPools(data.data);
        }
      }
    } catch {
      console.log('ZFS API not available');
    } finally {
      setLoading(false);
    }
  }, [hostName]);

  useEventSource('/server-list/api/event', {
    onMessage: (event) => {
      if (event.data === 'data') {
        fetchZfsData();
      }
    },
  });

  useEffect(() => {
    fetchZfsData();
  }, [fetchZfsData]);

  if (loading) {
    return (
      <div className="zfs-storage-info">
        <h4 className="text-sm font-bold mb-2">🗄️ ZFS プール</h4>
        <p className="text-gray-500 text-xs">読み込み中...</p>
      </div>
    );
  }

  if (pools.length === 0) {
    return null;
  }

  return (
    <div className="zfs-storage-info">
      <h4 className="text-sm font-bold mb-3">🗄️ ZFS プール</h4>
      <div className="space-y-3">
        {pools.map((pool) => {
          const usedPercent = pool.size_bytes && pool.allocated_bytes
            ? (pool.allocated_bytes / pool.size_bytes) * 100
            : 0;
          const healthStatus = getHealthStatus(pool.health);

          return (
            <div key={pool.pool_name} className="bg-gray-50 rounded p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">{pool.pool_name}</span>
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-${healthStatus.color}-100 text-${healthStatus.color}-700`}>
                  {healthStatus.text}
                </span>
              </div>

              {/* Progress bar */}
              <div className="relative h-4 bg-gray-200 rounded overflow-hidden mb-1">
                <div
                  className={`absolute top-0 left-0 h-full transition-all duration-300 ${
                    usedPercent > 90 ? 'bg-red-500' :
                    usedPercent > 70 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(usedPercent, 100)}%` }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-bold text-white drop-shadow-[0_1px_1px_rgba(0,0,0,0.5)]">
                    {usedPercent.toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Storage details */}
              <div className="flex justify-between text-xs text-gray-600">
                <span>使用: {formatBytes(pool.allocated_bytes)}</span>
                <span>空き: {formatBytes(pool.free_bytes)}</span>
                <span>合計: {formatBytes(pool.size_bytes)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
