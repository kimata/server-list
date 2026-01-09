import type { Storage } from '../types/config';

interface StorageInfoProps {
  storage: Storage[];
}

export function StorageInfo({ storage }: StorageInfoProps) {
  if (!storage || !Array.isArray(storage) || storage.length === 0) {
    return (
      <div className="storage-info">
        <h4 className="text-sm font-bold mb-2">
          💾 ストレージ
        </h4>
        <p className="text-gray-500 text-xs">ストレージ情報がありません</p>
      </div>
    );
  }

  return (
    <div className="storage-info">
      <h4 className="text-sm font-bold mb-2">
        💾 ストレージ
      </h4>
      <div>
        {storage.map((disk, index) => (
          <div key={index} className="storage-item rounded">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-sm">{String(disk.name ?? '')}</p>
                <p className="text-xs text-gray-500">
                  📦 モデル: {String(disk.model ?? '')}
                </p>
              </div>
              <div>
                <span className="inline-block px-3 py-1 bg-blue-500 text-white rounded text-sm volume-tag">
                  {String(disk.volume ?? '')}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
