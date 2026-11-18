import { useEffect, useRef } from 'react';
import { Crosshair, Video } from 'lucide-react';

interface WebcamCanvasProps {
  isStreaming: boolean;
  onToggleStream: () => void;
}

export const WebcamCanvas: React.FC<WebcamCanvasProps> = ({ isStreaming, onToggleStream }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Animated futuristic skeletal visualizer simulation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let t = 0;

    const render = () => {
      t += 0.03;
      ctx.fillStyle = '#0a0a0e';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Subtle tech background grid
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
      ctx.lineWidth = 1;
      const step = 40;
      for (let x = 0; x < canvas.width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      if (isStreaming) {
        // Floating hand skeleton simulation
        const cx = canvas.width * 0.5 + Math.sin(t * 0.8) * 80;
        const cy = canvas.height * 0.5 + Math.cos(t * 1.2) * 50;

        const wrist = { x: cx, y: cy + 120 };
        const thumbTip = { x: cx - 60 + Math.sin(t) * 10, y: cy - 20 + Math.cos(t) * 10 };
        const indexTip = { x: cx - 15, y: cy - 90 + Math.sin(t * 2) * 8 };
        const midTip = { x: cx + 25, y: cy - 95 };
        const ringTip = { x: cx + 60, y: cy - 70 };
        const pinkyTip = { x: cx + 90, y: cy - 30 };
        const mcp = { x: cx + 10, y: cy + 10 };

        // Draw connections
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.4)';
        ctx.lineWidth = 2;
        const tips = [thumbTip, indexTip, midTip, ringTip, pinkyTip];
        tips.forEach(pt => {
          ctx.beginPath();
          ctx.moveTo(wrist.x, wrist.y);
          ctx.lineTo(mcp.x, mcp.y);
          ctx.lineTo(pt.x, pt.y);
          ctx.stroke();
        });

        // Draw joints
        [wrist, mcp, ...tips].forEach((pt, idx) => {
          ctx.fillStyle = idx === 2 ? '#ff00ff' : '#00f0ff';
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, idx === 2 ? 6 : 4, 0, Math.PI * 2);
          ctx.fill();

          ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, idx === 2 ? 10 : 7, 0, Math.PI * 2);
          ctx.stroke();
        });

        // Target reticle at index tip
        ctx.strokeStyle = '#00f0ff';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(indexTip.x, indexTip.y, 20 + Math.sin(t * 4) * 3, 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = '#00f0ff';
        ctx.font = '10px monospace';
        ctx.fillText(`POINTER LOCK [${Math.round(indexTip.x * 2)}, ${Math.round(indexTip.y * 2)}]`, indexTip.x + 28, indexTip.y);
      } else {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.font = '12px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('CAMERA STANDBY — CLICK "INITIALIZE VISION" TO START FEED', canvas.width / 2, canvas.height / 2);
      }

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [isStreaming]);

  return (
    <div className="rounded-xl bg-[#111115] border border-white/5 overflow-hidden flex flex-col">
      <div className="h-11 px-4 border-b border-white/5 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2 text-zinc-300">
          <Crosshair className="w-4 h-4 text-cyan-400" />
          <span>OPTICAL SENSING MIRROR</span>
          <span className="text-[10px] text-zinc-400">• 1280x720 60FPS</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onToggleStream}
            className={`px-3 py-1 rounded text-[11px] font-mono transition-colors flex items-center gap-1.5 ${
              isStreaming
                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20'
                : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20'
            }`}
          >
            <Video className="w-3.5 h-3.5" />
            <span>{isStreaming ? 'Stop Vision' : 'Initialize Vision'}</span>
          </button>
        </div>
      </div>
      <div className="relative aspect-video w-full bg-black">
        <canvas
          ref={canvasRef}
          width={800}
          height={450}
          className="w-full h-full object-cover"
        />
        <div className="absolute bottom-3 left-4 text-[10px] font-mono text-zinc-400 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded border border-white/10">
          Model: MediaPipe Tasks 3D HandLandmarker • 42 Points Total
        </div>
      </div>
    </div>
  );
};
