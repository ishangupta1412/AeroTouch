import { RefreshCw } from 'lucide-react';

interface SensitivitySlidersProps {
  minCutoff: number;
  setMinCutoff: (val: number) => void;
  beta: number;
  setBeta: (val: number) => void;
  margin: number;
  setMargin: (val: number) => void;
  pinchThresh: number;
  setPinchThresh: (val: number) => void;
  onResetDefaults: () => void;
}

export const SensitivitySliders: React.FC<SensitivitySlidersProps> = ({
  minCutoff,
  setMinCutoff,
  beta,
  setBeta,
  margin,
  setMargin,
  pinchThresh,
  setPinchThresh,
  onResetDefaults,
}) => {
  return (
    <div className="p-5 rounded-xl bg-[#111115] border border-white/5 space-y-5">
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div>
          <h3 className="text-sm font-semibold text-white">1€ Adaptive Dynamic Signal Tuning</h3>
          <p className="text-xs text-zinc-400">
            Tune velocity-modulated cutoff thresholds to eliminate hand tremors without incurring phase lag.
          </p>
        </div>
        <button
          onClick={onResetDefaults}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono text-zinc-400 hover:text-white bg-white/5 hover:bg-white/10 transition-colors border border-white/5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reset Defaults</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Slider 1: Minimum Cutoff */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-zinc-300">Resting Jitter Cutoff (fc_min)</span>
            <span className="font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
              {minCutoff.toFixed(2)} Hz
            </span>
          </div>
          <input
            type="range"
            min="0.1"
            max="3.0"
            step="0.05"
            value={minCutoff}
            onChange={(e) => setMinCutoff(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
          <p className="text-[11px] text-zinc-400">
            Lower = zero tremors when holding still. Higher = faster response at dead stop.
          </p>
        </div>

        {/* Slider 2: Dynamic Velocity Beta */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-zinc-300">Velocity Coefficient (Beta)</span>
            <span className="font-mono text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
              {beta.toFixed(3)}
            </span>
          </div>
          <input
            type="range"
            min="0.001"
            max="0.08"
            step="0.001"
            value={beta}
            onChange={(e) => setBeta(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-purple-400"
          />
          <p className="text-[11px] text-zinc-400">
            Modulates cutoff when sweeping across screen. Eliminates cursor trailing behind fast hand movements.
          </p>
        </div>

        {/* Slider 3: Ergonomic Margin */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-zinc-300">Corner Reach Padding (Ergonomic Envelope)</span>
            <span className="font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              {(margin * 100).toFixed(0)}%
            </span>
          </div>
          <input
            type="range"
            min="0.05"
            max="0.30"
            step="0.01"
            value={margin}
            onChange={(e) => setMargin(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-emerald-400"
          />
          <p className="text-[11px] text-zinc-400">
            Allows reaching physical screen borders without extending arms beyond a comfortable 60° posture.
          </p>
        </div>

        {/* Slider 4: Pinch Trigger Distance */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-zinc-300">Scale-Invariant Pinch Threshold</span>
            <span className="font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
              {pinchThresh.toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min="0.15"
            max="0.45"
            step="0.01"
            value={pinchThresh}
            onChange={(e) => setPinchThresh(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
          />
          <p className="text-[11px] text-zinc-400">
            Euclidean distance between thumb tip and index tip relative to wrist-to-MCP scale anchor.
          </p>
        </div>
      </div>
    </div>
  );
};
