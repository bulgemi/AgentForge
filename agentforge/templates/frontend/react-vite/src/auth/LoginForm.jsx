import React, { useState } from 'react';
import { useAuth } from './AuthProvider';
import { Shield, Key, Users, ArrowRight } from 'lucide-react';

export function LoginForm({ onLoginSuccess }) {
  const { login } = useAuth();
  const [tab, setTab] = useState('id_pw'); // 'id_pw' | 'ldap'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password, tab);
      if (onLoginSuccess) onLoginSuccess();
    } catch (err) {
      setError(err.message || '로그인에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSamlLogin = () => {
    window.location.href = '/api/v1/sso/login';
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center">
            <img src="/agentforge_icon.png" alt="Logo" className="h-14 w-14 object-contain drop-shadow-sm" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">{{ project_name }}</h1>
          <p className="mt-1 text-sm text-gray-500">Enterprise AI Agent Platform</p>
        </div>

        {/* Auth Mode Tabs */}
        <div className="mb-6 grid grid-cols-2 gap-2 rounded-xl bg-gray-100 p-1">
          <button
            type="button"
            onClick={() => setTab('id_pw')}
            className={`flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition ${
              tab === 'id_pw' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Key className="h-4 w-4" />
            ID / Password
          </button>
          <button
            type="button"
            onClick={() => setTab('ldap')}
            className={`flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition ${
              tab === 'ldap' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Users className="h-4 w-4" />
            사내 LDAP
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm font-medium text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700">
              {tab === 'ldap' ? '사번 / LDAP 아이디' : '아이디'}
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-skred focus:outline-none focus:ring-1 focus:ring-skred"
              placeholder={tab === 'ldap' ? '사번 입력' : '아이디 입력'}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700">
              비밀번호
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-skred focus:outline-none focus:ring-1 focus:ring-skred"
              placeholder="비밀번호 입력"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-skred to-skorange py-2.5 text-sm font-semibold text-white shadow transition hover:opacity-95 disabled:opacity-50"
          >
            {loading ? '인증 중...' : '로그인'}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        {/* SSO Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-2 text-gray-400">또는 SSO 로그인</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleSamlLogin}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white py-2.5 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50"
        >
          <Shield className="h-4 w-4 text-skred" />
          SAML 2.0 Single Sign-On
        </button>
      </div>
    </div>
  );
}
