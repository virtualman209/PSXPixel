# Tạo / xoá lối tắt PSX Pixel trên Start Menu và Desktop.
param([string]$PythonW, [string]$AppDir, [switch]$Remove)
$places = @([Environment]::GetFolderPath("Programs"), [Environment]::GetFolderPath("Desktop"))
foreach ($p in $places) {
    $lnk = Join-Path $p "PSX Pixel.lnk"
    if ($Remove) { Remove-Item $lnk -ErrorAction SilentlyContinue; continue }
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
    $s.TargetPath = $PythonW
    $s.Arguments = '"' + (Join-Path $AppDir "psxpixel.pyw") + '"'
    $s.WorkingDirectory = $AppDir
    $s.IconLocation = (Join-Path $AppDir "psxpixel.ico") + ",0"
    $s.Description = "PSX Pixel - chuyển tranh thành pixel art kiểu PS1"
    $s.Save()
}
