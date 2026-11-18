import { Fragment } from 'react';

export const HotkeyRemapper: React.FC = () => {
  const bindings = [
    {
      gesture: 'Right Index + Thumb Pinch',
      leftModifier: 'None (Resting)',
      action: 'Primary Left Click',
      hotkey: ['LClick'],
      tag: 'Core Navigation',
    },
    {
      gesture: 'Right Middle + Thumb Pinch',
      leftModifier: 'None (Resting)',
      action: 'Context Menu',
      hotkey: ['RClick'],
      tag: 'Core Navigation',
    },
    {
      gesture: 'Right Index Pinch',
      leftModifier: 'Left Hand Fist (Closed)',
      action: 'Snap Active Window Left',
      hotkey: ['Win', '←'],
      tag: 'Window Snap Layout',
    },
    {
      gesture: 'Right Index Pinch',
      leftModifier: 'Left Hand 3-Fingers',
      action: 'Switch Virtual Desktop',
      hotkey: ['Win', 'Ctrl', '→'],
      tag: 'Workspace Navigation',
    },
    {
      gesture: 'Crossed Wrists / Fist Bump',
      leftModifier: 'Open Palm Facing Camera',
      action: 'Instant Minimize All Windows',
      hotkey: ['Win', 'D'],
      tag: 'Emergency Killswitch',
    },
  ];

  return (
    <div className="p-5 rounded-xl bg-[#111115] border border-white/5 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div>
          <h3 className="text-sm font-semibold text-white">Bimanual Chord Mappings</h3>
          <p className="text-xs text-zinc-400">
            Combine Left Hand posture modes with Right Hand spatial triggers to execute native Windows shortcuts.
          </p>
        </div>
        <span className="text-[11px] font-mono text-zinc-400 bg-white/5 px-2.5 py-1 rounded border border-white/5">
          5 Chords Configured
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-white/5 text-[10px] font-mono uppercase text-zinc-400">
              <th className="pb-2.5 font-medium">Physical Gesture Trigger</th>
              <th className="pb-2.5 font-medium">Left Hand Modifier</th>
              <th className="pb-2.5 font-medium">Native OS Action</th>
              <th className="pb-2.5 font-medium text-right">Synthesized Keycaps</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {bindings.map((b, i) => (
              <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                <td className="py-3 font-medium text-white flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  {b.gesture}
                </td>
                <td className="py-3 text-zinc-400 font-mono text-[11px]">{b.leftModifier}</td>
                <td className="py-3 text-zinc-300">
                  <span className="font-medium text-white">{b.action}</span>
                  <span className="block text-[10px] font-mono text-zinc-400 mt-0.5">{b.tag}</span>
                </td>
                <td className="py-3 text-right">
                  <div className="flex items-center justify-end gap-1 font-mono">
                    {b.hotkey.map((key, kIdx) => (
                      <Fragment key={kIdx}>
                        <kbd className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700/80 text-zinc-200 text-[11px] font-semibold shadow-xs shadow-black/80">
                          {key}
                        </kbd>
                        {kIdx < b.hotkey.length - 1 && <span className="text-zinc-400 text-xs">+</span>}
                      </Fragment>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
