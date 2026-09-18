# Open the Mimic 3D preview in your default browser.
# Serves the Drive build folder on http://localhost:8766 (FreeCAD's bundled python, no install).
# Leave the window open while you look; close it (or Ctrl+C) to stop.
#   .\preview.ps1                -> proof of concept (Mimic folder)
#   .\preview.ps1 -Sub Scale-1   -> a subfolder such as the life-size build
param([string]$Sub = "")
$root = "G:\My Drive\Projects\3D\Weyland\FNAF\Mimic"
if ($Sub) { $root = Join-Path $root $Sub }
$py = "C:\Program Files\FreeCAD 1.1\bin\python.exe"
Start-Process $py -ArgumentList "-m", "http.server", "8766", "--bind", "127.0.0.1", "--directory", "`"$root`"" -WindowStyle Minimized
Start-Sleep -Seconds 1
Start-Process "http://localhost:8766/Mimic-Viewer.html?view=iso"
