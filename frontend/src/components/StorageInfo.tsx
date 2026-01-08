import type { Storage } from '../types/config';

interface StorageInfoProps {
  storage: Storage[];
}

export function StorageInfo({ storage }: StorageInfoProps) {
  if (!storage || !Array.isArray(storage) || storage.length === 0) {
    return (
      <div className="storage-info">
        <h4 className="title is-6">
          💾 ストレージ
        </h4>
        <p className="has-text-grey is-size-7">ストレージ情報がありません</p>
      </div>
    );
  }

  return (
    <div className="storage-info">
      <h4 className="title is-6">
        💾 ストレージ
      </h4>
      <div className="content">
        {storage.map((disk, index) => (
          <div key={index} className="box storage-item">
            <div className="columns is-mobile is-vcentered">
              <div className="column">
                <p className="has-text-weight-semibold">{disk.name}</p>
                <p className="is-size-7 has-text-grey">
                  📦 モデル: {disk.model}
                </p>
              </div>
              <div className="column is-narrow">
                <span className="tag is-info is-medium volume-tag">
                  {disk.volume}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
