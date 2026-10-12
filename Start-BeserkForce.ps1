$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = 'C:\Users\Eric the Prince\AppData\Local\Programs\Python\Python313\python.exe'
$pidFile = Join-Path $root 'data\beserkforce.pid'
$logDir = Join-Path $root 'data\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
if (Test-Path -LiteralPath $pidFile) {
  $oldPid = [int](Get-Content -LiteralPath $pidFile -Raw)
  if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue) {
    Start-Process 'http://127.0.0.1:8877'
    exit 0
  }
}
$app = Join-Path $root 'app.py'
$arguments = '"{0}" serve' -f $app
$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'server.out.log') -RedirectStandardError (Join-Path $logDir 'server.err.log') -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Start-Sleep -Milliseconds 900
Start-Process 'http://127.0.0.1:8877'

