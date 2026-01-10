import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import type { Config, Machine, UptimeInfo, PowerInfo } from '../types/config';
import { StorageInfo } from '../components/StorageInfo';
import { ZfsStorageInfo } from '../components/ZfsStorageInfo';
import { PerformanceBar } from '../components/PerformanceBar';
import { VMTable } from '../components/VMTable';
import { UptimeDisplay } from '../components/UptimeDisplay';
import { ServerImage } from '../components/ServerImage';
import Footer from '../components/Footer';
import { useEventSource } from '../hooks/useEventSource';
import { useCpuBenchmarks } from '../hooks/useCpuBenchmarks';
import { parseRam, getTotalStorage } from '../utils/parsing';

export function MachineDetailPage() {
  const { machineName } = useParams<{ machineName: string }>();
  const navigate = useNavigate();
  const [config, setConfig] = useState<Config | null>(null);
  const [machine, setMachine] = useState<Machine | null>(null);
  const [uptimeInfo, setUptimeInfo] = useState<UptimeInfo | null>(null);
  const [powerInfo, setPowerInfo] = useState<PowerInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { cpuBenchmarks, fetchBenchmarks } = useCpuBenchmarks();

  const fetchUptimeData = useCallback(async () => {
    if (!machineName) return;

    try {
      const response = await fetch(`/server-list/api/uptime/${encodeURIComponent(machineName)}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          setUptimeInfo(data.data);
        }
      }
    } catch {
      console.log('Uptime API not available');
    }
  }, [machineName]);

  const fetchPowerData = useCallback(async () => {
    if (!machineName) return;

    try {
      const response = await fetch(`/server-list/api/power/${encodeURIComponent(machineName)}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          setPowerInfo(data.data);
        }
      }
    } catch {
      console.log('Power API not available');
    }
  }, [machineName]);

  // SSE event listener for data updates
  useEventSource('/server-list/api/event', {
    onMessage: (event) => {
      if (event.data === 'data') {
        fetchUptimeData();
        fetchPowerData();
      }
    },
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch config
        const configResponse = await fetch('/server-list/api/config');
        if (!configResponse.ok) {
          throw new Error('Failed to load config');
        }

        const configData: Config = await configResponse.json();
        setConfig(configData);
        const decodedName = decodeURIComponent(machineName || '');
        const foundMachine = configData.machine.find((m) => m.name === decodedName);

        if (!foundMachine) {
          setError(`Machine not found: ${decodedName}`);
          setLoading(false);
          return;
        }

        setMachine(foundMachine);

        // Fetch CPU benchmarks for all machines
        const cpuNames = configData.machine.map((m) => m.cpu);
        fetchBenchmarks(cpuNames);

        // Fetch uptime and power
        fetchUptimeData();
        fetchPowerData();

        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    };

    fetchData();
  }, [machineName, fetchUptimeData, fetchPowerData, fetchBenchmarks]);

  // Calculate max values across all machines (same as HomePage)
  // NOTE: This useMemo must be called before early returns to comply with Rules of Hooks
  const { maxCpuScore, maxSingleThreadScore, maxRam, maxStorage } = useMemo(() => {
    if (!config || !config.machine || !Array.isArray(config.machine)) {
      return { maxCpuScore: 0, maxSingleThreadScore: 0, maxRam: 0, maxStorage: 0 };
    }

    let maxCpu = 0;
    let maxSingle = 0;
    let maxRamValue = 0;
    let maxStorageValue = 0;

    for (const m of config.machine) {
      const benchmark = cpuBenchmarks[m.cpu];
      if (benchmark?.multi_thread_score && benchmark.multi_thread_score > maxCpu) {
        maxCpu = benchmark.multi_thread_score;
      }
      if (benchmark?.single_thread_score && benchmark.single_thread_score > maxSingle) {
        maxSingle = benchmark.single_thread_score;
      }

      const ram = parseRam(m.ram);
      if (ram > maxRamValue) {
        maxRamValue = ram;
      }

      const storage = getTotalStorage(m);
      if (storage > maxStorageValue) {
        maxStorageValue = storage;
      }
    }

    return {
      maxCpuScore: maxCpu,
      maxSingleThreadScore: maxSingle,
      maxRam: maxRamValue,
      maxStorage: maxStorageValue,
    };
  }, [config, cpuBenchmarks]);

  if (loading) {
    return (
      <section className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden mx-auto">
            <div className="h-full bg-purple-600 animate-pulse w-3/4"></div>
          </div>
          <p className="mt-4 text-gray-600">読み込み中...</p>
        </div>
      </section>
    );
  }

  if (error || !machine) {
    return (
      <section className="py-8">
        <div className="container mx-auto px-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700">{error || 'Machine not found'}</p>
            <Link to="/" className="inline-block mt-3 px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded transition-colors">
              一覧に戻る
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const ramGb = parseRam(machine.ram);
  const totalStorageGb = getTotalStorage(machine);
  const cpuBenchmark = machine ? cpuBenchmarks[machine.cpu] : null;

  return (
    <>
      <section className="hero-gradient py-12">
        <div className="container mx-auto px-4">
          <Link to="/" className="text-white/80 hover:text-white text-sm transition-colors">
            ← 一覧に戻る
          </Link>
          <h1 className="text-3xl font-bold text-white mt-2">
            サーバー・仮想マシン一覧
          </h1>
          <p className="text-xl text-white/80 mt-2">
            {String(machine.name ?? '')}
          </p>
          <div className="flex items-center flex-wrap gap-2 mt-3">
            <UptimeDisplay uptimeInfo={uptimeInfo} hostName={machine.name} />
            {powerInfo?.power_watts != null && (
              <span className="inline-flex items-center px-2 py-1 bg-red-100 text-red-700 rounded text-sm">
                <span className="mr-1">⚡</span>
                <span>{powerInfo.power_watts} W</span>
              </span>
            )}
            {machine.esxi && (
              <a
                href={machine.esxi}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="inline-flex items-center px-2 py-1 bg-blue-500 text-white rounded text-sm">ESXi</span>
              </a>
            )}
            {machine.ilo && (
              <a
                href={machine.ilo}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="inline-flex items-center px-2 py-1 bg-yellow-500 text-white rounded text-sm">iLO</span>
              </a>
            )}
            <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm">
              {String((uptimeInfo?.esxi_version ?? machine.os ?? '').replace(/^VMware\s+/i, ''))}
            </span>
          </div>
        </div>
      </section>

      <section className="py-8">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            {/* 左カラム - ハードウェア仕様 + VM */}
            <div className="lg:col-span-2 order-2 lg:order-1">
              {/* Machine Specs */}
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-bold mb-4">ハードウェア仕様</h3>

                <div className="specs-section">
                  <div className="spec-item mb-4">
                    <div className="flex items-center mb-2">
                      <span className="inline-block px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-sm mr-2">CPU</span>
                      <span className="text-sm">{String(machine.cpu ?? '')}</span>
                    </div>
                    {cpuBenchmark?.multi_thread_score && maxCpuScore > 0 && (
                      <PerformanceBar
                        label="マルチスレッド性能"
                        value={cpuBenchmark.multi_thread_score}
                        maxValue={maxCpuScore}
                        color="#f14668"
                        icon=""
                      />
                    )}
                    {cpuBenchmark?.single_thread_score && maxSingleThreadScore > 0 && (
                      <PerformanceBar
                        label="シングルスレッド性能"
                        value={cpuBenchmark.single_thread_score}
                        maxValue={maxSingleThreadScore}
                        color="#ff7f50"
                        icon=""
                      />
                    )}
                  </div>

                  <div className="spec-item mb-4">
                    <PerformanceBar
                      label="RAM"
                      value={ramGb}
                      maxValue={maxRam}
                      unit=" GB"
                      color="#3298dc"
                      icon=""
                    />
                  </div>

                  {machine.storage !== 'zfs' && (
                    <div className="spec-item mb-4">
                      <PerformanceBar
                        label="総ストレージ容量"
                        value={Math.round(totalStorageGb / 1024 * 10) / 10}
                        maxValue={maxStorage / 1024}
                        unit=" TB"
                        color="#48c774"
                        icon=""
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Virtual Machines */}
              {machine.vm && machine.vm.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <VMTable
                    vms={machine.vm}
                    esxiHost={machine.name}
                    hostCpuCount={uptimeInfo?.cpu_threads ?? undefined}
                    hostRamGb={ramGb}
                    hostStorageGb={totalStorageGb}
                  />
                </div>
              )}
            </div>

            {/* 右カラム - モバイルでは contents で展開、PCでは通常のブロック */}
            <div className="contents lg:block">
              {/* Server Image - モバイルでorder-1(最初)、PCでは右カラム内で上 */}
              <div className="order-1 lg:order-none bg-white rounded-lg shadow p-6 mb-6">
                <div className="flex justify-center">
                  <ServerImage modelName={machine.mode} size="large" />
                </div>
                <div className="mt-3 flex justify-center">
                  <div className="inline-flex rounded overflow-hidden">
                    <span className="px-2 py-1 bg-gray-800 text-white text-sm">モデル</span>
                    <span className="px-2 py-1 bg-gray-100 text-gray-800 text-sm">{String(machine.mode ?? '')}</span>
                  </div>
                </div>
              </div>

              {/* Storage Details - モバイルでorder-3(最後の方)、PCでは右カラム内で中央 */}
              <div className="order-3 lg:order-none bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-bold mb-4">ストレージ詳細</h3>
                {machine.storage === 'zfs' ? (
                  <ZfsStorageInfo hostName={machine.name} />
                ) : (
                  <StorageInfo storage={machine.storage} />
                )}
              </div>

              {/* Quick Actions - モバイルでorder-4(最後)、PCでは右カラム内で下 */}
              <div className="order-4 lg:order-none bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-bold mb-4">クイックアクション</h3>
                <div className="space-y-2">
                  <button
                    className="w-full px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded transition-colors"
                    onClick={() => navigate('/')}
                  >
                    一覧に戻る
                  </button>
                  {machine.esxi && (
                    <a
                      href={machine.esxi}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-center rounded transition-colors"
                    >
                      ESXi管理画面を開く
                    </a>
                  )}
                  {machine.ilo && (
                    <a
                      href={machine.ilo}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block w-full px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white text-center rounded transition-colors"
                    >
                      iLO管理画面を開く
                    </a>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
