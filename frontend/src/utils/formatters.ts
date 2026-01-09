/**
 * Format RAM value (in MB) to human-readable string
 */
export function formatRam(ramMb: number | null): string {
  if (ramMb === null) return '-';
  if (ramMb >= 1024) {
    return `${(ramMb / 1024).toFixed(1)} GB`;
  }
  return `${ramMb} MB`;
}

/**
 * Format storage value (in GB) to human-readable string
 */
export function formatStorage(storageGb: number | null): string {
  if (storageGb === null) return '-';
  if (storageGb >= 1024) {
    return `${(storageGb / 1024).toFixed(2)} TB`;
  }
  return `${storageGb.toFixed(1)} GB`;
}

/**
 * Format uptime (in seconds) to human-readable string
 */
export function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  const parts: string[] = [];
  if (days > 0) parts.push(`${days}日`);
  if (hours > 0 || days > 0) parts.push(`${hours}時間`);
  parts.push(`${minutes}分`);

  return parts.join(' ');
}

/**
 * Get power state display info (color class and label)
 */
export function getPowerStateInfo(powerState: string | null): { color: string; label: string } {
  if (!powerState) return { color: 'is-light', label: '-' };
  if (powerState.includes('poweredOn')) return { color: 'is-success', label: 'ON' };
  if (powerState.includes('poweredOff')) return { color: 'is-danger', label: 'OFF' };
  if (powerState.includes('suspended')) return { color: 'is-warning', label: 'SUSPENDED' };
  return { color: 'is-light', label: powerState };
}
