$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCandidates = @(
  (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python313\python.exe'),
  (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python312\python.exe'),
  'C:\Python314\python.exe'
)
$python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $python) {
  $python = (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
}
if (-not $python) { throw 'Python 3.11 or newer is required to start BeserkForce.' }
$pidFile = Join-Path $root 'data\beserkforce.pid'
$logDir = Join-Path $root 'data\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
if (Test-Path -LiteralPath $pidFile) {
  $oldPid = [int](Get-Content -LiteralPath $pidFile -Raw)
  if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue) {
    try {
      $ready = Invoke-RestMethod -Uri 'http://127.0.0.1:8877/api/health' -TimeoutSec 2
      if ($ready.ok) { Start-Process 'http://127.0.0.1:8877'; exit 0 }
    } catch {}
  }
}
$app = Join-Path $root 'app.py'
$arguments = '"{0}" serve' -f $app
$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'server.out.log') -RedirectStandardError (Join-Path $logDir 'server.err.log') -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
for ($i=0; $i -lt 24; $i++) {
  try {
    $ready = Invoke-RestMethod -Uri 'http://127.0.0.1:8877/api/health' -TimeoutSec 1
    if ($ready.ok) { Start-Process 'http://127.0.0.1:8877'; exit 0 }
  } catch {}
  Start-Sleep -Milliseconds 500
}
throw 'BeserkForce did not answer its local health endpoint after launch.'

