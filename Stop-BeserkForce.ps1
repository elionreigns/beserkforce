$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root 'data\beserkforce.pid'
if (Test-Path -LiteralPath $pidFile) {
  $serverPid = [int](Get-Content -LiteralPath $pidFile -Raw)
  if (Get-Process -Id $serverPid -ErrorAction SilentlyContinue) { Stop-Process -Id $serverPid -Force }
  Remove-Item -LiteralPath $pidFile -Force
}
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*BeserkForce.pyw*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host 'BeserkForce stopped.'
