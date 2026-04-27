Figma brief — SecureMLOPS (concise)

Goal
- Design a modern, accessible UI for SecureMLOPS (Login, Dashboard/Input + Pipeline, Settings). Keep server-rendered Flask flows working; preserve key IDs, form fields, and endpoints.

Quick context
- Flask + Jinja2 templates render `index.html` and `settings.html`. Key flows: sign-in, upload/select sample, run analysis, inspect 9-stage pipeline, view verdict and audit log.

Core color tokens (pick nearest match to attached image)
- --color-accent: #7CFF00
- --color-accent-600: #5EE600
- --color-bg: #0F1113
- --color-surface: #F7F8FA
- --color-muted: #7A7E86
- --color-success: #1FB764
- --color-warn: #F2B824
- --color-fail: #FF5C6C

Typography
- Outfit (300–700) and DM Mono for code/labels.

Keep these HTML IDs, attributes and form names (DO NOT rename)
- IDs: fileInput, filePreviewName, toggleInputPanel, openInputPanel
- Attributes: data-theme-toggle (theme buttons)
- Form fields: username, password (login); image (file input), sample_image (sample radio)
- Endpoints (form actions): /login, /analyze, /logout

Components to design (map to existing classes)
- Auth card `.auth-card`; Input panel `.input-panel`; Pipeline `.pipeline-panel`; Audit list `.audit-list`; Verdict card `.verdict-card`; Theme controls keep `data-theme-toggle`.

Accessibility & responsiveness
- Provide light + dark variants (JS toggles `data-theme` on `<html>` and uses localStorage key `sml-theme`).
- Ensure contrast (4.5:1 for primary buttons). Mobile-first: collapse left panel into top drawer on small screens.

Dev handoff requirements
- Deliver tokens, component library, and a short README listing preserved IDs, form names, and endpoints.
- If proposing React migration, include a minimal API checklist (e.g., POST /api/analyze accepting multipart/form-data). Prefer staged migration; keep server authoritative for results.

Figma plugin-ready short prompt
"Design a modern, accessible Login/Dashboard/Settings for SecureMLOPS. Use the attached neon-green palette and Outfit + DM Mono. Provide light & dark themes, desktop/tablet/mobile frames, and a component library. Preserve IDs (fileInput,filePreviewName,toggleInputPanel,openInputPanel), data-theme-toggle, form names (username,password,image,sample_image), and form endpoints /login,/analyze,/logout. Provide a dev-handoff README listing tokens and required DOM/endpoint invariants."

Acceptance
- Designer provides frames, tokens, component library, and a dev README listing preserved IDs, fields, and endpoints so backend remains compatible.
