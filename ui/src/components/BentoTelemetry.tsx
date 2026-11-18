import { Hand, MousePointer2, Zap, ShieldCheck } from 'lucide-react';

interface BentoTelemetryProps {
  leftMode: string;
  rightAction: string;
  pinchDistance: number;
  fps: number;
  latencyMs: number;
}

export const BentoTelemetry: React.FC<BentoTelemetryProps> = ({
  leftMode,
  rightAction,
  pinchDistance,
  fps,
  latencyMs,
}) => {
  const isPinching = pinchDistance < 0.28;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
      {/* Tile 1: Left Hand Modifier */}
      <div className="p-4 rounded-xl bg-[#111115] border border-white/5 hover:border-white/10 transition-colors">
        <div className="flex items-center justify-between text-zinc-400 mb-2">
          <span className="text-[11px] font-mono tracking-wider uppercase">Left Hand Modifier</span>
          <Hand className="w-4 h-4 text-amber-400" />
        </div>
        <div className="text-sm font-semibold text-white tracking-wide">{leftMode}</div>
        <p className="text-[11px] text-zinc-400 font-mono mt-1">
          Binding: <span className="text-amber-400/90 font-medium">Win + Arrow Snap</span>
        </p>
      </div>

      {/* Tile 2: Right Hand Action */}
      <div className="p-4 rounded-xl bg-[#111115] border border-white/5 hover:border-white/10 transition-colors">
        <div className="flex items-center justify-between text-zinc-400 mb-2">
          <span className="text-[11px] font-mono tracking-wider uppercase">Right Hand Pointer</span>
          <MousePointer2 className="w-4 h-4 text-cyan-400" />
        </div>
        <div className="text-sm font-semibold text-white tracking-wide">{rightAction}</div>
        <div className="mt-2 flex items-center justify-between text-[11px] font-mono">
          <span className="text-zinc-400">Pinch Delta:</span>
          <span className={isPinching ? 'text-emerald-400 font-medium' : 'text-zinc-400'}>
            {pinchDistance.toFixed(2)} {isPinching && '[ACTIVE]'}
          </span>
        </div>
        <div className="w-full bg-zinc-800/80 rounded-full h-1 mt-1.5 overflow-hidden">
          <div 
            className={`h-full transition-all duration-75 ${isPinching ? 'bg-cyan-400 shadow-[0_0_8px_#00f0ff]' : 'bg-zinc-600'}`}
            style={{ width: `${Math.min(100, (pinchDistance / 0.5) * 100)}%` }}
          />
        </div>
      </div>

      {/* Tile 3: 1€ Filter Signal Metric */}
      <div className="p-4 rounded-xl bg-[#111115] border border-white/5 hover:border-white/10 transition-colors">
        <div className="flex items-center justify-between text-zinc-400 mb-2">
          <span className="text-[11px] font-mono tracking-wider uppercase">1€ Jitter Filter</span>
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-sm font-semibold text-white tracking-wide">Tremor Damped</div>
        <div className="mt-1 flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <span>Static Noise:</span>
          <span className="text-emerald-400">&lt; 0.25 px</span>
        </div>
        <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <span>Dynamic Beta:</span>
          <span className="text-zinc-300">0.015 Adaptive</span>
        </div>
      </div>

      {/* Tile 4: Hardware Latency */}
      <div className="p-4 rounded-xl bg-[#111115] border border-white/5 hover:border-white/10 transition-colors">
        <div className="flex items-center justify-between text-zinc-400 mb-2">
          <span className="text-[11px] font-mono tracking-wider uppercase">Pipeline Latency</span>
          <Zap className="w-4 h-4 text-purple-400" />
        </div>
        <div className="text-sm font-semibold text-white tracking-wide">{fps} FPS Continuous</div>
        <div className="mt-1 flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <span>Frame Dispatch:</span>
          <span className="text-cyan-400 font-medium">{latencyMs.toFixed(1)} ms</span>
        </div>
        <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <span>Drop Rate:</span>
          <span className="text-emerald-400">0.0%</span>
        </div>
      </div>
    </div>
  );
};
