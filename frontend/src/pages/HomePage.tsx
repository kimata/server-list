import { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import type { Config, UptimeData, PowerData } from '../types/config';
import { ServerCard } from '../components/ServerCard';
import Footer from '../components/Footer';
import { useEventSource } from '../hooks/useEventSource';
import { useCpuBenchmarks } from '../hooks/useCpuBenchmarks';
import { parseRam, getTotalStorage } from '../utils/parsing';

export function HomePage() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uptimeData, setUptimeData] = useState<UptimeData>({});
  const [powerData, setPowerData] = useState<PowerData>({});
  const { cpuBenchmarks, fetchBenchmarks } = useCpuBenchmarks();

  const fetchUptimeData = useCallback(async () => {
    try {
      const response = await fetch('/server-list/api/uptime');
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          setUptimeData(data.data);
        }
      }
    } catch {
      console.log('Uptime API not available');
    }
  }, []);

  const fetchPowerData = useCallback(async () => {
    try {
      const response = await fetch('/server-list/api/power');
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          setPowerData(data.data);
        }
      }
    } catch {
      console.log('Power API not available');
    }
  }, []);

  // SSE event listener for data updates
  useEventSource('/server-list/api/event', {
    onMessage: (event) => {
      // 'data' event means uptime/power data was updated
      if (event.data === 'data') {
        fetchUptimeData();
        fetchPowerData();
      }
    },
  });

  useEffect(() => {
    // Fetch all data in parallel for faster initial load
    const fetchAllData = async () => {
      try {
        // Start all API calls in parallel
        const [configResponse] = await Promise.all([
          fetch('/server-list/api/config'),
          // Start uptime and power fetches in parallel (they don't need config)
          fetchUptimeData(),
          fetchPowerData(),
        ]);

        if (!configResponse.ok) {
          throw new Error('Failed to load config');
        }

        const response: { success: boolean; data?: Config; error?: string } = await configResponse.json();
        if (!response.success || !response.data) {
          throw new Error(response.error || 'Failed to load config');
        }

        const data = response.data;
        setConfig(data);
        setLoading(false);

        // Fetch CPU benchmarks after config is loaded (needs CPU names)
        const cpuNames = data.machine.map((m) => m.cpu);
        fetchBenchmarks(cpuNames);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    };

    fetchAllData();
  }, [fetchUptimeData, fetchPowerData, fetchBenchmarks]);

  const { maxCpuScore, maxRam, maxStorage } = useMemo(() => {
    if (!config || !config.machine || !Array.isArray(config.machine)) {
      return { maxCpuScore: 0, maxRam: 0, maxStorage: 0 };
    }

    let maxCpu = 0;
    let maxRamValue = 0;
    let maxStorageValue = 0;

    for (const machine of config.machine) {
      const benchmark = cpuBenchmarks[machine.cpu];
      if (benchmark?.multi_thread_score && benchmark.multi_thread_score > maxCpu) {
        maxCpu = benchmark.multi_thread_score;
      }

      const ramGb = parseRam(machine.ram);
      if (ramGb > maxRamValue) {
        maxRamValue = ramGb;
      }

      const storageGb = getTotalStorage(machine);
      if (storageGb > maxStorageValue) {
        maxStorageValue = storageGb;
      }
    }

    return {
      maxCpuScore: maxCpu,
      maxRam: maxRamValue,
      maxStorage: maxStorageValue,
    };
  }, [config, cpuBenchmarks]);

  const handleMachineClick = (machineName: string) => {
    navigate(`/machine/${encodeURIComponent(machineName)}`);
  };

  if (loading) {
    return (
      <section className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden mx-auto">
            <div className="h-full bg-purple-600 animate-pulse w-3/4"></div>
          </div>
          <p className="mt-4 text-gray-600">設定ファイルを読み込み中...</p>
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

  const totalVMs = config?.machine.reduce((acc, machine) => {
    return acc + (machine.vm?.length || 0);
  }, 0) || 0;

  const totalStorageDevices = config?.machine.reduce((acc, machine) => {
    return acc + (machine.storage?.length || 0);
  }, 0) || 0;

  return (
    <>
      <section className="hero-gradient py-12">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl font-bold text-white">
            サーバー・仮想マシン一覧
          </h1>
          <p className="text-xl text-white/80 mt-2">
            インフラストラクチャの概要
          </p>
        </div>
      </section>

      <section className="py-8">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-xs uppercase tracking-wide text-blue-600 mb-1">物理サーバー</p>
              <p className="text-2xl font-bold text-blue-800">{config?.machine.length || 0} 台</p>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-xs uppercase tracking-wide text-green-600 mb-1">仮想マシン</p>
              <p className="text-2xl font-bold text-green-800">{totalVMs} 台</p>
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-xs uppercase tracking-wide text-yellow-600 mb-1">ストレージデバイス</p>
              <p className="text-2xl font-bold text-yellow-800">{totalStorageDevices} 個</p>
            </div>
            <Link
              to="/ups"
              className="bg-purple-50 border border-purple-200 rounded-lg p-4 hover:bg-purple-100 hover:border-purple-300 transition-colors"
            >
              <p className="text-xs uppercase tracking-wide text-purple-600 mb-1">UPS トポロジー</p>
              <p className="text-2xl font-bold text-purple-800 flex items-center gap-2">
                <span>🔋</span>
                <span>表示 →</span>
              </p>
            </Link>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {config?.machine.map((machine, index) => (
              <div key={index} className="animate-fade-in-up" style={{ animationDelay: `${index * 0.1}s` }}>
                <ServerCard
                  machine={machine}
                  cpuBenchmark={cpuBenchmarks[machine.cpu]}
                  maxCpuScore={maxCpuScore}
                  maxRam={maxRam}
                  maxStorage={maxStorage}
                  uptimeInfo={uptimeData[machine.name] || null}
                  powerInfo={powerData[machine.name] || null}
                  onClick={() => handleMachineClick(machine.name)}
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
