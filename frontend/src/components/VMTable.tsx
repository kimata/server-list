import { useState, useEffect, useCallback, useMemo } from 'react';
import { CloudIcon } from '@heroicons/react/24/outline';
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

interface MiniUsageBarProps {
  percentage: number;
  color: string;
  label: string;
}

function MiniUsageBar({ percentage, color, label }: MiniUsageBarProps) {
  const clampedPercentage = Math.min(Math.max(percentage, 0), 100);

  return (
    <div className="flex items-center gap-1">
      <span className="text-xs text-gray-500 w-8">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden min-w-[40px]">
        <div
          style={{
            width: `${clampedPercentage}%`,
            height: '100%',
            backgroundColor: color,
            transition: 'width 0.5s ease-out',
          }}
        />
      </div>
      <span className="text-xs text-gray-600 w-10 text-right">{clampedPercentage.toFixed(0)}%</span>
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

  // Sort VMs: running VMs first (alphabetically), then stopped VMs (alphabetically)
  const sortedVms = useMemo(() => {
    return [...vms].sort((a, b) => {
      const infoA = vmInfoMap[a.name];
      const infoB = vmInfoMap[b.name];
      const isPoweredOnA = infoA?.power_state?.includes('poweredOn') ?? false;
      const isPoweredOnB = infoB?.power_state?.includes('poweredOn') ?? false;

      // First, sort by power state (running first)
      if (isPoweredOnA !== isPoweredOnB) {
        return isPoweredOnA ? -1 : 1;
      }

      // Then, sort alphabetically by name
      return a.name.localeCompare(b.name);
    });
  }, [vms, vmInfoMap]);

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
        <h3 className="text-lg font-bold flex items-center gap-2">
          <CloudIcon className="w-5 h-5" />
          仮想マシン ({vms.length}台)
        </h3>
        <button
          className="p-1 bg-transparent border-none cursor-pointer disabled:cursor-wait text-gray-600 hover:text-gray-800 transition-colors"
          onClick={handleRefresh}
          disabled={refreshing}
          title="ESXi から最新データを取得"
        >
          {refreshing ? (
            <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
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
              sortedVms.map((vm) => {
                const info = vmInfoMap[vm.name];
                const powerState = getPowerStateInfo(info?.power_state || null);
                const isPoweredOn = info?.power_state?.includes('poweredOn');

                // Calculate usage percentages
                const memoryUsagePercent = (info?.ram_mb && info?.memory_usage_mb)
                  ? (info.memory_usage_mb / info.ram_mb) * 100
                  : null;

                // For CPU usage, we show MHz value since we don't have max MHz per VM
                // But we can estimate a percentage based on typical assumption (2000 MHz per vCPU as baseline)
                const estimatedCpuMaxMhz = (info?.cpu_count || 1) * 2000;
                const cpuUsagePercent = info?.cpu_usage_mhz
                  ? Math.min((info.cpu_usage_mhz / estimatedCpuMaxMhz) * 100, 100)
                  : null;

                const showUsage = isPoweredOn && (cpuUsagePercent !== null || memoryUsagePercent !== null);

                return (
                  <tr key={vm.name} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="p-2">
                      <div>
                        <span className="inline-flex items-center">
                          <span className="mr-2">🔹</span>
                          <span>{String(vm.name ?? '')}</span>
                        </span>
                        {showUsage && (
                          <div className="mt-1 ml-6 space-y-0.5">
                            {cpuUsagePercent !== null && (
                              <MiniUsageBar
                                percentage={cpuUsagePercent}
                                color="#f14668"
                                label="CPU"
                              />
                            )}
                            {memoryUsagePercent !== null && (
                              <MiniUsageBar
                                percentage={memoryUsagePercent}
                                color="#3298dc"
                                label="MEM"
                              />
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="text-center p-2 align-top">
                      {info?.cpu_count ?? '-'}
                    </td>
                    <td className="text-center p-2 align-top">
                      {formatRam(info?.ram_mb || null)}
                    </td>
                    <td className="text-center p-2 align-top">
                      {formatStorage(info?.storage_gb || null)}
                    </td>
                    <td className="text-center p-2 align-top">
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
