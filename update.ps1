# Tải bản mới nhất từ GitHub và chép đè vào thư mục cài đặt (giữ style, cấu hình và token).
param([string]$AppDir = $PSScriptRoot)
$ErrorActionPreference = "Stop"
$repo = "virtualman209/PSXPixel"
$keep = @("styles.json", "settings.json", "update_state.json", "github_token.txt", "bin", ".git")
$zip = Join-Path $env:TEMP "PSXPixel_update.zip"
$tmp = Join-Path $env:TEMP "PSXPixel_update"
$tokFile = Join-Path $AppDir "github_token.txt"
$token = if (Test-Path $tokFile) { (Get-Content $tokFile -Raw).Trim() } else { $env:PSXPIXEL_TOKEN }
function Get-PSXZip($repo, $token, $out) {
    if ($token) {
        $h = @{ Authorization = "Bearer $token"; "User-Agent" = "PSXPixel" }
        Invoke-WebRequest "https://api.github.com/repos/$repo/zipball/main" -Headers $h -OutFile $out -UseBasicParsing
    } else {
        Invoke-WebRequest "https://codeload.github.com/$repo/zip/refs/heads/main" -OutFile $out -UseBasicParsing
    }
}

try {
    Write-Host "Đang tải bản mới PSX Pixel..." -ForegroundColor Cyan
    Get-PSXZip $repo $token $zip
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Expand-Archive $zip $tmp -Force
    $src = (Get-ChildItem $tmp -Directory | Select-Object -First 1).FullName
    if (-not (Test-Path (Join-Path $src "psxpixel.pyw"))) { throw "Gói cập nhật không hợp lệ." }
    Get-ChildItem $src -Force | Where-Object { $keep -notcontains $_.Name } | ForEach-Object {
        Copy-Item $_.FullName $AppDir -Recurse -Force
    }
    Remove-Item $zip, $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Đã cập nhật." -ForegroundColor Green
    exit 0
} catch {
    Write-Host "Cập nhật thất bại: $_" -ForegroundColor Red
    Set-Content (Join-Path $AppDir "update_error.txt") "$_" -Encoding UTF8
    Start-Sleep 5
    exit 1
}
