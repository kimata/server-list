import { useState, useCallback } from 'react';
import type { VirtualMachine, VMInfo } from '../types/config';

interface VMListProps {
  vms: VirtualMachine[];
  esxiHost?: string;
}

interface TooltipState {
  visible: boolean;
  vmName: string;
  vmInfo: VMInfo | null;
  loading: boolean;
  x: number;
  y: number;
}

export function VMList({ vms, esxiHost }: VMListProps) {
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    vmName: '',
    vmInfo: null,
    loading: false,
    x: 0,
    y: 0,
  });

  const fetchVMInfo = useCallback(async (vmName: string) => {
    try {
      const params = new URLSearchParams({ vm_name: vmName });
      if (esxiHost) {
        params.append('esxi_host', esxiHost);
      }
      const response = await fetch(`/server-list/api/vm/info?${params}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          return data.data as VMInfo;
        }
      }
    } catch {
      // API not available
    }
    return null;
  }, [esxiHost]);

  const handleMouseEnter = useCallback(async (e: React.MouseEvent, vmName: string) => {
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    setTooltip({
      visible: true,
      vmName,
      vmInfo: null,
      loading: true,
      x: rect.left + rect.width / 2,
      y: rect.top,
    });

    const vmInfo = await fetchVMInfo(vmName);
    setTooltip(prev => ({
      ...prev,
      vmInfo,
      loading: false,
    }));
  }, [fetchVMInfo]);

  const handleMouseLeave = useCallback(() => {
    setTooltip(prev => ({ ...prev, visible: false }));
  }, []);

  if (!vms || vms.length === 0) {
    return null;
  }

  const formatRam = (ramMb: number | null): string => {
    if (ramMb === null) return '-';
    if (ramMb >= 1024) {
      return `${(ramMb / 1024).toFixed(1)} GB`;
    }
    return `${ramMb} MB`;
  };

  const formatStorage = (storageGb: number | null): string => {
    if (storageGb === null) return '-';
    if (storageGb >= 1024) {
      return `${(storageGb / 1024).toFixed(2)} TB`;
    }
    return `${storageGb.toFixed(1)} GB`;
  };

  const getPowerStateClass = (powerState: string | null): string => {
    if (!powerState) return 'bg-gray-100 text-gray-700';
    if (powerState.includes('poweredOn')) return 'bg-green-500 text-white';
    if (powerState.includes('poweredOff')) return 'bg-red-500 text-white';
    if (powerState.includes('suspended')) return 'bg-yellow-500 text-white';
    return 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="vm-list">
      <h4 className="text-sm font-bold mb-2">
        ☁️ 仮想マシン ({vms.length}台)
      </h4>
      <div className="flex flex-wrap gap-1">
        {vms.map((vm, index) => (
          <span
            key={index}
            className="vm-tag inline-block px-2 py-1 bg-green-100 text-green-700 rounded text-xs"
            onMouseEnter={(e) => handleMouseEnter(e, vm.name)}
            onMouseLeave={handleMouseLeave}
          >
            🔹 {vm.name}
          </span>
        ))}
      </div>

      {tooltip.visible && (
        <div
          className="vm-tooltip"
          style={{
            position: 'fixed',
            left: tooltip.x,
            top: tooltip.y - 10,
            transform: 'translate(-50%, -100%)',
            zIndex: 1000,
          }}
        >
          <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-3 min-w-[200px]">
            <p className="font-bold mb-2">{tooltip.vmName}</p>
            {tooltip.loading ? (
              <p className="text-gray-500 text-xs">読み込み中...</p>
            ) : tooltip.vmInfo ? (
              <div className="text-xs">
                <div className="flex gap-0 mb-1">
                  <div className="w-16 text-gray-500">CPU:</div>
                  <div>{tooltip.vmInfo.cpu_count ?? '-'} vCPU</div>
                </div>
                <div className="flex gap-0 mb-1">
                  <div className="w-16 text-gray-500">RAM:</div>
                  <div>{formatRam(tooltip.vmInfo.ram_mb)}</div>
                </div>
                <div className="flex gap-0 mb-1">
                  <div className="w-16 text-gray-500">Storage:</div>
                  <div>{formatStorage(tooltip.vmInfo.storage_gb)}</div>
                </div>
                {tooltip.vmInfo.power_state && (
                  <div className="flex gap-0">
                    <div className="w-16 text-gray-500">Status:</div>
                    <div>
                      <span className={`inline-block px-2 py-0.5 rounded text-xs ${getPowerStateClass(tooltip.vmInfo.power_state)}`}>
                        {tooltip.vmInfo.power_state.replace('poweredOn', 'ON').replace('poweredOff', 'OFF')}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500 text-xs">情報なし</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
