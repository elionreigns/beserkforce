$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCandidates = @(
  (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python312\python.exe'),
  (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python313\python.exe')
)
$python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $python) { throw 'Python 3.12 or 3.13 is required. The default Python 3.14 on this PC has no Pacific/Honolulu time zone data.' }
$pythonw = [IO.Path]::ChangeExtension($python, 'pythonw.exe')
if (-not (Test-Path -LiteralPath $pythonw)) { $pythonw = $python }
& $python -c "import webview" 2>$null
if ($LASTEXITCODE -ne 0) {
  & $python -m pip install pywebview
  if ($LASTEXITCODE -ne 0) { throw 'pywebview is required for the BeserkForce window.' }
}
$app = Join-Path $root 'BeserkForce.pyw'
Start-Process -FilePath $pythonw -ArgumentList "`"$app`"" -WorkingDirectory $root
