# Build the Mimic.   .\run.ps1                      -> proof of concept (Scale from mimic_params.py, 0.25)
#                    .\run.ps1 -Scale 1             -> life size, into Mimic\LifeSize
#                    .\run.ps1 -Parts SnapTest,Thigh -> only those part files
param([double]$Scale = 0, [string]$Out = "", [string]$Parts = "")
$root = "G:\My Drive\Projects\3D\Weyland\FNAF\Mimic"
if ($Scale -gt 0) { $env:MIMIC_SCALE = "$Scale" } else { Remove-Item Env:MIMIC_SCALE -ErrorAction SilentlyContinue }
if (-not $Out -and $Scale -gt 0 -and $Scale -ne 0.25) { $Out = Join-Path $root ("Scale-" + $Scale) }
if ($Out)   { $env:MIMIC_OUT = $Out }     else { Remove-Item Env:MIMIC_OUT -ErrorAction SilentlyContinue }
if ($Parts) { $env:MIMIC_PARTS = $Parts } else { Remove-Item Env:MIMIC_PARTS -ErrorAction SilentlyContinue }
& "C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe" -c "exec(open('C:/Users/wende/dev/Claude/3D/mimic/build.py').read())" 2>&1 |
    ForEach-Object { $_ -replace "`t", "" -replace "\(\d+ %\)", "" } | Select-String "\[mimic\]|Traceback|Error|line \d+"
