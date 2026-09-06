import React, { useState } from 'react';
import { AlertCircle, Check, X } from 'lucide-react';

export function InterruptApprovalCard({ interrupt, onResolve }) {
  const [loading, setLoading] = useState(false);

  const handleAction = async (decision) => {
    setLoading(true);
    try {
      await onResolve(interrupt.interrupt_id, decision);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="my-4 rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-amber-100 p-2 text-amber-600">
          <AlertCircle className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-bold text-amber-900">사용자 확인 필요 (Human-in-the-Loop)</h4>
          <p className="mt-1 text-sm text-amber-800">{interrupt.prompt}</p>
          {interrupt.action_name && (
            <div className="mt-2 rounded bg-white/60 p-2 font-mono text-xs text-amber-950">
              실행 예정 액션: <span className="font-semibold">{interrupt.action_name}</span>
            </div>
          )}
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={loading}
              onClick={() => handleAction('approve')}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow transition hover:bg-emerald-700 disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" />
              승인 (진행)
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => handleAction('reject')}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:opacity-50"
            >
              <X className="h-3.5 w-3.5" />
              반려 (중단)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
