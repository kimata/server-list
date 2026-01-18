import { Link } from 'react-router-dom';
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

function getImageUrl(upsName: string, model: string | null): string {
  // Try to find image by model name first, then by ups_name
  // The image filename should match the model name (e.g., "BL100T.png")
  const imageName = model?.replace(/\s+/g, '') || upsName.toUpperCase();
  return `/server-list/api/img/${encodeURIComponent(imageName)}.png`;
}

export function UPSCard({ ups }: UPSCardProps) {
  const statusBadge = getStatusBadge(ups.ups_status);
  const displayName = ups.model || ups.ups_name.toUpperCase();
  const imageUrl = getImageUrl(ups.ups_name, ups.model);

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <header className="card-header-gradient px-4 py-3 flex justify-between items-center">
        <div>
          <p className="text-white font-semibold flex items-center gap-2">
            <span>🔋</span>
            <span>{displayName}</span>
          </p>
          <p className="text-white/70 text-sm">
            NUT Master: {ups.host}
          </p>
        </div>
        <span className={`inline-flex items-center px-2 py-1 ${statusBadge.color} text-xs rounded`}>
          {statusBadge.text}
        </span>
      </header>

      <div className="p-4">
        {/* Image and basic info */}
        <div className="flex gap-4 mb-4">
          <div className="w-24 h-24 flex-shrink-0">
            <img
              src={imageUrl}
              alt={displayName}
              className="w-full h-full object-contain"
              onError={(e) => {
                // Hide image on error
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
          <div className="flex-1">
            {/* UPS Name (internal) */}
            <div className="mb-2">
              <div className="inline-flex rounded overflow-hidden">
                <span className="px-2 py-0.5 bg-gray-800 text-white text-xs">NUT 名</span>
                <span className="px-2 py-0.5 bg-gray-100 text-gray-800 text-xs">{ups.ups_name}</span>
              </div>
            </div>

            {/* Runtime and Temperature in compact format */}
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-500">残り時間: </span>
                <span className="font-semibold">{formatRuntime(ups.battery_runtime)}</span>
              </div>
              {ups.ups_temperature !== null && (
                <div>
                  <span className="text-gray-500">温度: </span>
                  <span className="font-semibold">{ups.ups_temperature}°C</span>
                </div>
              )}
            </div>
          </div>
        </div>

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
                {ups.clients.map((client, index) => {
                  const displayName = client.client_hostname || client.client_ip;
                  const isVM = !!client.esxi_host;
                  const linkTarget = client.machine_name;

                  return (
                    <div
                      key={index}
                      className="flex items-center gap-2 text-sm"
                    >
                      <span className={`inline-block w-2 h-2 rounded-full ${isVM ? 'bg-blue-500' : 'bg-green-500'}`} />
                      {linkTarget ? (
                        <Link
                          to={`/machine/${encodeURIComponent(linkTarget)}`}
                          className="text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          {displayName}
                        </Link>
                      ) : (
                        <span className="text-gray-600">{displayName}</span>
                      )}
                      {isVM && (
                        <span className="text-xs text-gray-400">
                          (VM on {client.esxi_host})
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
