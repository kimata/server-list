import type { Machine } from '../types/config';

/**
 * Parse RAM string (e.g., "64 GB", "1 TB") to GB value
 */
export function parseRam(ram: string | undefined | null): number {
  if (!ram || typeof ram !== 'string') return 0;
  const match = ram.match(/([\d.]+)\s*(GB|TB|MB)/i);
  if (!match) return 0;

  const value = parseFloat(match[1]);
  const unit = match[2].toUpperCase();

  switch (unit) {
    case 'TB':
      return value * 1024;
    case 'GB':
      return value;
    case 'MB':
      return value / 1024;
    default:
      return value;
  }
}

/**
 * Parse storage volume string (e.g., "1 TB", "500 GB") to GB value
 */
export function parseStorage(volume: string | undefined | null): number {
  if (!volume || typeof volume !== 'string') return 0;
  const match = volume.match(/([\d.]+)\s*(TB|GB|MB)/i);
  if (!match) return 0;

  const value = parseFloat(match[1]);
  const unit = match[2].toUpperCase();

  switch (unit) {
    case 'TB':
      return value * 1024;
    case 'GB':
      return value;
    case 'MB':
      return value / 1024;
    default:
      return value;
  }
}

/**
 * Calculate total storage for a machine in GB
 */
export function getTotalStorage(machine: Machine): number {
  if (!machine.storage || !Array.isArray(machine.storage)) {
    return 0;
  }
  return machine.storage.reduce((total, disk) => total + parseStorage(disk.volume), 0);
}
