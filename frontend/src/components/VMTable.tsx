import { useState, useEffect, useCallback } from 'react';
import type { VirtualMachine, VMInfo } from '../types/config';
import { useEventSource } from '../hooks/useEventSource';

interface VMTableProps {
  vms: VirtualMachine[];
  esxiHost: string;
  hostCpuCount?: number;
  hostRamGb?: number;
  hostStorageGb?: number;
}

function formatRam(ramMb: number | null): string {
  if (ramMb === null) return '-';
  if (ramMb >= 1024) {
    return `${(ramMb / 1024).toFixed(1)} GB`;
  }
  return `${ramMb} MB`;
}

function formatStorage(storageGb: number | null): string {
  if (storageGb === null) return '-';
  if (storageGb >= 1024) {
    return `${(storageGb / 1024).toFixed(2)} TB`;
  }
  return `${storageGb.toFixed(1)} GB`;
}

function getPowerStateInfo(powerState: string | null): { color: string; label: string } {
  if (!powerState) return { color: 'is-light', label: '-' };
  if (powerState.includes('poweredOn')) return { color: 'is-success', label: 'ON' };
  if (powerState.includes('poweredOff')) return { color: 'is-danger', label: 'OFF' };
  if (powerState.includes('suspended')) return { color: 'is-warning', label: 'SUSPENDED' };
  return { color: 'is-light', label: powerState };
}

interface ResourceBarProps {
  used: number;
  total: number;
  label: string;
  color: string;
  unit: string;
}

function ResourceBar({ used, total, label, color, unit }: ResourceBarProps) {
  const percentage = total > 0 ? Math.min((used / total) * 100, 100) : 0;
  const isOvercommitted = used > total;

  return (
    <div className="resource-bar mb-3">
      <div className="is-flex is-justify-content-space-between mb-1">
        <span className="is-size-7 has-text-weight-semibold">{label}</span>
        <span className="is-size-7">
          {used.toFixed(1)}{unit} / {total.toFixed(1)}{unit}
          {isOvercommitted && <span className="has-text-warning ml-1">(オーバーコミット)</span>}
        </span>
      </div>
      <div className="progress-container" style={{ height: '12px', backgroundColor: '#e9ecef', borderRadius: '6px', overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.min(percentage, 100)}%`,
            height: '100%',
            backgroundColor: isOvercommitted ? '#f14668' : color,
            borderRadius: '6px',
            transition: 'width 0.5s ease-out',
          }}
        />
      </div>
      <div className="is-flex is-justify-content-space-between mt-1">
        <span className="is-size-7 has-text-grey">{percentage.toFixed(1)}% 使用</span>
        <span className="is-size-7 has-text-grey">{(total - used).toFixed(1)}{unit} 空き</span>
      </div>
    </div>
  );
}

export function VMTable({ vms, esxiHost, hostCpuCount, hostRamGb, hostStorageGb }: VMTableProps) {
  const [vmInfoMap, setVmInfoMap] = useState<Record<string, VMInfo | null>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAllVMInfo = useCallback(async () => {
    setLoading(true);

    try {
      // Batch fetch all VM info
      const response = await fetch('/server-list/api/vm/info/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vms: vms.map((vm) => vm.name),
          esxi_host: esxiHost,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.results) {
          const newMap: Record<string, VMInfo | null> = {};
          for (const vm of vms) {
            const result = data.results[vm.name];
            newMap[vm.name] = result?.success ? result.data : null;
          }
          setVmInfoMap(newMap);
        }
      }
    } catch {
      console.log('Failed to fetch VM info');
    }

    setLoading(false);
  }, [vms, esxiHost]);

  // SSE event listener for data updates
  useEventSource('/server-list/api/event', {
    onMessage: (event) => {
      if (event.data === 'data') {
        fetchAllVMInfo();
        setRefreshing(false);
      }
    },
  });

  useEffect(() => {
    if (vms.length > 0) {
      fetchAllVMInfo();
    }
  }, [vms, esxiHost, fetchAllVMInfo]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const response = await fetch(`/server-list/api/vm/refresh/${encodeURIComponent(esxiHost)}`, {
        method: 'POST',
      });
      if (!response.ok) {
        console.error('Failed to trigger refresh');
        setRefreshing(false);
      }
      // Note: We don't set refreshing to false here because the SSE event will trigger the update
    } catch {
      console.error('Failed to trigger refresh');
      setRefreshing(false);
    }
  };

  if (!vms || vms.length === 0) {
    return null;
  }

  // Calculate totals
  const totals = {
    cpu: 0,
    ramMb: 0,
    storageGb: 0,
  };

  for (const vm of vms) {
    const info = vmInfoMap[vm.name];
    if (info) {
      totals.cpu += info.cpu_count || 0;
      totals.ramMb += info.ram_mb || 0;
      totals.storageGb += info.storage_gb || 0;
    }
  }

  const totalsRamGb = totals.ramMb / 1024;

  return (
    <div className="vm-table-container">
      <div className="is-flex is-justify-content-space-between is-align-items-center mb-4">
        <h4 className="title is-5 mb-0">
          <span className="icon-text">
            <span className="icon">☁️</span>
            <span>仮想マシン ({vms.length}台)</span>
          </span>
        </h4>
        <button
          className={`button is-ghost ${refreshing ? 'is-loading' : ''}`}
          onClick={handleRefresh}
          disabled={refreshing}
          title="ESXi から最新データを取得"
          style={{
            fontSize: '1.25rem',
            padding: '0.25rem',
            height: 'auto',
            minWidth: 'auto',
          }}
        >
          {!refreshing && '🔄'}
        </button>
      </div>

      {/* Resource Usage Summary */}
      {!loading && (hostCpuCount || hostRamGb || hostStorageGb) && (
        <div className="box mb-4" style={{ backgroundColor: '#fafafa' }}>
          <h5 className="title is-6 mb-3">リソース使用状況</h5>
          {hostCpuCount && hostCpuCount > 0 && (
            <ResourceBar
              used={totals.cpu}
              total={hostCpuCount}
              label="vCPU割当"
              color="#f14668"
              unit=" コア"
            />
          )}
          {hostRamGb && hostRamGb > 0 && (
            <ResourceBar
              used={totalsRamGb}
              total={hostRamGb}
              label="メモリ割当"
              color="#3298dc"
              unit=" GB"
            />
          )}
          {hostStorageGb && hostStorageGb > 0 && (
            <ResourceBar
              used={totals.storageGb}
              total={hostStorageGb}
              label="ストレージ割当"
              color="#48c774"
              unit=" GB"
            />
          )}
        </div>
      )}

      <div className="table-container">
        <table className="table is-fullwidth is-striped is-hoverable">
          <thead>
            <tr>
              <th>VM名</th>
              <th className="has-text-centered">vCPU</th>
              <th className="has-text-centered">メモリ</th>
              <th className="has-text-centered">ストレージ</th>
              <th className="has-text-centered">状態</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="has-text-centered">
                  読み込み中...
                </td>
              </tr>
            ) : (
              vms.map((vm) => {
                const info = vmInfoMap[vm.name];
                const powerState = getPowerStateInfo(info?.power_state || null);

                return (
                  <tr key={vm.name}>
                    <td>
                      <span className="icon-text">
                        <span className="icon is-small">🔹</span>
                        <span>{vm.name}</span>
                      </span>
                    </td>
                    <td className="has-text-centered">
                      {info?.cpu_count ?? '-'}
                    </td>
                    <td className="has-text-centered">
                      {formatRam(info?.ram_mb || null)}
                    </td>
                    <td className="has-text-centered">
                      {formatStorage(info?.storage_gb || null)}
                    </td>
                    <td className="has-text-centered">
                      <span className={`tag ${powerState.color}`}>
                        {powerState.label}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
          <tfoot>
            <tr className="has-background-light">
              <th>合計</th>
              <th className="has-text-centered">{totals.cpu} vCPU</th>
              <th className="has-text-centered">{formatRam(totals.ramMb)}</th>
              <th className="has-text-centered">{formatStorage(totals.storageGb)}</th>
              <th></th>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
