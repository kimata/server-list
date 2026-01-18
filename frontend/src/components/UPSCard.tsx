import type { UPSInfo } from '../types/ups';

interface UPSCardProps {
  ups: UPSInfo;
}

function getStatusBadge(status: string | null) {
  if (!status) return { text: '不明', color: 'bg-gray-100 text-gray-700' };

  // NUT status codes
  if (status.includes('OL')) {
    return { text: 'オンライン', color: 'bg-green-100 text-green-700' };
  }
  if (status.includes('OB')) {
    return { text: 'バッテリー駆動', color: 'bg-yellow-100 text-yellow-700' };
  }
  if (status.includes('LB')) {
    return { text: 'バッテリー低下', color: 'bg-red-100 text-red-700' };
  }
  if (status.includes('CHRG')) {
    return { text: '充電中', color: 'bg-blue-100 text-blue-700' };
  }
  if (status.includes('DISCHRG')) {
    return { text: '放電中', color: 'bg-orange-100 text-orange-700' };
  }

  return { text: status, color: 'bg-gray-100 text-gray-700' };
}

function formatRuntime(seconds: number | null): string {
  if (seconds === null) return '-';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}時間${minutes}分`;
  }
  return `${minutes}分`;
}

export function UPSCard({ ups }: UPSCardProps) {
  const statusBadge = getStatusBadge(ups.ups_status);

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <header className="card-header-gradient px-4 py-3 flex justify-between items-center">
        <p className="text-white font-semibold flex items-center gap-2">
          <span>🔋</span>
          <span>{ups.ups_name}@{ups.host}</span>
        </p>
        <span className={`inline-flex items-center px-2 py-1 ${statusBadge.color} text-xs rounded`}>
          {statusBadge.text}
        </span>
      </header>

      <div className="p-4">
        {/* Model */}
        {ups.model && (
          <div className="mb-3">
            <div className="inline-flex rounded overflow-hidden">
              <span className="px-2 py-0.5 bg-gray-800 text-white text-xs">モデル</span>
              <span className="px-2 py-0.5 bg-gray-100 text-gray-800 text-xs">{ups.model}</span>
            </div>
          </div>
        )}

        {/* Battery and Load */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Battery Charge */}
          <div>
            <div className="text-xs text-gray-500 mb-1">バッテリー残量</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 rounded-full h-4 overflow-hidden">
                <div
                  className={`h-full transition-all ${
                    (ups.battery_charge ?? 0) > 50
                      ? 'bg-green-500'
                      : (ups.battery_charge ?? 0) > 20
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                  }`}
                  style={{ width: `${ups.battery_charge ?? 0}%` }}
                />
              </div>
              <span className="text-sm font-medium w-12 text-right">
                {ups.battery_charge !== null ? `${ups.battery_charge}%` : '-'}
              </span>
            </div>
          </div>

          {/* UPS Load */}
          <div>
            <div className="text-xs text-gray-500 mb-1">負荷率</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 rounded-full h-4 overflow-hidden">
                <div
                  className={`h-full transition-all ${
                    (ups.ups_load ?? 0) < 50
                      ? 'bg-green-500'
                      : (ups.ups_load ?? 0) < 80
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                  }`}
                  style={{ width: `${ups.ups_load ?? 0}%` }}
                />
              </div>
              <span className="text-sm font-medium w-12 text-right">
                {ups.ups_load !== null ? `${ups.ups_load}%` : '-'}
              </span>
            </div>
          </div>
        </div>

        {/* Runtime and Temperature */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <div className="text-xs text-gray-500 mb-1">残り稼働時間</div>
            <div className="text-lg font-semibold text-gray-800">
              {formatRuntime(ups.battery_runtime)}
            </div>
          </div>
          {ups.ups_temperature !== null && (
            <div>
              <div className="text-xs text-gray-500 mb-1">温度</div>
              <div className="text-lg font-semibold text-gray-800">
                {ups.ups_temperature}°C
              </div>
            </div>
          )}
        </div>

        {/* Voltage */}
        {(ups.input_voltage !== null || ups.output_voltage !== null) && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            {ups.input_voltage !== null && (
              <div>
                <div className="text-xs text-gray-500 mb-1">入力電圧</div>
                <div className="text-sm text-gray-800">{ups.input_voltage} V</div>
              </div>
            )}
            {ups.output_voltage !== null && (
              <div>
                <div className="text-xs text-gray-500 mb-1">出力電圧</div>
                <div className="text-sm text-gray-800">{ups.output_voltage} V</div>
              </div>
            )}
          </div>
        )}

        {/* Connected Clients */}
        {ups.clients && ups.clients.length > 0 && (
          <>
            <hr className="my-4 border-gray-200" />
            <div>
              <h4 className="text-sm font-bold mb-2 flex items-center gap-1">
                <span>🖥️</span>
                <span>接続クライアント ({ups.clients.length}台)</span>
              </h4>
              <div className="space-y-1">
                {ups.clients.map((client, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 text-sm text-gray-600"
                  >
                    <span className="inline-block w-2 h-2 bg-green-500 rounded-full" />
                    <span>{client.client_hostname || client.client_ip}</span>
                    {client.client_hostname && (
                      <span className="text-xs text-gray-400">({client.client_ip})</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
