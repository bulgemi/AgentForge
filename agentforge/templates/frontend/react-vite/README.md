# {{ project_name }} - Frontend ⚡

Modern, AI-first web interface built with **React 18**, **Vite**, and **Tailwind CSS**.

---

## 🎨 UI/UX Design System & AI Coding Guidelines

> **IMPORTANT**: When designing new UI components or collaborating with **AI Coding Agents** (Cursor, Claude Code, GitHub Copilot, Windsurf, Antigravity, etc.), you **MUST** follow the design system and constraints specified in [`DESIGN.md`](./DESIGN.md).

- **Brand Tokens**: SK Red (`#E1002A`), SK Orange (`#F58220`), Gradient CTAs
- **Icons**: Exclusively [`lucide-react`](https://lucide.dev/)
- **AI Patterns**: SSE token streaming, Human-in-the-Loop approval cards, dark terminal console
- **Strict Rules**: No arbitrary hex values (`bg-[#...]`), no inline styles, accessible semantics

See [**`DESIGN.md`**](./DESIGN.md) for comprehensive component guidelines, color palettes, and copy-paste prompt templates for AI agents.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Local Development Server
```bash
npm run dev
```
- **User Chat Portal**: [http://localhost:5173](http://localhost:5173)
- **Admin Governance Console**: [http://localhost:5173/admin.html](http://localhost:5173/admin.html)

### 3. Build for Production
```bash
npm run build
```

---

## 📂 Project Structure

```text
frontend/
├── DESIGN.md                 # Official UI/UX Design System & AI Coding Agent Rules
├── README.md                 # Frontend documentation
├── index.html                # Entrypoint: User Chat Portal
├── admin.html                # Entrypoint: Admin Console
├── package.json              # Dependencies (React, Lucide, Tailwind, Markdown)
├── tailwind.config.js        # SK brand color extensions (skred, skorange)
├── vite.config.js            # Vite multi-page configuration (chat & admin)
└── src/
    ├── App.jsx               # Root portal container & auth protection
    ├── main.jsx              # Main chat application mounter
    ├── admin/                # Admin Console application
    │   ├── AdminApp.jsx      # Admin UI container & RBAC enforcement
    │   └── main.jsx          # Admin application mounter
    ├── auth/                 # Authentication state & login flows
    │   ├── AuthProvider.jsx  # JWT token management & session context
    │   └── LoginForm.jsx     # Login form with ID/PW and LDAP/SAML hooks
    ├── api/                  # Backend API clients
    │   └── client.js         # Base fetcher & SSE stream endpoints
    └── components/           # Modular UI component system
        ├── auth/             # Password reset & security modals
        ├── chat/             # AI Chat, Streaming, Interrupt cards & Console
        └── settings/         # User & Account governance management tables
```
