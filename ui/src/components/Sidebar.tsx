import { 
  Activity, 
  Camera, 
  Sliders, 
  Command, 
  Terminal, 
  Radio
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  isEngineActive: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, setCurrentTab, isEngineActive }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'camera', label: 'Optical Hardware', icon: Camera },
    { id: 'sensitivity', label: '1€ Signal Tuning', icon: Sliders },
    { id: 'gestures', label: 'Bimanual Chords', icon: Command },
    { id: 'logs', label: 'Kernel Telemetry', icon: Terminal },
  ];

  return (
    <aside className="w-64 border-r border-white/5 bg-[#0d0d11] flex flex-col justify-between shrink-0 h-screen select-none">
      <div>
        {/* App Title & Status */}
        <div className="h-16 border-b border-white/5 flex items-center px-5 gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Radio className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wider text-white">AEROTOUCH</h1>
            <p className="text-[10px] font-mono tracking-tight text-zinc-400">SPATIAL LAYER v1.0.0</p>
          </div>
        </div>

        {/* Navigation Items */}
        <div className="p-3 space-y-1">
          <p className="px-3 pt-3 pb-1.5 text-[10px] font-mono uppercase tracking-wider text-zinc-400">Navigation</p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-white/10 text-white shadow-sm shadow-black/50 border border-white/10'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-zinc-400'}`} />
                <span>{item.label}</span>
                {isActive && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#00f0ff]" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* System Engine Status Card (Bottom Sidebar) */}
      <div className="p-3 border-t border-white/5">
        <div className="p-3 rounded-lg bg-zinc-900/60 border border-white/5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-zinc-400">WIN32 KERNEL</span>
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium ${
              isEngineActive 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isEngineActive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              {isEngineActive ? 'ONLINE' : 'STANDBY'}
            </span>
          </div>
          <div className="text-[10px] text-zinc-400 font-mono space-y-0.5">
            <div className="flex justify-between">
              <span>Display:</span>
              <span className="text-zinc-300">1920x1080 Native</span>
            </div>
            <div className="flex justify-between">
              <span>Driver:</span>
              <span className="text-zinc-300">Direct ctypes user32</span>
            </div>
            <div className="flex justify-between">
              <span>Polling Rate:</span>
              <span className="text-cyan-400">60 Hz</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
