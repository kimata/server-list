import { useEffect, useState, useCallback } from 'react';
import type { MountInfo } from '../types/config';
import { useEventSource } from '../hooks/useEventSource';

interface MountStorageInfoProps {
  hostName: string;
}

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
}

export function MountStorageInfo({ hostName }: MountStorageInfoProps) {
  const [mounts, setMounts] = useState<MountInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMountData = useCallback(async () => {
    try {
      const response = await fetch(`/server-list/api/storage/mount/${encodeURIComponent(hostName)}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          setMounts(data.data);
        }
      }
    } catch {
      console.log('Mount API not available');
    } finally {
      setLoading(false);
    }
  }, [hostName]);

  useEventSource('/server-list/api/event', {
    onMessage: (event) => {
      if (event.data === 'data') {
        fetchMountData();
      }
    },
  });

  useEffect(() => {
    fetchMountData();
  }, [fetchMountData]);

  if (loading) {
    return (
      <div className="mount-storage-info">
        <h4 className="text-sm font-bold mb-2">ファイルシステム</h4>
        <p className="text-gray-500 text-xs">読み込み中...</p>
      </div>
    );
  }

  if (mounts.length === 0) {
    return null;
  }

  return (
    <div className="mount-storage-info">
      <h4 className="text-sm font-bold mb-3">ファイルシステム</h4>
      <div className="space-y-3">
        {mounts.map((mount) => {
          const usedPercent = mount.size_bytes && mount.used_bytes
            ? (mount.used_bytes / mount.size_bytes) * 100
            : 0;

          return (
            <div key={mount.mountpoint} className="bg-gray-50 rounded p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm font-mono">{mount.mountpoint}</span>
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
                <span>使用: {formatBytes(mount.used_bytes)}</span>
                <span>空き: {formatBytes(mount.avail_bytes)}</span>
                <span>合計: {formatBytes(mount.size_bytes)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
