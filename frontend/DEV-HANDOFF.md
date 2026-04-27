# SecureMLOPS - Dev Handoff Documentation

## Overview
Modern, accessible UI for SecureMLOPS with light/dark theme support. Built with React, TypeScript, and Tailwind CSS while preserving Flask-compatible HTML structure.

## Design Tokens

### Colors
```css
/* Light Theme */
--color-accent: #7CFF00 (neon green - primary brand color)
--color-accent-600: #5EE600 (darker accent for hover states)
--color-bg: #0F1113 (dark background)
--color-surface: #F7F8FA (light surface)
--color-muted: #7A7E86 (muted text)
--color-success: #1FB764 (success state)
--color-warning: #F2B824 (warning state)
--color-fail: #FF5C6C (error/destructive state)

/* Dark Theme */
Dark theme uses same accent colors with inverted backgrounds
```

### Typography
- **Primary Font**: Outfit (300, 400, 500, 600, 700)
- **Monospace Font**: DM Mono (300, 400, 500)
- Use `.font-mono` class for code/labels

## Preserved HTML Structure (Flask Compatibility)

### Required HTML IDs
These IDs **MUST** be preserved for Flask JavaScript integration:

| ID | Element | Location | Purpose |
|---|---|---|---|
| `fileInput` | `<input type="file">` | Dashboard > Input Panel | File upload input |
| `filePreviewName` | `<p>` | Dashboard > Input Panel | Display selected filename |
| `toggleInputPanel` | `<button>` | Dashboard > Input Panel Header | Toggle panel visibility |
| `openInputPanel` | `<button>` | Dashboard > Input Panel | Submit button (opens panel state) |

### Required Form Field Names
These `name` attributes **MUST** be preserved for Flask form handling:

| Name | Type | Form | Endpoint |
|---|---|---|---|
| `username` | text input | Login form | `/login` |
| `password` | password input | Login form | `/login` |
| `image` | file input | Analysis form | `/analyze` |
| `sample_image` | radio input | Analysis form | `/analyze` |

### Required HTML Attributes

| Attribute | Element | Purpose |
|---|---|---|
| `data-theme-toggle` | `<button>` | Theme toggle buttons (tracks theme state) |
| `data-theme` | `<html>` | Root element attribute (set to 'light' or 'dark') |

### Form Endpoints (Flask Routes)

| Endpoint | Method | Form | Purpose |
|---|---|---|---|
| `/login` | POST | Login form | User authentication |
| `/analyze` | POST | Analysis form | Submit model for analysis |
| `/logout` | POST/GET | Logout button | End user session |

## CSS Class Reference

### Component Classes
These classes map to Flask template sections:

| Class | Component | Description |
|---|---|---|
| `.auth-card` | Login | Main authentication card |
| `.input-panel` | Dashboard | Left panel for file upload/sample selection |
| `.pipeline-panel` | Dashboard | Main pipeline stages visualization |
| `.audit-list` | Dashboard | Audit log display |
| `.verdict-card` | Dashboard | Analysis verdict/results card |

## Theme Management

### JavaScript API
```javascript
// Get current theme
const theme = localStorage.getItem('sml-theme'); // 'light' or 'dark'

// Set theme
localStorage.setItem('sml-theme', 'dark');
document.documentElement.setAttribute('data-theme', 'dark');
document.documentElement.classList.add('dark'); // or .remove('dark')
```

### localStorage Key
- **Key**: `sml-theme`
- **Values**: `'light'` | `'dark'`

## Accessibility Features

### Contrast Ratios
- Primary buttons (accent): 4.5:1 minimum
- Text on backgrounds: 4.5:1 minimum
- Large text: 3:1 minimum

### Responsive Breakpoints
- **Mobile**: < 1024px (lg breakpoint)
  - Sidebar collapses to mobile menu
  - Input panel becomes full-width collapsible section
- **Desktop**: ≥ 1024px
  - Fixed sidebar navigation
  - Side-by-side input panel and pipeline view

### Keyboard Navigation
- All interactive elements are keyboard accessible
- Focus states use `--color-ring` (#7CFF00)
- Logical tab order preserved

## Component Structure

### Login (`/src/app/components/Login.tsx`)
- Centered auth card
- Form fields: username, password
- Form action: `/login` (POST)
- Shield icon branding

### Dashboard (`/src/app/components/Dashboard.tsx`)
- **Layout**: Responsive multi-column layout with sidebar, input panel, and main content area
- **Sidebar Navigation**: Desktop fixed sidebar / Mobile collapsible menu
- **Stats Grid**: 4-card KPI dashboard showing Total Scans, Safe Models, Threats Detected, Avg Analysis Time
- **Input Panel**: Collapsible left panel with file upload & sample selection (preserves Flask IDs)
- **Pipeline Visualization**: 9-stage analysis pipeline with:
  - Status indicators (pending, running, success, warning, error)
  - Progress bars for running stages
  - Expandable details for each stage
  - Duration tracking
- **Current Analysis Card**: Real-time display of active scan with model details
- **Recent Scans**: Right sidebar showing last 3 scans with verdict badges
- **Quick Actions Panel**: Shortcut buttons for common operations
- **Audit Log**: Full-width timestamped log with status badges
- Form action: `/analyze` (POST, multipart/form-data)

### Settings (`/src/app/components/Settings.tsx`)
- **Layout**: 2-column grid layout for settings categories
- **General Settings**: Scan depth, file size limits, log retention
- **Security Settings**: Threat threshold, quarantine status, protection indicators
- **Analysis Features**: 4 feature toggles (Behavioral, Signature, Anomaly, Real-time)
- **Notifications**: Email and Slack integration toggles
- Visual indicators for security status
- Back navigation to dashboard

### Theme Toggle (`/src/app/components/ThemeToggle.tsx`)
- Sun/Moon icon toggle
- Persists to localStorage (`sml-theme` key)
- Manages HTML class and data-theme attribute

## Migration Notes

### If Migrating to Full React/API
Current implementation maintains Flask form compatibility. For API migration:

1. **Endpoints to Create**:
   - `POST /api/login` - Accept JSON `{username, password}`
   - `POST /api/analyze` - Accept `multipart/form-data` with `image` file or `sample_image` string
   - `POST /api/logout` - Clear session
   - `GET /api/settings` - Get current settings
   - `PUT /api/settings` - Update settings

2. **State Management**:
   - Add authentication state (JWT/session)
   - WebSocket for real-time pipeline updates
   - Consider React Query or similar for data fetching

3. **Keep Server Authoritative**:
   - Server determines analysis results
   - Client displays pipeline progress
   - Maintain audit log on backend

## File Structure
```
src/
├── app/
│   ├── App.tsx                 # Main app with routing logic
│   └── components/
│       ├── Login.tsx           # Login page
│       ├── Dashboard.tsx       # Main dashboard with pipeline
│       ├── Settings.tsx        # Settings page
│       └── ThemeToggle.tsx     # Theme switcher component
├── styles/
│   ├── theme.css              # Color tokens and theme definitions
│   └── fonts.css              # Font imports (Outfit, DM Mono)
```

## New Components Added

### Stats Cards
- Display key metrics (Total Scans, Safe Models, Threats, Avg Time)
- Icons from lucide-react (TrendingUp, FileCheck, AlertTriangle, Clock)
- Color-coded status indicators

### Recent Scans List
- Shows last 3 scans with verdict badges
- Color-coded by verdict (safe=green, suspicious=yellow, malicious=red)
- Displays filename, timestamp, and score

### Quick Actions Panel
- Shortcut buttons for common operations
- Upload Model, View Reports, System Status

### Enhanced Pipeline
- Progress bars for running stages
- Duration tracking for completed stages
- Expandable stage details with messages
- Visual status indicators

### Audit Log Enhancements
- Timestamped entries with ISO format
- Status badges (INFO, SUCCESS, WARNING, ERROR)
- Color-coded by severity
- Expandable details field

## Testing Checklist

- [ ] Verify all HTML IDs are present and functional (`fileInput`, `filePreviewName`, `toggleInputPanel`, `openInputPanel`)
- [ ] Confirm form field names match Flask expectations (`username`, `password`, `image`, `sample_image`)
- [ ] Test form submissions to `/login` and `/analyze` endpoints
- [ ] Validate theme toggle persists across sessions (localStorage `sml-theme`)
- [ ] Check responsive behavior on mobile (< 1024px) / tablet / desktop (≥ 1024px)
- [ ] Verify 4.5:1 contrast ratio on all text and buttons
- [ ] Test keyboard navigation through all interactive elements
- [ ] Ensure file upload accepts .h5, .pt, .pkl, .onnx formats
- [ ] Validate sample radio selection works correctly
- [ ] Test stats grid responsive behavior (4 cols desktop → 2 cols tablet → 1 col mobile)
- [ ] Verify pipeline progress bars animate correctly
- [ ] Test expandable pipeline stage details
- [ ] Check audit log status badge colors in light/dark themes

## Support

For questions about Flask integration or backend compatibility, ensure:
1. Form `action` attributes point to correct endpoints
2. Form `method` is POST where required
3. File input has `encType="multipart/form-data"`
4. All required IDs and names are preserved
