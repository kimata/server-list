import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import type { Config, Machine, CpuBenchmark, UptimeInfo } from '../types/config';
import { StorageInfo } from '../components/StorageInfo';
import { PerformanceBar } from '../components/PerformanceBar';
import { VMTable } from '../components/VMTable';
import { UptimeDisplay } from '../components/UptimeDisplay';
import { useEventSource } from '../hooks/useEventSource';

function ServerImage({ modelName }: { modelName: string }) {
  const [hasImage, setHasImage] = useState(true);
  const imageUrl = `/server-list/api/img/${encodeURIComponent(modelName)}.png`;

  if (!hasImage) {
    return null;
  }

  return (
    <div className="has-text-centered">
      <img
        src={imageUrl}
        alt={modelName}
        className="server-image"
        onError={() => setHasImage(false)}
        style={{
          maxWidth: '100%',
          height: 'auto',
          maxHeight: '200px',
          objectFit: 'contain',
        }}
      />
    </div>
  );
}

function parseRam(ram: string | undefined | null): number {
  if (!ram || typeof ram !== 'string') return 0;
  const match = ram.match(/([\d.]+)\s*(GB|TB|MB)/i);
  if (!match) return 0;

  const value = parseFloat(match[1]);
  const unit = match[2].toUpperCase();

  switch (unit) {
    case 'TB':
      return value * 1024;
    case 'GB':
      return value;
    case 'MB':
      return value / 1024;
    default:
      return value;
  }
}

function parseStorage(volume: string | undefined | null): number {
  if (!volume || typeof volume !== 'string') return 0;
  const match = volume.match(/([\d.]+)\s*(TB|GB|MB)/i);
  if (!match) return 0;

  const value = parseFloat(match[1]);
  const unit = match[2].toUpperCase();

  switch (unit) {
    case 'TB':
      return value * 1024;
    case 'GB':
      return value;
    case 'MB':
      return value / 1024;
    default:
      return value;
  }
}

function getTotalStorage(machine: Machine): number {
  if (!machine.storage || !Array.isArray(machine.storage)) {
    return 0;
  }
  return machine.storage.reduce((total, disk) => total + parseStorage(disk.volume), 0);
}

export function MachineDetailPage() {
  const { machineName } = useParams<{ machineName: string }>();
  const navigate = useNavigate();
  const [config, setConfig] = useState<Config | null>(null);
  const [machine, setMachine] = useState<Machine | null>(null);
  const [cpuBenchmarks, setCpuBenchmarks] = useState<Record<string, CpuBenchmark | null>>({});
  const [uptimeInfo, setUptimeInfo] = useState<UptimeInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  // SSE event listener for uptime updates
  useEventSource('/server-list/api/event', {
    onMessage: (event) => {
      if (event.data === 'data') {
        fetchUptimeData();
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
        const fetchBenchmarks = async (shouldFetch = false) => {
          try {
            const cpuNames = configData.machine.map((m) => m.cpu);
            const benchmarkResponse = await fetch('/server-list/api/cpu/benchmark/batch', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ cpus: cpuNames, fetch: shouldFetch }),
            });

            if (benchmarkResponse.ok) {
              const data = await benchmarkResponse.json();
              const benchmarks: Record<string, CpuBenchmark | null> = {};
              let hasMissingData = false;

              for (const cpu of cpuNames) {
                const result = data.results?.[cpu];
                benchmarks[cpu] = result?.success ? result.data : null;
                if (!result?.success) {
                  hasMissingData = true;
                }
              }

              setCpuBenchmarks(benchmarks);

              // If some data is missing and we haven't tried fetching yet, retry with fetch=true
              if (hasMissingData && !shouldFetch) {
                fetchBenchmarks(true);
              }
            }
          } catch {
            console.log('CPU benchmark API not available');
          }
        };
        fetchBenchmarks();

        // Fetch uptime
        fetchUptimeData();

        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    };

    fetchData();
  }, [machineName, fetchUptimeData]);

  if (loading) {
    return (
      <section className="hero is-fullheight">
        <div className="hero-body">
          <div className="container has-text-centered">
            <progress className="progress is-primary" max="100">Loading...</progress>
            <p className="mt-4">読み込み中...</p>
          </div>
        </div>
      </section>
    );
  }

  if (error || !machine) {
    return (
      <section className="section">
        <div className="container">
          <div className="notification is-danger">
            <p>{error || 'Machine not found'}</p>
            <Link to="/" className="button is-light mt-3">
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

  // Calculate max values across all machines (same as HomePage)
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

  return (
    <>
      <section className="hero is-primary is-bold">
        <div className="hero-body">
          <div className="container">
            <nav className="breadcrumb has-bullet-separator" aria-label="breadcrumbs">
              <ul>
                <li>
                  <Link to="/" className="has-text-white-ter">サーバー一覧</Link>
                </li>
                <li className="is-active">
                  <a href="#" className="has-text-white">{String(machine.name ?? '')}</a>
                </li>
              </ul>
            </nav>
            <h1 className="title is-3">
              {String(machine.name ?? '')}
            </h1>
            <div className="is-flex is-align-items-center">
              <UptimeDisplay uptimeInfo={uptimeInfo} hostName={machine.name} />
              {machine.esxi && (
                <a
                  href={machine.esxi}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-3"
                >
                  <span className="tag is-link">ESXi</span>
                </a>
              )}
              {machine.ilo && (
                <a
                  href={machine.ilo}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2"
                >
                  <span className="tag is-warning">iLO</span>
                </a>
              )}
              <span className="tag is-info ml-2">{String(machine.os ?? '')}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="columns">
            <div className="column is-8">
              {/* Machine Specs */}
              <div className="box">
                <h3 className="title is-5 mb-4">ハードウェア仕様</h3>

                <div className="specs-section">
                  <div className="spec-item mb-4">
                    <div className="is-flex is-align-items-center mb-2">
                      <span className="tag is-warning is-light mr-2">CPU</span>
                      <span className="is-size-6">{String(machine.cpu ?? '')}</span>
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
                </div>
              </div>

              {/* Virtual Machines */}
              {machine.vm && machine.vm.length > 0 && (
                <div className="box">
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

            <div className="column is-4">
              {/* Server Image */}
              <div className="box">
                <ServerImage modelName={machine.mode} />
                <div className="has-text-centered mt-3">
                  <div className="tags has-addons is-justify-content-center">
                    <span className="tag is-dark">モデル</span>
                    <span className="tag is-light">{String(machine.mode ?? '')}</span>
                  </div>
                </div>
              </div>

              {/* Storage Details */}
              <div className="box">
                <h3 className="title is-5 mb-4">ストレージ詳細</h3>
                <StorageInfo storage={machine.storage} />
              </div>

              {/* Quick Actions */}
              <div className="box">
                <h3 className="title is-5 mb-4">クイックアクション</h3>
                <div className="buttons">
                  <button
                    className="button is-light is-fullwidth"
                    onClick={() => navigate('/')}
                  >
                    一覧に戻る
                  </button>
                  {machine.esxi && (
                    <a
                      href={machine.esxi}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="button is-link is-fullwidth"
                    >
                      ESXi管理画面を開く
                    </a>
                  )}
                  {machine.ilo && (
                    <a
                      href={machine.ilo}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="button is-warning is-fullwidth"
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

      <footer className="footer">
        <div className="content has-text-centered">
          <p>
            Server List Viewer - Built with React + Bulma
          </p>
        </div>
      </footer>
    </>
  );
}
