# SecureMLOPS: End-to-End Commands

> PowerShell commands for Windows. Run from the repo root unless noted.

## 1) Backend setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2) Frontend setup

```powershell
Set-Location -LiteralPath .\frontend
npm install
Set-Location -LiteralPath ..
```

## 3) Run the platform (option A: Flask serves built React)

```powershell
Set-Location -LiteralPath .\frontend
npm run build
Set-Location -LiteralPath ..
python app.py
```

Open:

- `http://127.0.0.1:5000`

## 4) Run the platform (option B: React dev server + Flask API)

Terminal 1:

```powershell
python app.py
```

Terminal 2:

```powershell
Set-Location -LiteralPath .\frontend
npm run dev
```

Open:

- `http://127.0.0.1:5173`

## 5) Tests

```powershell
pytest
```

## 6) Security audit (frontend)

```powershell
Set-Location -LiteralPath .\frontend
npm audit
```
