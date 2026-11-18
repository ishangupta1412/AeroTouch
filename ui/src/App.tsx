import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { BentoTelemetry } from './components/BentoTelemetry';
import { SensitivitySliders } from './components/SensitivitySliders';
import { DeviceSelector } from './components/DeviceSelector';
import { HotkeyRemapper } from './components/HotkeyRemapper';
import { WebcamCanvas } from './components/WebcamCanvas';
import { Power, Terminal } from 'lucide-react';

export function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [isEngineActive, setIsEngineActive] = useState(true);
  const [isStreaming, setIsStreaming] = useState(true);

  // Settings State
  const [selectedCamera, setSelectedCamera] = useState('cam_0');
  const [flipMirror, setFlipMirror] = useState(true);
  const [minCutoff, setMinCutoff] = useState(0.8);
  const [beta, setBeta] = useState(0.015);
  const [margin, setMargin] = useState(0.15);
  const [pinchThresh, setPinchThresh] = useState(0.28);

  const handleResetDefaults = () => {
    setMinCutoff(0.8);
    setBeta(0.015);
    setMargin(0.15);
    setPinchThresh(0.28);
  };

  return (
    <div className="flex h-screen bg-[#09090b] text-zinc-100 overflow-hidden font-sans">
      {/* 1. Left Sidebar Navigation */}
      <Sidebar 
        currentTab={currentTab} 
        setCurrentTab={setCurrentTab} 
        isEngineActive={isEngineActive} 
      />

      {/* 2. Main Content Canvas */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-16 border-b border-white/5 bg-[#0d0d11]/80 backdrop-blur-md px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold tracking-wide text-white capitalize">
              {currentTab === 'dashboard' ? 'Overview Cockpit' : currentTab.replace('_', ' ')}
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              Win32 DPI v2 Aware
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsEngineActive(!isEngineActive)}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                isEngineActive
                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 shadow-sm shadow-emerald-950/40'
                  : 'bg-zinc-800 text-zinc-400 border border-white/5 hover:bg-zinc-700'
              }`}
            >
              <Power className="w-3.5 h-3.5" />
              <span>{isEngineActive ? 'Spatial Engine: ACTIVE' : 'Engine: PAUSED'}</span>
            </button>
          </div>
        </header>

        {/* Scrollable Cockpit Content */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Top Bento Metrics */}
          <BentoTelemetry
            leftMode="FIST (WINDOW SNAP)"
            rightAction="INDEX PINCH [CLICK]"
            pinchDistance={0.16}
            fps={60}
            latencyMs={1.2}
          />

          {/* Conditional View by Tab */}
          {currentTab === 'dashboard' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left 7 cols: Live Optical Sensing Feed */}
                <div className="lg:col-span-7">
                  <WebcamCanvas 
                    isStreaming={isStreaming} 
                    onToggleStream={() => setIsStreaming(!isStreaming)} 
                  />
                </div>

                {/* Right 5 cols: Device Selector */}
                <div className="lg:col-span-5">
                  <DeviceSelector
                    selectedCamera={selectedCamera}
                    setSelectedCamera={setSelectedCamera}
                    flipMirror={flipMirror}
                    setFlipMirror={setFlipMirror}
                  />
                </div>
              </div>

              {/* 1€ Signal Tuning Sliders */}
              <SensitivitySliders
                minCutoff={minCutoff}
                setMinCutoff={setMinCutoff}
                beta={beta}
                setBeta={setBeta}
                margin={margin}
                setMargin={setMargin}
                pinchThresh={pinchThresh}
                setPinchThresh={setPinchThresh}
                onResetDefaults={handleResetDefaults}
              />

              {/* Hotkey Remapper */}
              <HotkeyRemapper />
            </div>
          )}

          {currentTab === 'camera' && (
            <div className="space-y-6">
              <WebcamCanvas 
                isStreaming={isStreaming} 
                onToggleStream={() => setIsStreaming(!isStreaming)} 
              />
              <DeviceSelector
                selectedCamera={selectedCamera}
                setSelectedCamera={setSelectedCamera}
                flipMirror={flipMirror}
                setFlipMirror={setFlipMirror}
              />
            </div>
          )}

          {currentTab === 'sensitivity' && (
            <SensitivitySliders
              minCutoff={minCutoff}
              setMinCutoff={setMinCutoff}
              beta={beta}
              setBeta={setBeta}
              margin={margin}
              setMargin={setMargin}
              pinchThresh={pinchThresh}
              setPinchThresh={setPinchThresh}
              onResetDefaults={handleResetDefaults}
            />
          )}

          {currentTab === 'gestures' && (
            <HotkeyRemapper />
          )}

          {currentTab === 'logs' && (
            <div className="p-5 rounded-xl bg-[#111115] border border-white/5 space-y-3 font-mono text-xs">
              <div className="flex items-center gap-2 text-zinc-300 pb-2 border-b border-white/5">
                <Terminal className="w-4 h-4 text-cyan-400" />
                <span>REAL-TIME KERNEL DISPATCH LOGS</span>
              </div>
              <div className="space-y-1.5 text-zinc-400">
                <p className="text-zinc-500">[00:00:01] Direct Win32 ctypes bridge loaded (user32.dll &amp; shcore.dll)</p>
                <p className="text-emerald-400">[00:00:01] Hardware Display verified: 1920x1080 Native Resolution</p>
                <p className="text-zinc-400">[00:00:02] OneEuroFilter initial frequency modulated: fc_min=0.80Hz, beta=0.015</p>
                <p className="text-cyan-400">[00:00:03] MediaPipe Tasks 3D HandLandmarker model online</p>
                <p className="text-zinc-400">[00:00:04] Left hand entered frame: FIST detected &rarr; HandMode.WINDOW_SNAP</p>
                <p className="text-emerald-400">[00:00:05] Right hand pinch detected: synthesized Win+Left shortcut [1.2ms]</p>
                <p className="text-zinc-400">[00:00:06] Non-blocking hysteresis release: 120ms debounce nominal</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
