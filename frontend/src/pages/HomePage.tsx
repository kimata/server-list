import { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Config, UptimeData } from '../types/config';
import { ServerCard } from '../components/ServerCard';
import { useEventSource } from '../hooks/useEventSource';
import { useCpuBenchmarks } from '../hooks/useCpuBenchmarks';
import { parseRam, getTotalStorage } from '../utils/parsing';

export function HomePage() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uptimeData, setUptimeData] = useState<UptimeData>({});
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

  // SSE event listener for uptime updates
  useEventSource('/server-list/api/event', {
    onMessage: (event) => {
      // 'data' event means uptime data was updated
      if (event.data === 'data') {
        fetchUptimeData();
      }
    },
  });

  useEffect(() => {
    fetch('/server-list/api/config')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load config');
        }
        return response.json();
      })
      .then((data: Config) => {
        setConfig(data);
        setLoading(false);

        // Fetch CPU benchmarks
        const cpuNames = data.machine.map((m) => m.cpu);
        fetchBenchmarks(cpuNames);

        // Fetch uptime data
        fetchUptimeData();
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [fetchUptimeData, fetchBenchmarks]);

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
      <section className="hero is-fullheight">
        <div className="hero-body">
          <div className="container has-text-centered">
            <progress className="progress is-primary" max="100">Loading...</progress>
            <p className="mt-4">設定ファイルを読み込み中...</p>
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="hero is-fullheight is-danger">
        <div className="hero-body">
          <div className="container has-text-centered">
            <h1 className="title">エラー</h1>
            <p className="subtitle">{error}</p>
          </div>
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
      <section className="hero is-primary is-bold">
        <div className="hero-body">
          <div className="container">
            <h1 className="title">
              サーバー・仮想マシン一覧
            </h1>
            <p className="subtitle">
              インフラストラクチャの概要
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="columns is-multiline mb-5">
            <div className="column is-4">
              <div className="notification is-info is-light">
                <p className="heading">物理サーバー</p>
                <p className="title">{config?.machine.length || 0} 台</p>
              </div>
            </div>
            <div className="column is-4">
              <div className="notification is-success is-light">
                <p className="heading">仮想マシン</p>
                <p className="title">{totalVMs} 台</p>
              </div>
            </div>
            <div className="column is-4">
              <div className="notification is-warning is-light">
                <p className="heading">ストレージデバイス</p>
                <p className="title">{totalStorageDevices} 個</p>
              </div>
            </div>
          </div>

          <div className="columns is-multiline">
            {config?.machine.map((machine, index) => (
              <div key={index} className="column is-12-tablet is-6-desktop">
                <ServerCard
                  machine={machine}
                  cpuBenchmark={cpuBenchmarks[machine.cpu]}
                  maxCpuScore={maxCpuScore}
                  maxRam={maxRam}
                  maxStorage={maxStorage}
                  uptimeInfo={uptimeData[machine.name] || null}
                  onClick={() => handleMachineClick(machine.name)}
                />
              </div>
            ))}
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
