import { useState, useEffect, useCallback } from 'react';
import type { VirtualMachine, VMInfo } from '../types/config';
import { useEventSource } from '../hooks/useEventSource';
import { formatRam, formatStorage, getPowerStateInfo } from '../utils/formatters';

interface VMTableProps {
  vms: VirtualMachine[];
  esxiHost: string;
  hostCpuCount?: number;
  hostRamGb?: number;
  hostStorageGb?: number;
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
      <div className="flex justify-between mb-1">
        <span className="text-xs font-semibold">{label}</span>
        <span className="text-xs">
          {used.toFixed(1)}{unit} / {total.toFixed(1)}{unit}
          {isOvercommitted && <span className="text-yellow-600 ml-1">(オーバーコミット)</span>}
        </span>
      </div>
      <div className="h-3 bg-gray-200 rounded-md overflow-hidden">
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
      <div className="flex justify-between mt-1">
        <span className="text-xs text-gray-500">{percentage.toFixed(1)}% 使用</span>
        <span className="text-xs text-gray-500">{(total - used).toFixed(1)}{unit} 空き</span>
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
  // CPU and RAM: only count powered on VMs (use cached_power_state for calculation)
  // Storage: count all VMs (allocated regardless of power state)
  const totals = {
    cpu: 0,
    ramMb: 0,
    storageGb: 0,
  };

  for (const vm of vms) {
    const info = vmInfoMap[vm.name];
    if (info) {
      const isPoweredOn = info.cached_power_state?.includes('poweredOn');
      if (isPoweredOn) {
        totals.cpu += info.cpu_count || 0;
        totals.ramMb += info.ram_mb || 0;
      }
      totals.storageGb += info.storage_gb || 0;
    }
  }

  const totalsRamGb = totals.ramMb / 1024;

  return (
    <div className="vm-table-container">
      <div className="flex justify-between items-center mb-4">
        <h4 className="text-lg font-bold">
          <span className="inline-flex items-center">
            <span className="mr-2">☁️</span>
            <span>仮想マシン ({vms.length}台)</span>
          </span>
        </h4>
        <button
          className={`text-xl p-1 bg-transparent border-none cursor-pointer ${refreshing ? 'animate-spin' : ''}`}
          onClick={handleRefresh}
          disabled={refreshing}
          title="ESXi から最新データを取得"
        >
          {!refreshing && '🔄'}
        </button>
      </div>

      {/* Resource Usage Summary */}
      {!loading && (hostCpuCount || hostRamGb || hostStorageGb) && (
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <h5 className="text-sm font-bold mb-3">リソース使用状況</h5>
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

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="text-left p-2 font-semibold">VM名</th>
              <th className="text-center p-2 font-semibold">vCPU</th>
              <th className="text-center p-2 font-semibold">メモリ</th>
              <th className="text-center p-2 font-semibold">ストレージ</th>
              <th className="text-center p-2 font-semibold">状態</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="text-center p-4">
                  読み込み中...
                </td>
              </tr>
            ) : (
              vms.map((vm) => {
                const info = vmInfoMap[vm.name];
                const powerState = getPowerStateInfo(info?.power_state || null);

                return (
                  <tr key={vm.name} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="p-2">
                      <span className="inline-flex items-center">
                        <span className="mr-2">🔹</span>
                        <span>{String(vm.name ?? '')}</span>
                      </span>
                    </td>
                    <td className="text-center p-2">
                      {info?.cpu_count ?? '-'}
                    </td>
                    <td className="text-center p-2">
                      {formatRam(info?.ram_mb || null)}
                    </td>
                    <td className="text-center p-2">
                      {formatStorage(info?.storage_gb || null)}
                    </td>
                    <td className="text-center p-2">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs ${powerState.tailwindClass}`}>
                        {powerState.label}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
          <tfoot>
            <tr className="bg-gray-100 border-t-2 border-gray-300">
              <th className="text-left p-2 font-semibold">合計</th>
              <th className="text-center p-2 font-semibold">{totals.cpu} vCPU</th>
              <th className="text-center p-2 font-semibold">{formatRam(totals.ramMb)}</th>
              <th className="text-center p-2 font-semibold">{formatStorage(totals.storageGb)}</th>
              <th></th>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
