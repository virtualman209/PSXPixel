# Cài PSX Pixel chỉ bằng 1 lệnh (PowerShell).
# Repo private: đặt token trước rồi tải script này qua GitHub API (xem README):
#   $env:PSXPIXEL_TOKEN = "github_pat_..."
#   irm "https://api.github.com/repos/virtualman209/PSXPixel/contents/setup.ps1" -Headers @{Authorization="Bearer $env:PSXPIXEL_TOKEN"; Accept="application/vnd.github.raw"} | iex
# Repo public:
#   irm https://raw.githubusercontent.com/virtualman209/PSXPixel/main/setup.ps1 | iex
$ErrorActionPreference = "Stop"
$repo  = "virtualman209/PSXPixel"
$token = $env:PSXPIXEL_TOKEN
$dest  = Join-Path $env:LOCALAPPDATA "PSXPixel"
$zip   = Join-Path $env:TEMP "PSXPixel.zip"
$tmp   = Join-Path $env:TEMP "PSXPixel_setup"
function Get-PSXZip($repo, $token, $out) {
    if ($token) {
        $h = @{ Authorization = "Bearer $token"; "User-Agent" = "PSXPixel" }
        Invoke-WebRequest "https://api.github.com/repos/$repo/zipball/main" -Headers $h -OutFile $out -UseBasicParsing
    } else {
        Invoke-WebRequest "https://codeload.github.com/$repo/zip/refs/heads/main" -OutFile $out -UseBasicParsing
    }
}

Write-Host "Đang tải PSX Pixel từ GitHub..." -ForegroundColor Cyan
try { Get-PSXZip $repo $token $zip }
catch { Write-Host "Tải thất bại. Repo private cần token hợp lệ (xem README). $_" -ForegroundColor Red; return }
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Expand-Archive $zip $tmp -Force
$src = Get-ChildItem $tmp -Directory | Select-Object -First 1
New-Item -ItemType Directory -Force $dest | Out-Null
Get-ChildItem $src.FullName -Force | Where-Object { @("styles.json", "settings.json", "github_token.txt") -notcontains $_.Name } |
    ForEach-Object { Copy-Item $_.FullName $dest -Recurse -Force }
Remove-Item $zip, $tmp -Recurse -Force
if ($token) { Set-Content (Join-Path $dest "github_token.txt") $token -NoNewline -Encoding ASCII }

Write-Host "Đã chép vào $dest" -ForegroundColor Green
Start-Process -FilePath (Join-Path $dest "install.bat") -WorkingDirectory $dest -Wait
