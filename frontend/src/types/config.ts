export interface Storage {
  name: string;
  model: string;
  volume: string;
}

export interface VirtualMachine {
  name: string;
  power_state?: string;
}

export interface Machine {
  name: string;
  mode: string;
  cpu: string;
  ram: string;
  storage: Storage[];
  os: string;
  vm?: VirtualMachine[];
  esxi?: string;
  ilo?: string;
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
  status: 'running' | 'stopped';
  cpu_threads: number | null;
  cpu_cores: number | null;
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
