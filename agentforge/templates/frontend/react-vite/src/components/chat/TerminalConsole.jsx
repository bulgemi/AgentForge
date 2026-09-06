import React from 'react';
import { Terminal, Activity, CheckCircle2 } from 'lucide-react';

export function TerminalConsole({ logs = [], isStreaming = false }) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-gray-800 bg-gray-950 text-gray-200 shadow-2xl">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-emerald-400" />
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-gray-300">
            Agent Execution Console
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {isStreaming ? (
            <span className="flex items-center gap-1.5 text-amber-400">
              <Activity className="h-3 w-3 animate-pulse" />
              Thinking...
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-gray-500">
              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
              Idle
            </span>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs leading-relaxed">
        {logs.length === 0 ? (
          <p className="text-gray-600">No agent actions recorded yet.</p>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="flex gap-2 py-0.5">
              <span className="text-gray-500">[{log.time}]</span>
              <span className={log.type === 'meta' ? 'text-amber-400' : 'text-emerald-300'}>
                {log.text}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
