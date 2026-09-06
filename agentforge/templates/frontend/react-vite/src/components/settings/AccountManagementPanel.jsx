import React, { useState, useEffect } from 'react';
import { Users, UserPlus, KeyRound, Unlock, Search, Shield, RefreshCw } from 'lucide-react';
import { apiRequest } from '../../api/client';

export function AccountManagementPanel() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [tempPasswordResult, setTempPasswordResult] = useState(null);

  // Form State
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('user');

  const fetchUsers = async () => {
    setLoading(true);
    try {
      let query = `?page=1&size=50`;
      if (search) query += `&search=${encodeURIComponent(search)}`;
      if (roleFilter) query += `&role=${encodeURIComponent(roleFilter)}`;
      const data = await apiRequest(`/admin/users${query}`);
      setUsers(data.items || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [roleFilter]);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      const res = await apiRequest('/admin/users', {
        method: 'POST',
        body: JSON.stringify({
          username: newUsername,
          email: newEmail || null,
          role: newRole,
        }),
      });
      setShowCreateModal(false);
      setTempPasswordResult({ username: newUsername, password: res.initial_password });
      setNewUsername('');
      setNewEmail('');
      fetchUsers();
    } catch (err) {
      alert(`계정 생성 실패: ${err.message}`);
    }
  };

  const handleUnlock = async (userId) => {
    if (!confirm('이 계정의 잠금을 해제하시겠습니까?')) return;
    try {
      await apiRequest(`/admin/users/${userId}/unlock`, { method: 'POST' });
      fetchUsers();
    } catch (err) {
      alert(`잠금 해제 실패: ${err.message}`);
    }
  };

  const handleResetPassword = async (userId, username) => {
    if (!confirm(`'${username}' 계정의 비밀번호를 임시 비밀번호로 초기화하시겠습니까?`)) return;
    try {
      const res = await apiRequest(`/admin/users/${userId}/reset-password`, { method: 'POST' });
      setTempPasswordResult({ username, password: res.temporary_password });
    } catch (err) {
      alert(`비밀번호 리셋 실패: ${err.message}`);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="h-6 w-6 text-skred" />
            사용자 및 계정 권한 관리
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            엔터프라이즈 계정 생성, 역할(Role) 배정, 잠금 해제 및 비밀번호 초기화
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-skred to-skorange px-4 py-2.5 text-sm font-semibold text-white shadow transition hover:opacity-95"
        >
          <UserPlus className="h-4 w-4" />
          신규 사용자 등록
        </button>
      </div>

      {/* Filter Bar */}
      <div className="mb-6 flex gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="아이디 또는 이메일 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchUsers()}
            className="w-full rounded-lg border border-gray-300 pl-9 pr-4 py-2 text-sm focus:border-skred focus:outline-none"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-skred focus:outline-none"
        >
          <option value="">전체 권한</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
          <option value="auditor">Auditor</option>
        </select>
        <button
          type="button"
          onClick={fetchUsers}
          className="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-gray-50 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
        >
          <RefreshCw className="h-4 w-4" />
          조회
        </button>
      </div>

      {/* Users Table */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-xs font-semibold uppercase tracking-wider text-gray-500">
            <tr>
              <th className="px-6 py-3 text-left">사용자</th>
              <th className="px-6 py-3 text-left">이메일</th>
              <th className="px-6 py-3 text-left">권한 (Role)</th>
              <th className="px-6 py-3 text-left">계정 상태</th>
              <th className="px-6 py-3 text-right">작업</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {users.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-gray-500">
                  {loading ? '불러오는 중...' : '등록된 사용자가 없습니다.'}
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50/50">
                  <td className="px-6 py-4 font-medium text-gray-900">{u.username}</td>
                  <td className="px-6 py-4 text-gray-500">{u.email || '-'}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${
                        u.role === 'admin'
                          ? 'bg-red-50 text-skred'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {u.role.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${
                        u.status === 'active'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-amber-50 text-amber-700'
                      }`}
                    >
                      {u.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    {u.status === 'locked' && (
                      <button
                        type="button"
                        onClick={() => handleUnlock(u.id)}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 hover:text-emerald-700"
                      >
                        <Unlock className="h-3.5 w-3.5" />
                        잠금해제
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleResetPassword(u.id, u.username)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-gray-600 hover:text-gray-900"
                    >
                      <KeyRound className="h-3.5 w-3.5" />
                      비밀번호 초기화
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-4">신규 사용자 등록</h3>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase">아이디</label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-skred focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase">이메일</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-skred focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase">권한 (Role)</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-skred focus:outline-none"
                >
                  <option value="user">User (일반 에이전트 사용자)</option>
                  <option value="admin">Admin (시스템 관리자)</option>
                  <option value="auditor">Auditor (감사자)</option>
                </select>
              </div>
              <div className="mt-6 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                >
                  취소
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-gradient-to-r from-skred to-skorange px-4 py-2 text-sm font-semibold text-white shadow"
                >
                  생성
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Password Result Modal */}
      {tempPasswordResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-2">임시 비밀번호 안내</h3>
            <p className="text-sm text-gray-600 mb-4">
              <strong>{tempPasswordResult.username}</strong> 계정의 임시 비밀번호가 발급되었습니다.
            </p>
            <div className="rounded-lg bg-gray-100 p-3 font-mono text-center text-base font-bold text-skred select-all">
              {tempPasswordResult.password}
            </div>
            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setTempPasswordResult(null)}
                className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white shadow"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
