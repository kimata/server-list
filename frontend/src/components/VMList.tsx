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

  const getPowerStateColor = (powerState: string | null): string => {
    if (!powerState) return '';
    if (powerState.includes('poweredOn')) return 'is-success';
    if (powerState.includes('poweredOff')) return 'is-danger';
    if (powerState.includes('suspended')) return 'is-warning';
    return 'is-light';
  };

  return (
    <div className="vm-list">
      <h4 className="title is-6">
        ☁️ 仮想マシン ({vms.length}台)
      </h4>
      <div className="tags are-medium">
        {vms.map((vm, index) => (
          <span
            key={index}
            className="tag is-success is-light vm-tag"
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
          <div className="box" style={{ padding: '0.75rem', minWidth: '200px' }}>
            <p className="has-text-weight-bold mb-2">{tooltip.vmName}</p>
            {tooltip.loading ? (
              <p className="has-text-grey is-size-7">読み込み中...</p>
            ) : tooltip.vmInfo ? (
              <div className="is-size-7">
                <div className="columns is-mobile is-gapless mb-1">
                  <div className="column is-5 has-text-grey">CPU:</div>
                  <div className="column">{tooltip.vmInfo.cpu_count ?? '-'} vCPU</div>
                </div>
                <div className="columns is-mobile is-gapless mb-1">
                  <div className="column is-5 has-text-grey">RAM:</div>
                  <div className="column">{formatRam(tooltip.vmInfo.ram_mb)}</div>
                </div>
                <div className="columns is-mobile is-gapless mb-1">
                  <div className="column is-5 has-text-grey">Storage:</div>
                  <div className="column">{formatStorage(tooltip.vmInfo.storage_gb)}</div>
                </div>
                {tooltip.vmInfo.power_state && (
                  <div className="columns is-mobile is-gapless">
                    <div className="column is-5 has-text-grey">Status:</div>
                    <div className="column">
                      <span className={`tag is-small ${getPowerStateColor(tooltip.vmInfo.power_state)}`}>
                        {tooltip.vmInfo.power_state.replace('poweredOn', 'ON').replace('poweredOff', 'OFF')}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="has-text-grey is-size-7">情報なし</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
