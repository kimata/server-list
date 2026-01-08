import { useEffect, useState, useCallback } from 'react';
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

function parseRam(ram: string): number {
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

function parseStorage(volume: string): number {
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
  return machine.storage.reduce((total, disk) => total + parseStorage(disk.volume), 0);
}

export function MachineDetailPage() {
  const { machineName } = useParams<{ machineName: string }>();
  const navigate = useNavigate();
  const [machine, setMachine] = useState<Machine | null>(null);
  const [cpuBenchmark, setCpuBenchmark] = useState<CpuBenchmark | null>(null);
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

        const config: Config = await configResponse.json();
        const decodedName = decodeURIComponent(machineName || '');
        const foundMachine = config.machine.find((m) => m.name === decodedName);

        if (!foundMachine) {
          setError(`Machine not found: ${decodedName}`);
          setLoading(false);
          return;
        }

        setMachine(foundMachine);

        // Fetch CPU benchmark
        try {
          const benchmarkResponse = await fetch('/server-list/api/cpu/benchmark/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cpus: [foundMachine.cpu] }),
          });

          if (benchmarkResponse.ok) {
            const data = await benchmarkResponse.json();
            const result = data.results?.[foundMachine.cpu];
            if (result?.success) {
              setCpuBenchmark(result.data);
            }
          }
        } catch {
          console.log('CPU benchmark API not available');
        }

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
                  <a href="#" className="has-text-white">{machine.name}</a>
                </li>
              </ul>
            </nav>
            <h1 className="title is-3">
              {machine.name}
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
              <span className="tag is-info ml-2">{machine.os}</span>
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
                      <span className="is-size-6">{machine.cpu}</span>
                    </div>
                    {cpuBenchmark?.multi_thread_score && (
                      <PerformanceBar
                        label="マルチスレッド性能"
                        value={cpuBenchmark.multi_thread_score}
                        maxValue={cpuBenchmark.multi_thread_score * 1.2}
                        color="#f14668"
                        icon=""
                      />
                    )}
                  </div>

                  <div className="spec-item mb-4">
                    <PerformanceBar
                      label="RAM"
                      value={ramGb}
                      maxValue={ramGb * 1.2}
                      unit=" GB"
                      color="#3298dc"
                      icon=""
                    />
                  </div>

                  <div className="spec-item mb-4">
                    <PerformanceBar
                      label="総ストレージ容量"
                      value={Math.round(totalStorageGb / 1024 * 10) / 10}
                      maxValue={totalStorageGb / 1024 * 1.2}
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
                    <span className="tag is-light">{machine.mode}</span>
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
