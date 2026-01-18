import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import type { UPSInfo, UPSResponse } from '../types/ups';
import { UPSCard } from '../components/UPSCard';
import Footer from '../components/Footer';
import { useEventSource } from '../hooks/useEventSource';

export function UPSPage() {
  const [upsList, setUpsList] = useState<UPSInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUpsData = useCallback(async () => {
    try {
      const response = await fetch('/server-list/api/ups');
      if (!response.ok) {
        throw new Error('Failed to fetch UPS data');
      }
      const data: UPSResponse = await response.json();
      if (data.success && data.data) {
        setUpsList(data.data);
      }
    } catch (err) {
      console.error('Failed to fetch UPS data:', err);
    }
  }, []);

  useEventSource('/server-list/api/event', {
    onMessage: (event) => {
      if (event.data === 'data') {
        fetchUpsData();
      }
    },
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/server-list/api/ups');
        if (!response.ok) {
          throw new Error('Failed to fetch UPS data');
        }
        const data: UPSResponse = await response.json();
        if (data.success && data.data) {
          setUpsList(data.data);
        } else {
          throw new Error(data.error || 'Failed to fetch UPS data');
        }
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <section className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden mx-auto">
            <div className="h-full bg-purple-600 animate-pulse w-3/4"></div>
          </div>
          <p className="mt-4 text-gray-600">UPS 情報を読み込み中...</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="min-h-screen flex items-center justify-center bg-red-500">
        <div className="text-center text-white">
          <h1 className="text-3xl font-bold">エラー</h1>
          <p className="text-xl mt-2">{error}</p>
        </div>
      </section>
    );
  }

  const totalClients = upsList.reduce((acc, ups) => acc + (ups.clients?.length || 0), 0);

  return (
    <>
      <section className="hero-gradient py-12">
        <div className="container mx-auto px-4">
          <div className="flex items-center gap-4 mb-2">
            <Link
              to="/"
              className="text-white/80 hover:text-white transition-colors"
            >
              ← サーバー一覧に戻る
            </Link>
          </div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <span>🔋</span>
            <span>UPS トポロジー</span>
          </h1>
          <p className="text-xl text-white/80 mt-2">
            無停電電源装置の状態と接続構成
          </p>
        </div>
      </section>

      <section className="py-8">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-xs uppercase tracking-wide text-green-600 mb-1">UPS 台数</p>
              <p className="text-2xl font-bold text-green-800">{upsList.length} 台</p>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-xs uppercase tracking-wide text-blue-600 mb-1">接続クライアント</p>
              <p className="text-2xl font-bold text-blue-800">{totalClients} 台</p>
            </div>
          </div>

          {upsList.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>UPS が設定されていません</p>
              <p className="text-sm mt-2">config.yaml に ups セクションを追加してください</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {upsList.map((ups, index) => (
                <div key={`${ups.host}-${ups.ups_name}`} className="animate-fade-in-up" style={{ animationDelay: `${index * 0.1}s` }}>
                  <UPSCard ups={ups} />
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <Footer />
    </>
  );
}
