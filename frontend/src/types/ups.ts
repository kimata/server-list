export interface UPSClient {
  ups_name: string;
  host: string;
  client_ip: string;
  client_hostname: string | null;
  esxi_host: string | null;  // If client is a VM, the ESXi host running it
  machine_name: string | null;  // Machine name for linking
  collected_at: string | null;
}

export interface UPSInfo {
  ups_name: string;
  host: string;
  model: string | null;
  battery_charge: number | null;  // %
  battery_runtime: number | null; // seconds
  ups_load: number | null;        // %
  ups_status: string | null;      // OL, OB, etc.
  ups_temperature: number | null; // °C
  input_voltage: number | null;
  output_voltage: number | null;
  collected_at: string | null;
  clients: UPSClient[];
}

export interface UPSResponse {
  success: boolean;
  data?: UPSInfo[];
  error?: string;
}

export interface UPSDetailResponse {
  success: boolean;
  data?: UPSInfo;
  error?: string;
}
