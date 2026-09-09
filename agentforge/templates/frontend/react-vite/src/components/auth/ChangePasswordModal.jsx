import React, { useState } from 'react';
import { Lock, KeyRound, AlertCircle, CheckCircle2, X } from 'lucide-react';
import { apiRequest } from '../../api/client';

export function ChangePasswordModal({ isOpen, isMandatory = false, onClose, onSuccess }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  if (!isOpen) return null;

  // Validation rules
  const hasMinLength = newPassword.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(newPassword);
  const hasDigit = /[0-9]/.test(newPassword);
  const hasSpecial = /[~!@#$%^&*()-_=+[{\]}\\|;:'",<.>/?`]/.test(newPassword);
  const isDifferent = currentPassword ? newPassword !== currentPassword : true;
  const isMatching = newPassword && confirmPassword ? newPassword === confirmPassword : false;

  const isFormValid =
    hasMinLength &&
    hasLetter &&
    hasDigit &&
    hasSpecial &&
    isDifferent &&
    isMatching &&
    currentPassword.length > 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isFormValid || loading) return;

    setLoading(true);
    setErrorMessage('');

    try {
      const res = await apiRequest('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (onSuccess) {
        onSuccess(res);
      }
      if (onClose) {
        onClose();
      }
    } catch (err) {
      setErrorMessage(err.message || '비밀번호 변경 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-skred/10 text-skred">
              <KeyRound className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">
                {isMandatory ? '비밀번호 필수 변경' : '비밀번호 변경'}
              </h3>
              <p className="text-xs text-gray-500">
                {isMandatory
                  ? '임시 비밀번호 상태입니다. 새 비밀번호를 설정해주세요.'
                  : '주기적인 비밀번호 변경으로 계정을 안전하게 보호하세요.'}
              </p>
            </div>
          </div>
          {!isMandatory && onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {isMandatory && (
          <div className="mb-4 flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-800 border border-amber-200">
            <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
            <span>
              보안 규정에 따라 <strong>최초 발급된 임시 비밀번호</strong>를 변경해야 AI 어시스턴트 채팅 및 서비스를 이용하실 수 있습니다.
            </span>
          </div>
        )}

        {errorMessage && (
          <div className="mb-4 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-xs text-skred border border-red-200">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              현재 비밀번호 (임시 비밀번호)
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="현재 비밀번호 입력"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm pl-9 focus:border-skred focus:outline-none focus:ring-1 focus:ring-skred"
              />
              <Lock className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              새 비밀번호
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="8자 이상 영문/숫자/특수문자"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm pl-9 focus:border-skred focus:outline-none focus:ring-1 focus:ring-skred"
              />
              <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              새 비밀번호 확인
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="새 비밀번호 재입력"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm pl-9 focus:border-skred focus:outline-none focus:ring-1 focus:ring-skred"
              />
              <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            </div>
          </div>

          {/* Validation Checklist */}
          <div className="rounded-xl bg-gray-50 p-3 text-xs space-y-1.5 border border-gray-200">
            <div className="font-semibold text-gray-600 mb-1">비밀번호 설정 기준:</div>
            <div className={`flex items-center gap-1.5 ${hasMinLength ? 'text-emerald-600 font-medium' : 'text-gray-400'}`}>
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>최소 8자 이상</span>
            </div>
            <div className={`flex items-center gap-1.5 ${hasLetter && hasDigit && hasSpecial ? 'text-emerald-600 font-medium' : 'text-gray-400'}`}>
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>영문, 숫자, 특수문자 조합 포함</span>
            </div>
            <div className={`flex items-center gap-1.5 ${newPassword && isDifferent ? 'text-emerald-600 font-medium' : 'text-gray-400'}`}>
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>현재(임시) 비밀번호와 다름</span>
            </div>
            <div className={`flex items-center gap-1.5 ${confirmPassword && isMatching ? 'text-emerald-600 font-medium' : 'text-gray-400'}`}>
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>새 비밀번호 확인 일치</span>
            </div>
          </div>

          <div className="mt-5 flex justify-end gap-2">
            {!isMandatory && onClose && (
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                className="rounded-lg border border-gray-300 px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 transition"
              >
                취소
              </button>
            )}
            <button
              type="submit"
              disabled={!isFormValid || loading}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-skred to-skorange px-4 py-2 text-xs font-semibold text-white shadow transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? '변경 중...' : '비밀번호 변경 및 완료'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
