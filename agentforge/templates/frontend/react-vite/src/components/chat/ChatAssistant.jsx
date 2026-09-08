import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Terminal as TerminalIcon } from 'lucide-react';
import { InterruptApprovalCard } from './InterruptApprovalCard';
import { TerminalConsole } from './TerminalConsole';
import { API_BASE } from '../../api/client';
import { useAuth } from '../../auth/AuthProvider';

export function ChatAssistant({ chatId = 'default-chat', headerActions = null }) {
  const { logout } = useAuth() || {};
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [logs, setLogs] = useState([]);
  const [showTerminal, setShowTerminal] = useState(false);
  const [pendingInterrupt, setPendingInterrupt] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streaming]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || streaming) return;

    const userMessage = { id: Date.now().toString(), role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setStreaming(true);

    const timeStr = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { time: timeStr, text: `Prompt sent: "${userMessage.content}"`, type: 'meta' }]);

    const token = localStorage.getItem('access_token');
    try {
      const response = await fetch(`${API_BASE}/chats/${chatId}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: userMessage.content }),
      });

      if (response.status === 401) {
        if (logout) {
          logout();
        } else {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.reload();
        }
        return;
      }

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMsg = { id: (Date.now() + 1).toString(), role: 'assistant', content: '' };
      setMessages((prev) => [...prev, assistantMsg]);

      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          if (!block.trim()) continue;
          const blockLines = block.split('\n');
          let eventType = 'token';
          const dataLines = [];

          for (const line of blockLines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              dataLines.push(line.slice(6));
            }
          }

          const rawData = dataLines.join('\n').trim();
          if (!rawData && eventType !== 'done') continue;

          let parsedPayload = null;
          try {
            parsedPayload = JSON.parse(rawData);
          } catch {
            // rawData is plain text
          }

          if (eventType === 'token') {
            const tokenText = parsedPayload && typeof parsedPayload === 'object'
              ? (parsedPayload.content ?? parsedPayload.data ?? '')
              : rawData;

            if (tokenText) {
              assistantMsg.content += tokenText;
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantMsg.id ? { ...m, content: assistantMsg.content } : m))
              );
            }
          } else if (eventType === 'meta') {
            const metaText = parsedPayload && typeof parsedPayload === 'object'
              ? (parsedPayload.data ? JSON.stringify(parsedPayload.data) : JSON.stringify(parsedPayload))
              : rawData;
            setLogs((prev) => [
              ...prev,
              { time: new Date().toLocaleTimeString(), text: `Meta: ${metaText}`, type: 'meta' },
            ]);
          } else if (eventType === 'interrupt') {
            const interruptObj = (parsedPayload && typeof parsedPayload === 'object') ? parsedPayload : rawData;
            setPendingInterrupt(interruptObj);
          } else if (eventType === 'done') {
            // Stream completed
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), role: 'assistant', content: `⚠️ 오류: ${err.message}` },
      ]);
    } finally {
      setStreaming(false);
    }
  };

  const handleResolveInterrupt = async (interruptId, decision) => {
    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_BASE}/chats/${chatId}/interrupts/${interruptId}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ decision }),
      });
      if (res.status === 401) {
        if (logout) {
          logout();
        } else {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.reload();
        }
        return;
      }
    } catch (err) {
      console.error('Failed to resolve interrupt:', err);
    }
    setPendingInterrupt(null);
  };

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
        <div className="flex items-center gap-3">
          <img src="/agentforge_icon.png" alt="Logo" className="h-8 w-8 object-contain" />
          <div>
            <h2 className="text-sm font-bold text-gray-900">{{ project_name }}</h2>
            <p className="text-xs text-emerald-600 font-medium">● Connected (SSE Stream)</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowTerminal(!showTerminal)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold shadow-sm transition ${
              showTerminal ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            <TerminalIcon className="h-3.5 w-3.5" />
            Console
          </button>
          {headerActions}
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat Feed */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <div className="mb-3 rounded-2xl bg-orange-50 p-4 text-skorange">
                  <Sparkles className="h-8 w-8" />
                </div>
                <h3 className="text-lg font-bold text-gray-900">어떤 작업을 도와드릴까요?</h3>
                <p className="mt-1 max-w-sm text-sm text-gray-500">
                  AgentForge Clean Architecture 런타임과 연결되어 실시간 스트리밍으로 답변합니다.
                </p>
              </div>
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {m.role !== 'user' && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gray-900 text-white text-xs font-bold">
                      AI
                    </div>
                  )}
                  <div
                    className={`max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                      m.role === 'user'
                        ? 'bg-gradient-to-r from-skred to-skorange text-white'
                        : 'border border-gray-200 bg-white text-gray-800'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  </div>
                  {m.role === 'user' && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gray-300 text-gray-700 text-xs font-bold">
                      Me
                    </div>
                  )}
                </div>
              ))
            )}

            {pendingInterrupt && (
              <InterruptApprovalCard
                interrupt={pendingInterrupt}
                onResolve={handleResolveInterrupt}
              />
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Footer */}
          <div className="border-t border-gray-200 bg-white p-4">
            <form onSubmit={handleSend} className="mx-auto flex max-w-4xl gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="에이전트에게 프롬프트를 입력하세요..."
                className="flex-1 rounded-xl border border-gray-300 px-4 py-3 text-sm shadow-sm focus:border-skred focus:outline-none focus:ring-1 focus:ring-skred"
              />
              <button
                type="submit"
                disabled={streaming || !input.trim()}
                className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-skred to-skorange px-5 py-3 text-sm font-semibold text-white shadow transition hover:opacity-95 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                전송
              </button>
            </form>
          </div>
        </div>

        {/* Side Console */}
        {showTerminal && (
          <div className="w-96 border-l border-gray-200 bg-gray-950 p-2">
            <TerminalConsole logs={logs} isStreaming={streaming} />
          </div>
        )}
      </div>
    </div>
  );
}
