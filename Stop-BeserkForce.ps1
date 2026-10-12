$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root 'data\beserkforce.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'BeserkForce is not running.'; exit 0 }
$serverPid = [int](Get-Content -LiteralPath $pidFile -Raw)
$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if ($process) { Stop-Process -Id $serverPid }
Remove-Item -LiteralPath $pidFile -Force
Write-Host 'BeserkForce stopped.'

