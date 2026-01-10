import type { Machine, CpuBenchmark, UptimeInfo, PowerInfo } from '../types/config';
import { StorageInfo } from './StorageInfo';
import { PerformanceBar } from './PerformanceBar';
import { UptimeDisplay } from './UptimeDisplay';
import { ServerImage } from './ServerImage';
import { parseRam, getTotalStorage } from '../utils/parsing';

interface ServerCardProps {
  machine: Machine;
  cpuBenchmark?: CpuBenchmark | null;
  maxCpuScore: number;
  maxRam: number;
  maxStorage: number;
  uptimeInfo?: UptimeInfo | null;
  powerInfo?: PowerInfo | null;
  onClick?: () => void;
}

export function ServerCard({
  machine,
  cpuBenchmark,
  maxCpuScore,
  maxRam,
  maxStorage,
  uptimeInfo,
  powerInfo,
  onClick,
}: ServerCardProps) {
  const ramGb = parseRam(machine.ram);
  const totalStorageGb = getTotalStorage(machine);

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't navigate if clicking on a link
    if ((e.target as HTMLElement).closest('a')) {
      return;
    }
    if (onClick) {
      onClick();
    }
  };

  return (
    <div
      className={`server-card bg-white rounded-lg shadow overflow-hidden ${onClick ? 'is-clickable' : ''}`}
      onClick={handleCardClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <header className="card-header-gradient px-4 py-3 flex justify-between items-center">
        <p className="text-white font-semibold">
          {String(machine.name ?? '')}
        </p>
        <span className="flex items-center gap-2">
          {machine.esxi && (
            <a href={machine.esxi} target="_blank" rel="noopener noreferrer" className="management-link" title="ESXi" onClick={(e) => e.stopPropagation()}>
              <span className="inline-block px-2 py-0.5 bg-blue-500 text-white text-xs rounded">ESXi</span>
            </a>
          )}
          {machine.ilo && (
            <a href={machine.ilo} target="_blank" rel="noopener noreferrer" className="management-link" title="iLO" onClick={(e) => e.stopPropagation()}>
              <span className="inline-block px-2 py-0.5 bg-yellow-500 text-white text-xs rounded">iLO</span>
            </a>
          )}
          <span className="inline-block px-2 py-0.5 bg-purple-500 text-white text-xs rounded">
            {String((uptimeInfo?.esxi_version ?? machine.os ?? '').replace(/^VMware\s+/i, ''))}
          </span>
        </span>
      </header>
      <div className="p-4">
        <div className="flex gap-4">
          {/* Server Image */}
          <ServerImage modelName={machine.mode} />

          {/* Server Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <div className="inline-flex rounded overflow-hidden flex-shrink-0">
                <span className="px-2 py-0.5 bg-gray-800 text-white text-xs">モデル</span>
                <span className="px-2 py-0.5 bg-gray-100 text-gray-800 text-xs">{String(machine.mode ?? '')}</span>
              </div>
              <div className="flex items-center gap-2">
                {powerInfo?.power_watts != null && (
                  <span className="inline-flex items-center px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">
                    <span className="mr-1">⚡</span>
                    <span>{powerInfo.power_watts} W</span>
                  </span>
                )}
                {machine.os?.toLowerCase().includes('esxi') && (
                  <UptimeDisplay uptimeInfo={uptimeInfo || null} hostName={machine.name} />
                )}
              </div>
            </div>

            <div className="specs-section">
              <div className="spec-item mb-3">
                <div className="flex items-center mb-1">
                  <span className="inline-block px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs mr-2">CPU</span>
                  <span className="text-xs">{String(machine.cpu ?? '')}</span>
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
              </div>

              <div className="spec-item mb-3">
                <PerformanceBar
                  label="RAM"
                  value={ramGb}
                  maxValue={maxRam}
                  unit=" GB"
                  color="#3298dc"
                  icon=""
                />
              </div>

              <div className="spec-item mb-3">
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
        </div>

        <hr className="my-4 border-gray-200" />

        <StorageInfo storage={machine.storage} />

        {machine.vm && machine.vm.length > 0 && (
          <>
            <hr className="my-4 border-gray-200" />
            <div className="vm-summary">
              <h4 className="text-sm font-bold mb-2">
                仮想マシン ({machine.vm.length}台)
              </h4>
              <div className="flex flex-wrap gap-1">
                {[...machine.vm]
                  .sort((a, b) => {
                    // Sort by power state first (poweredOn first), then alphabetically
                    const aOn = a.power_state?.includes('poweredOn') ? 0 : 1;
                    const bOn = b.power_state?.includes('poweredOn') ? 0 : 1;
                    if (aOn !== bOn) return aOn - bOn;
                    return a.name.localeCompare(b.name);
                  })
                  .slice(0, 5)
                  .map((vm, index) => {
                    const isPoweredOn = vm.power_state?.includes('poweredOn');
                    const tagClass = isPoweredOn
                      ? 'inline-block px-2 py-1 bg-green-100 text-green-700 rounded text-xs'
                      : 'inline-block px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs';
                    return (
                      <span key={index} className={tagClass}>
                        {String(vm.name ?? '')}
                      </span>
                    );
                  })}
                {machine.vm.length > 5 && (
                  <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                    +{machine.vm.length - 5} more
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-2">
                クリックして詳細を表示
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
