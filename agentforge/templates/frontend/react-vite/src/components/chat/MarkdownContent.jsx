import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';

const LANGUAGE_MAP = {
  'c++': 'cpp',
  'c#': 'csharp',
  'cs': 'csharp',
  'py': 'python',
  'js': 'javascript',
  'ts': 'typescript',
  'sh': 'bash',
  'shell': 'bash',
  'zsh': 'bash',
  'yml': 'yaml',
  'golang': 'go',
  'dockerfile': 'docker',
};

function normalizeLanguage(lang) {
  if (!lang) return 'text';
  const base = lang.split(/[:{]/)[0].trim().toLowerCase();
  return LANGUAGE_MAP[base] || base || 'text';
}

function CodeBlock({ language, value = '' }) {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleCopy = async () => {
    try {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      const safeValue = value ?? '';

      if (navigator?.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(safeValue);
          setCopied(true);
          timeoutRef.current = setTimeout(() => setCopied(false), 2000);
          return;
        } catch {
          // Fall through to execCommand if clipboard API permission is denied
        }
      }

      // Fallback for non-secure contexts (e.g. plain HTTP on IP address) or older browsers
      const textArea = document.createElement('textarea');
      textArea.value = safeValue;
      textArea.setAttribute('readonly', '');
      textArea.style.position = 'fixed';
      textArea.style.top = '0';
      textArea.style.left = '-9999px';
      textArea.style.opacity = '0';
      textArea.style.fontSize = '16px'; // Prevent iOS viewport auto-zoom
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      if (textArea.setSelectionRange) {
        textArea.setSelectionRange(0, safeValue.length);
      }
      const success = document.execCommand('copy');
      document.body.removeChild(textArea);
      if (success) {
        setCopied(true);
        timeoutRef.current = setTimeout(() => setCopied(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const displayLang = language || 'code';
  const highlightLang = normalizeLanguage(language);

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-gray-800 bg-gray-950 shadow-md">
      <div className="flex items-center justify-between border-b border-gray-800 bg-gray-900 px-4 py-1.5 text-xs text-gray-400">
        <span className="font-mono text-[11px] uppercase tracking-wider text-gray-300">
          {displayLang}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded px-2 py-0.5 text-xs text-gray-400 transition hover:bg-gray-800 hover:text-gray-200"
          title="코드 복사"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400">복사됨</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>복사</span>
            </>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        language={highlightLang}
        style={vscDarkPlus}
        PreTag="div"
        customStyle={{
          margin: 0,
          padding: '0.875rem 1rem',
          fontSize: '0.8125rem',
          lineHeight: '1.5',
          backgroundColor: '#030712',
        }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
}

export function MarkdownContent({ content }) {
  const textContent = content == null ? '' : String(content);

  return (
    <div className="markdown-content text-sm leading-relaxed text-gray-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }) {
            return <>{children}</>;
          },
          code({ node, className, children, ...props }) {
            const match = /language-([^\s]+)/.exec(className || '');
            const codeText = Array.isArray(children) ? children.join('') : String(children ?? '');
            const isMultiLine = codeText.includes('\n') || Boolean(match);
            if (!isMultiLine) {
              return (
                <code
                  className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs font-semibold text-pink-600"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <CodeBlock
                language={match ? match[1] : ''}
                value={codeText.replace(/\n$/, '')}
              />
            );
          },
          h1({ children }) {
            return <h1 className="mb-2 mt-4 text-lg font-bold text-gray-900 first:mt-0">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="mb-2 mt-3 text-base font-bold text-gray-900 first:mt-0">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="mb-1.5 mt-2.5 text-sm font-bold text-gray-900 first:mt-0">{children}</h3>;
          },
          h4({ children }) {
            return <h4 className="mb-1 mt-2 text-sm font-semibold text-gray-900 first:mt-0">{children}</h4>;
          },
          h5({ children }) {
            return <h5 className="mb-1 mt-1.5 text-xs font-semibold uppercase tracking-wider text-gray-700 first:mt-0">{children}</h5>;
          },
          h6({ children }) {
            return <h6 className="mb-1 mt-1.5 text-xs font-medium text-gray-500 first:mt-0">{children}</h6>;
          },
          p({ children }) {
            return <p className="mb-2.5 last:mb-0 leading-relaxed">{children}</p>;
          },
          ul({ className, children }) {
            const isTaskList = className?.includes('contains-task-list');
            return (
              <ul className={isTaskList ? 'mb-2.5 list-none space-y-1 pl-1 last:mb-0' : 'mb-2.5 list-disc space-y-1 pl-5 last:mb-0'}>
                {children}
              </ul>
            );
          },
          ol({ children }) {
            return <ol className="mb-2.5 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>;
          },
          li({ className, children }) {
            const isTaskItem = className?.includes('task-list-item');
            return (
              <li className={isTaskItem ? 'flex items-start gap-2 leading-relaxed' : 'leading-relaxed'}>
                {children}
              </li>
            );
          },
          input({ node, ...props }) {
            return <input className="mt-0.5 h-4 w-4 rounded border-gray-300 accent-skred text-skred focus:ring-0" readOnly disabled {...props} />;
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-2 border-l-4 border-gray-300 pl-3 italic text-gray-600">
                {children}
              </blockquote>
            );
          },
          a({ href, children }) {
            const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
            return (
              <a
                href={href}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
                className="font-medium text-skred hover:underline"
              >
                {children}
              </a>
            );
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto rounded-lg border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200 text-xs">
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-gray-50">{children}</thead>;
          },
          th({ node, style, children, ...props }) {
            return (
              <th
                style={style}
                className="px-3 py-2 text-left font-semibold text-gray-700"
                {...props}
              >
                {children}
              </th>
            );
          },
          td({ node, style, children, ...props }) {
            return (
              <td
                style={style}
                className="border-t border-gray-100 px-3 py-2 text-gray-700"
                {...props}
              >
                {children}
              </td>
            );
          },
          hr() {
            return <hr className="my-3 border-gray-200" />;
          },
          strong({ children }) {
            return <strong className="font-semibold text-gray-900">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic">{children}</em>;
          },
          del({ children }) {
            return <del className="line-through text-gray-500">{children}</del>;
          },
        }}
      >
        {textContent}
      </ReactMarkdown>
    </div>
  );
}
