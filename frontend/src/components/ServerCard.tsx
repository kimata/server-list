import type { Machine, CpuBenchmark, UptimeInfo } from '../types/config';
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
  onClick?: () => void;
}

export function ServerCard({
  machine,
  cpuBenchmark,
  maxCpuScore,
  maxRam,
  maxStorage,
  uptimeInfo,
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
      className={`card server-card ${onClick ? 'is-clickable' : ''}`}
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
      <header className="card-header">
        <p className="card-header-title">
          {String(machine.name ?? '')}
        </p>
        <span className="card-header-icon">
          {machine.esxi && (
            <a href={machine.esxi} target="_blank" rel="noopener noreferrer" className="management-link mr-2" title="ESXi" onClick={(e) => e.stopPropagation()}>
              <span className="tag is-link">ESXi</span>
            </a>
          )}
          {machine.ilo && (
            <a href={machine.ilo} target="_blank" rel="noopener noreferrer" className="management-link mr-2" title="iLO" onClick={(e) => e.stopPropagation()}>
              <span className="tag is-warning">iLO</span>
            </a>
          )}
          <span className="tag is-primary">{String(machine.os ?? '')}</span>
        </span>
      </header>
      <div className="card-content">
        <div className="content">
          <div className="is-flex is-align-items-start" style={{ gap: '1rem' }}>
            {/* Server Image */}
            <ServerImage modelName={machine.mode} />

            {/* Server Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="is-flex is-align-items-center is-justify-content-space-between mb-3">
                <div className="tags has-addons mb-0">
                  <span className="tag is-dark">モデル</span>
                  <span className="tag is-light">{String(machine.mode ?? '')}</span>
                </div>
                <UptimeDisplay uptimeInfo={uptimeInfo || null} hostName={machine.name} />
              </div>

              <div className="specs-section">
                <div className="spec-item mb-3">
                  <div className="is-flex is-align-items-center mb-1">
                    <span className="tag is-warning is-light mr-2">CPU</span>
                    <span className="is-size-7">{String(machine.cpu ?? '')}</span>
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

          <hr />

          <StorageInfo storage={machine.storage} />

          {machine.vm && machine.vm.length > 0 && (
            <>
              <hr />
              <div className="vm-summary">
                <h4 className="title is-6">
                  仮想マシン ({machine.vm.length}台)
                </h4>
                <div className="tags are-medium">
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
                      const tagClass = isPoweredOn ? 'tag is-success is-light' : 'tag is-light';
                      return (
                        <span key={index} className={tagClass}>
                          {String(vm.name ?? '')}
                        </span>
                      );
                    })}
                  {machine.vm.length > 5 && (
                    <span className="tag is-light">
                      +{machine.vm.length - 5} more
                    </span>
                  )}
                </div>
                <p className="is-size-7 has-text-grey mt-2">
                  クリックして詳細を表示
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
