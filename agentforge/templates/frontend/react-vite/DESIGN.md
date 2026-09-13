# {{ project_name }} Frontend Design System & AI Agent Guidelines

> 📘 **Project Design Specification (Single Source of Truth)**  
> 이 문서는 **{{ project_name }}** 프로젝트의 고유한 비즈니스/도메인 요구사항에 맞추어 UI/UX를 기획·정의하는 **표준 설계 명세서**입니다.  
> 
> - **프로젝트 맞춤 편집**: 프로젝트의 브랜드 색상, 타겟 사용자, 화면 레이아웃, 커스텀 컴포넌트 요건에 맞게 본 문서를 자유롭게 수정·확장하십시오.
> - **AI Coding Agent 협업**: Cursor, Windsurf, Claude Code, GitHub Copilot 등 AI 에이전트에게 프론트엔드 작업을 지시할 때 이 `DESIGN.md`를 필독하도록 설정하여, 임의의 스타일 파편화 없이 **프로젝트 요구사항에 정확히 부합하는 일관된 UI**를 자동 생성·유지할 수 있습니다.
> - **기본 제공 베이스라인**: 아래에 기술된 규칙(Tailwind 토큰, 8pt 그리드, Lucide 아이콘, 스트리밍 인터랙션 등)은 즉시 활용 가능한 프로덕션 검증 베이스라인 템플릿입니다.

This document defines the official design system, UI/UX conventions, component standards, and AI Coding Agent rules for **{{ project_name }}**.

All human engineers and **AI Coding Agents** (Cursor, Claude Code, GitHub Copilot, Windsurf, Antigravity, etc.) **MUST** read and adhere to the design rules defined here when creating, modifying, or refactoring frontend code.

---

## 1. Core Principles

1. **AI-First & Responsive Clarity**: Interface flows must clearly reflect AI state transitions (idle, streaming tokens, tool calling, awaiting human interrupt approval, error).
2. **Design Token Consistency**: Never use arbitrary one-off CSS classes, raw pixel values, or hardcoded hex colors (`#xxxxxx`). Always use the predefined Tailwind color palette and tokens.
3. **Single Icon Family**: Exclusively use [`lucide-react`](https://lucide.dev/). Do NOT install or introduce alternative icon libraries (FontAwesome, Heroicons, Material Icons, etc.) or raw inline SVGs.
4. **Accessible & Semantic HTML**: All interactive elements must use semantic elements (`<button type="button">`, `<nav>`, `<header>`, `<main>`, `<dialog>`/modal traps), have explicit accessible labels, and support keyboard navigation (`focus:ring-2`).
5. **Clean Utility Architecture**: Avoid raw CSS or inline `style={{ ... }}` objects. Use Tailwind utility classes composed cleanly with `clsx` and `tailwind-merge` where needed.

---

## 2. Color System & Design Tokens

The color system builds on the official **SK Brand Identity** paired with a sophisticated neutral slate/gray scale and crisp semantic alerts.

### 2.1 Brand Colors (`tailwind.config.js`)
| Token | Hex | Tailwind Utility Class | Usage |
| :--- | :--- | :--- | :--- |
| **SK Red** | `#E1002A` | `bg-skred`, `text-skred`, `border-skred` | Primary brand accent, error badges, active highlights, key brand logos |
| **SK Orange** | `#F58220` | `bg-skorange`, `text-skorange`, `border-skorange` | Secondary brand accent, sparkles, warning tones, warm gradient pairings |
| **Brand Gradient** | `linear-gradient` | `bg-gradient-to-r from-skred to-skorange text-white` | Primary call-to-action buttons, user chat bubbles, hero badges |

### 2.2 Neutral Palette (Tailwind Gray Scale)
- **Backgrounds**:
  - App background: `bg-gray-50`
  - Container / Card background: `bg-white`
  - Dark surfaces (Console/Terminal): `bg-gray-950` or `bg-gray-900`
  - Hover states: `hover:bg-gray-100`, `hover:bg-gray-50`
- **Borders & Dividers**:
  - Subtle borders: `border-gray-200`
  - Input field borders: `border-gray-300`, `focus:border-skred`
- **Typography Hierarchy**:
  - Headings & Primary labels: `text-gray-900 font-bold` or `font-semibold`
  - Body text: `text-gray-800` or `text-gray-700`
  - Secondary / Helper text: `text-gray-500 text-xs` or `text-sm`
  - Disabled / Placeholder: `text-gray-400`

### 2.3 Semantic Status Colors
| State | Text Class | Background / Badge Class | Border Class |
| :--- | :--- | :--- | :--- |
| **Success / Connected** | `text-emerald-600` | `bg-emerald-50` | `border-emerald-200` |
| **Warning / Attention** | `text-amber-600` | `bg-amber-50` | `border-amber-200` |
| **Destructive / Error** | `text-red-600` | `bg-red-50` | `border-red-200` |
| **Information / Active** | `text-blue-600` | `bg-blue-50` | `border-blue-200` |

---

## 3. Typography & Spacing (8pt Grid)

### 3.1 Font Stack
- Primary font: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
- Monospace font (Terminal, code snippets, tokens): `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace`

### 3.2 Spacing & Radii Scale
- **Spacing rhythm**: Multiples of 4px / 8px (`p-2` = 8px, `p-3` = 12px, `p-4` = 16px, `p-6` = 24px, `p-8` = 32px).
- **Border Radii**:
  - Buttons, Inputs, Badges: `rounded-xl` or `rounded-lg`
  - Cards, Containers, Message Bubbles: `rounded-2xl`
  - Avatars, Pills: `rounded-full`
- **Shadows**:
  - Default cards: `shadow-sm`
  - Modals, popovers, floating dialogs: `shadow-xl` or `shadow-2xl`

---

## 4. UI Component Guidelines

### 4.1 Buttons
- **Primary Action (Brand Gradient)**:
  ```jsx
  <button
    type="button"
    className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-skred to-skorange px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:opacity-95 disabled:opacity-50"
  >
    <Send className="h-4 w-4" />
    <span>전송</span>
  </button>
  ```
- **Secondary / Outlined Action**:
  ```jsx
  <button
    type="button"
    className="flex items-center gap-1.5 rounded-xl border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-200"
  >
    <KeyRound className="h-3.5 w-3.5 text-gray-500" />
    <span>비밀번호 변경</span>
  </button>
  ```
- **Destructive / Caution Action**:
  ```jsx
  <button
    type="button"
    className="flex items-center gap-1.5 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 shadow-sm transition hover:bg-red-100"
  >
    <Trash2 className="h-3.5 w-3.5 text-red-600" />
    <span>삭제</span>
  </button>
  ```

### 4.2 Form Inputs & Textareas
- Always pair with `<label className="block text-xs font-semibold text-gray-700 mb-1">`
- Inputs should default to:
  ```jsx
  <input
    type="text"
    className="w-full rounded-xl border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 shadow-sm transition focus:border-skred focus:outline-none focus:ring-1 focus:ring-skred"
  />
  ```

### 4.3 Cards & Data Tables
- Use `bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden` for card wraps.
- Tables should feature a subtle header (`bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wider`) and alternating hover rows (`hover:bg-gray-50/80 transition`).

---

## 5. AI Agent Interaction Patterns

### 5.1 Chat Message Bubbles
- **User Bubble (Right-aligned)**:
  - Container: `flex justify-end gap-3`
  - Bubble: `bg-gradient-to-r from-skred to-skorange text-white rounded-2xl px-4 py-3 text-sm shadow-sm leading-relaxed max-w-2xl`
  - User Avatar: `h-8 w-8 rounded-lg bg-gray-300 text-gray-700 text-xs font-bold`
- **Assistant Bubble (Left-aligned)**:
  - Container: `flex justify-start gap-3`
  - Bubble: `border border-gray-200 bg-white text-gray-800 rounded-2xl px-4 py-3 text-sm shadow-sm leading-relaxed max-w-2xl`
  - AI Avatar: `h-8 w-8 rounded-lg bg-gray-900 text-white text-xs font-bold`

### 5.2 Streaming & Thinking States
- While receiving SSE stream tokens (`streaming === true`):
  - Disable input submit button (`disabled:opacity-50 cursor-not-allowed`).
  - Render an animated pulsing indicator or streaming cursor `●` or blinking bar next to active assistant response.
  - Automatically smooth scroll to bottom via `messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })`.

### 5.3 Human-in-the-Loop (HITL) Interrupt Approval
When an AI agent requests confirmation for risky tools (e.g. database migration, payment, email dispatch), render `InterruptApprovalCard`:
- Border: `border-amber-300 bg-amber-50/70 rounded-2xl p-5 shadow-sm`
- Prominent warning icon (`AlertTriangle` from `lucide-react`)
- Two distinct choice buttons:
  - **Approve (승인)**: `bg-amber-600 hover:bg-amber-700 text-white`
  - **Reject (거부)**: `bg-white border border-gray-300 text-gray-700 hover:bg-gray-100`

### 5.4 Markdown & Code Presentation (`MarkdownContent.jsx`)
- Use `react-markdown` with `remark-gfm`.
- Fenced code blocks must feature syntax highlighting (`react-syntax-highlighter` or Prism) with a top header bar showing language tag and a "Copy Code" button.
- Tables inside assistant answers must render with cleanly styled borders and header padding.

### 5.5 Terminal & Execution Logs (`TerminalConsole.jsx`)
- Background: `bg-gray-950 text-gray-200`
- Monospace font (`font-mono text-xs`)
- Distinct log coloring:
  - Tool calls: `text-sky-400`
  - LLM Tokens: `text-gray-300`
  - System metadata: `text-amber-400`
  - Errors: `text-red-400`

---

## 6. Strict Rules & Constraints for AI Coding Agents

When prompt engineering or executing tasks through an AI Agent, enforce these rules:

| Category | Strict Rule (DO) | Strictly Prohibited (DON'T) |
| :--- | :--- | :--- |
| **Colors** | Use `skred`, `skorange`, or Tailwind default `gray-50~950`. | **NO** arbitrary hex styles (`bg-[#112233]`, `text-[#ff0000]`). |
| **Icons** | Import directly from `lucide-react` (e.g. `import { Bot, Send } from 'lucide-react'`). | **NO** FontAwesome, inline `<svg>`, or external icon packages. |
| **CSS Styling** | Use Tailwind classes exclusively. | **NO** custom `.css` files, CSS modules, or inline `style={{ ... }}`. |
| **Buttons** | Always specify `type="button"` or `type="submit"`. | **NO** `<button>` without an explicit `type` attribute. |
| **Responsive** | Mobile-first with `sm:`, `md:`, `lg:` breakpoints. | **NO** fixed pixel widths on parent layout containers. |
| **Navigation** | Cross-app links between Chat and Admin (`/admin.html` vs `/`). | **NO** hard-reloads unless clearing auth session tokens. |

---

## 7. AI Coding Agent Prompt Instructions

Developers can copy and paste this system instruction prompt directly into Cursor (`.cursorrules`), Windsurf, Claude Code, or Antigravity sessions:

```markdown
You are developing components for {{ project_name }}.
Follow the strict UI/UX design specifications in `frontend/DESIGN.md`:
1. Use Tailwind CSS with SK Brand tokens: `skred` (#E1002A) and `skorange` (#F58220).
2. Primary CTAs & user chat bubbles use `bg-gradient-to-r from-skred to-skorange text-white`.
3. Use ONLY icons from `lucide-react`. Do not introduce other icon packages or raw SVGs.
4. Cards must be `bg-white rounded-2xl border border-gray-200 shadow-sm`.
5. Maintain all AI interaction patterns (streaming states, HITL approval cards, markdown formatting).
6. Do NOT use inline styles (`style={{}}`) or arbitrary hex classes (`bg-[#...]`).
```
