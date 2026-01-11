export interface Storage {
  name: string;
  model: string;
  volume: string;
}

export interface VirtualMachine {
  name: string;
  power_state?: string;
}

export interface MountConfig {
  label: string;
  path?: string;
  type?: 'btrfs' | 'filesystem' | 'windows';
}

export interface Machine {
  name: string;
  mode: string;
  cpu: string;
  ram: string;
  storage: Storage[] | 'zfs';
  os: string;
  vm?: VirtualMachine[];
  esxi?: string;
  ilo?: string;
  mount?: MountConfig[];
}

export interface Config {
  machine: Machine[];
}

export interface CpuBenchmark {
  cpu_name: string;
  multi_thread_score: number | null;
  single_thread_score: number | null;
}

export interface CpuBenchmarkResponse {
  success: boolean;
  data?: CpuBenchmark;
  error?: string;
}

export interface VMInfo {
  vm_name: string;
  cpu_count: number | null;
  ram_mb: number | null;
  storage_gb: number | null;
  power_state: string | null;
  cached_power_state: string | null;
  esxi_host: string;
}

export interface VMInfoResponse {
  success: boolean;
  data?: VMInfo;
  error?: string;
}

export interface UptimeInfo {
  boot_time: string | null;
  uptime_seconds: number | null;
  status: 'running' | 'stopped' | 'unknown';
  cpu_threads: number | null;
  cpu_cores: number | null;
  esxi_version: string | null;
  collected_at: string;
}

export interface UptimeData {
  [host: string]: UptimeInfo;
}

export interface UptimeResponse {
  success: boolean;
  data?: UptimeData;
  error?: string;
}

export interface PowerInfo {
  power_watts: number | null;
  power_average_watts: number | null;
  power_max_watts: number | null;
  power_min_watts: number | null;
  collected_at: string;
}

export interface PowerData {
  [host: string]: PowerInfo;
}

export interface PowerResponse {
  success: boolean;
  data?: PowerData;
  error?: string;
}

export interface ZfsPoolInfo {
  pool_name: string;
  size_bytes: number | null;
  allocated_bytes: number | null;
  free_bytes: number | null;
  health: number | null;
  collected_at: string;
}

export interface ZfsPoolResponse {
  success: boolean;
  data?: ZfsPoolInfo[];
  error?: string;
}

export interface MountInfo {
  mountpoint: string;
  size_bytes: number | null;
  avail_bytes: number | null;
  used_bytes: number | null;
  collected_at: string;
}

export interface MountInfoResponse {
  success: boolean;
  data?: MountInfo[];
  error?: string;
}
