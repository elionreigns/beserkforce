# Desktop app install: window icon, pywebview, and a Desktop shortcut.
# Does not push to GitHub.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python312\python.exe'
$pythonw = Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python312\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw "Missing $pythonw" }
& $python -c "import webview" 2>$null
if ($LASTEXITCODE -ne 0) { & $python -m pip install pywebview }

$png = Join-Path $root 'web\assets\beserkforce-command-core.png'
$ico = Join-Path $root 'web\assets\beserkforce.ico'
if ((Test-Path -LiteralPath $png) -and -not (Test-Path -LiteralPath $ico)) {
  Add-Type -AssemblyName System.Drawing
  $src = [Drawing.Image]::FromFile($png)
  $bmp = New-Object Drawing.Bitmap 64, 64
  $g = [Drawing.Graphics]::FromImage($bmp)
  $g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.DrawImage($src, 0, 0, 64, 64)
  $g.Dispose(); $src.Dispose()
  $ms = New-Object IO.MemoryStream
  $bmp.Save($ms, [Drawing.Imaging.ImageFormat]::Png)
  $pngBytes = $ms.ToArray()
  $bmp.Dispose()
  $fs = [IO.File]::Create($ico)
  $bw = New-Object IO.BinaryWriter $fs
  $bw.Write([uint16]0); $bw.Write([uint16]1); $bw.Write([uint16]1)
  $bw.Write([byte]64); $bw.Write([byte]64); $bw.Write([byte]0); $bw.Write([byte]0)
  $bw.Write([uint16]1); $bw.Write([uint16]32)
  $bw.Write([uint32]$pngBytes.Length); $bw.Write([uint32]22); $bw.Write($pngBytes)
  $bw.Close()
}

$app = Join-Path $root 'BeserkForce.pyw'
$ws = New-Object -ComObject WScript.Shell
$lnkPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'BeserkForce.lnk'
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath = $pythonw
$lnk.Arguments = "`"$app`""
$lnk.WorkingDirectory = $root
$lnk.Description = 'BeserkForce'
$lnk.WindowStyle = 1
if (Test-Path -LiteralPath $ico) { $lnk.IconLocation = "$ico,0" }
$lnk.Save()
Write-Host "BeserkForce app shortcut: $lnkPath"
