import { useState } from 'react';
import { Camera, Smartphone, Usb, Globe, Check } from 'lucide-react';

interface DeviceSelectorProps {
  selectedCamera: string;
  setSelectedCamera: (id: string) => void;
  flipMirror: boolean;
  setFlipMirror: (val: boolean) => void;
}

export const DeviceSelector: React.FC<DeviceSelectorProps> = ({
  selectedCamera,
  setSelectedCamera,
  flipMirror,
  setFlipMirror,
}) => {
  const [ipUrl, setIpUrl] = useState('http://192.168.1.45:8080/video');

  const devices = [
    {
      id: 'cam_0',
      name: 'Integrated HD Webcam (Default)',
      subtext: 'Built-in Laptop Camera • 1280x720 60 FPS',
      icon: Camera,
      badge: 'Hardware Direct',
    },
    {
      id: 'cam_1',
      name: 'External USB Video Device',
      subtext: 'External UVC Web Camera • 1920x1080 30 FPS',
      icon: Usb,
      badge: 'USB 3.0',
    },
    {
      id: 'phone_droidcam',
      name: 'Phone as Optical Sensor (DroidCam / Iriun)',
      subtext: 'Ultra-low latency WiFi / USB tether stream',
      icon: Smartphone,
      badge: 'Recommended for 60FPS',
    },
    {
      id: 'ip_rtsp',
      name: 'IP Camera / RTSP Stream Source',
      subtext: 'Local area network optical sensor',
      icon: Globe,
      badge: 'Network RTSP',
    },
  ];

  return (
    <div className="p-5 rounded-xl bg-[#111115] border border-white/5 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div>
          <h3 className="text-sm font-semibold text-white">Optical Sensor Hardware Selector</h3>
          <p className="text-xs text-zinc-400">
            Select physical camera pipeline or tether a mobile device as a high-precision 60 FPS vision sensor.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 cursor-pointer text-xs font-mono text-zinc-300 bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-md border border-white/5">
            <input
              type="checkbox"
              checked={flipMirror}
              onChange={(e) => setFlipMirror(e.target.checked)}
              className="rounded bg-zinc-800 border-zinc-700 text-cyan-400 focus:ring-0"
            />
            <span>Mirror Selfie Stream</span>
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {devices.map((dev) => {
          const Icon = dev.icon;
          const isSelected = selectedCamera === dev.id;
          return (
            <div
              key={dev.id}
              onClick={() => setSelectedCamera(dev.id)}
              className={`p-3.5 rounded-lg border transition-all cursor-pointer flex items-start gap-3.5 ${
                isSelected
                  ? 'bg-cyan-500/[0.06] border-cyan-500/40 shadow-sm shadow-cyan-950/20'
                  : 'bg-zinc-900/40 border-white/5 hover:border-white/10 hover:bg-white/[0.02]'
              }`}
            >
              <div className={`p-2.5 rounded-lg shrink-0 ${
                isSelected ? 'bg-cyan-500/20 text-cyan-400' : 'bg-white/5 text-zinc-400'
              }`}>
                <Icon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-xs font-semibold text-white truncate">{dev.name}</h4>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                    isSelected ? 'bg-cyan-500/20 text-cyan-300' : 'bg-white/5 text-zinc-400'
                  }`}>
                    {dev.badge}
                  </span>
                </div>
                <p className="text-[11px] text-zinc-400 mt-0.5">{dev.subtext}</p>
              </div>
              {isSelected && (
                <div className="w-5 h-5 rounded-full bg-cyan-400/20 border border-cyan-400/50 flex items-center justify-center text-cyan-400 shrink-0 mt-0.5">
                  <Check className="w-3 h-3 stroke-[3]" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {selectedCamera === 'ip_rtsp' && (
        <div className="mt-3 p-3 rounded-lg bg-zinc-900/80 border border-white/5 flex items-center gap-3">
          <Globe className="w-4 h-4 text-cyan-400 shrink-0" />
          <input
            type="text"
            value={ipUrl}
            onChange={(e) => setIpUrl(e.target.value)}
            placeholder="http://192.168.x.x:8080/video or rtsp://..."
            className="flex-1 bg-transparent text-xs font-mono text-zinc-200 outline-none placeholder:text-zinc-400"
          />
          <button className="px-3 py-1 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 rounded text-xs font-mono border border-cyan-500/30">
            Connect
          </button>
        </div>
      )}
    </div>
  );
};
