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
 * Get power state display info (tailwind class and label)
 */
export function getPowerStateInfo(powerState: string | null): { tailwindClass: string; label: string } {
  if (!powerState) return { tailwindClass: 'bg-gray-100 text-gray-700', label: '-' };
  if (powerState.includes('poweredOn')) return { tailwindClass: 'bg-green-500 text-white', label: 'ON' };
  if (powerState.includes('poweredOff')) return { tailwindClass: 'bg-red-500 text-white', label: 'OFF' };
  if (powerState.includes('suspended')) return { tailwindClass: 'bg-yellow-500 text-white', label: 'SUSPENDED' };
  return { tailwindClass: 'bg-gray-100 text-gray-700', label: powerState };
}
