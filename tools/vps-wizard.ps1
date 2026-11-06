#requires -Version 5.1
<#
  境外云主机向导（Windows PowerShell 版）
  ------------------------------------------------------------
  带你走完 6 步：开机器 → 记地址 → 配免密 → 跑自检 → 抓 1 个真实页面 → 收尾
  只读：不会替你买东西、不会采集数据；每一步都要你确认。
  用法：powershell -NoProfile -ExecutionPolicy Bypass -File .\vps-wizard.ps1
  可重跑：已填过的值会记住（存在同目录 vps.env）。
#>
[CmdletBinding()]
param([string]$EnvFile = '')

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$ScriptDir = $PSScriptRoot
$RepoRoot  = Split-Path -Parent $ScriptDir
if (-not $EnvFile) { $EnvFile = Join-Path $ScriptDir 'vps.env' }
$CaptureDir = Join-Path $ScriptDir 'captured'
if (-not (Test-Path $CaptureDir)) { New-Item -ItemType Directory -Path $CaptureDir -Force | Out-Null }

$TOTAL_STAGES = 6
$StageIndex = 0
$Values = @{}
$Saved  = @()

# ------------------------------------------------------------------ 库
function Clear-Screen {
    try { if ($Host.UI.RawUI) { Clear-Host } } catch { }
}

function Show-Banner {
    Clear-Screen
    Write-Host ''
    Write-Host '  境外云主机向导' -ForegroundColor Cyan
    Write-Host "  $TOTAL_STAGES 个阶段" -ForegroundColor DarkGray
    Write-Host ''
    Write-Host '  你操作浏览器和终端，向导告诉你每一步点哪里、填什么。' -ForegroundColor DarkGray
    Write-Host '  随时 Ctrl-C 退出，重新运行时已填的值会保留。' -ForegroundColor DarkGray
    Write-Host ''
    Pause-Wizard '准备好了按回车开始'
}

function Show-Stage {
    param([int]$Number, [string]$Title)
    Clear-Screen
    Write-Host ''
    Write-Host ("  ▸ 阶段 {0}/{1} · {2}" -f $Number, $TOTAL_STAGES, $Title) -ForegroundColor Cyan
    Write-Host ''
}

function Say  { param([string]$T) Write-Host ("  " + $T) }
function Step { param([string]$T) Write-Host ("  • " + $T) -ForegroundColor White }
function Note { param([string]$T) Write-Host ("  " + $T) -ForegroundColor DarkGray }
function Warn { param([string]$T) Write-Host ("  ⚠ " + $T) -ForegroundColor Yellow }

function Open-Url {
    param([string]$Url)
    Write-Host ("  ↗ 打开 " + $Url) -ForegroundColor Green
    try { Start-Process $Url | Out-Null } catch { Warn "打不开浏览器，请手动访问：$Url" }
}

function Pause-Wizard {
    param([string]$Message = '按回车继续')
    Write-Host ''
    Write-Host ("  " + $Message + " ") -ForegroundColor DarkGray -NoNewline
    [void](Read-Host)
}

function Confirm-Wizard {
    param([string]$Question)
    Write-Host ''
    Write-Host ("  ? " + $Question + " [y/N] ") -ForegroundColor Yellow -NoNewline
    $r = Read-Host
    return ($r -match '^[Yy]')
}

function Get-Saved {
    param([string]$Key)
    if ($Values.ContainsKey($Key) -and $Values[$Key]) { return $Values[$Key] }
    if (Test-Path $EnvFile) {
        $line = Get-Content $EnvFile -Encoding UTF8 | Where-Object { $_ -like "$Key=*" } | Select-Object -Last 1
        if ($line) { return $line.Substring($Key.Length + 1).Trim("'", '"') }
    }
    return ''
}

function Save-Value {
    param([string]$Key, [string]$Value)
    $Values[$Key] = $Value
    if (-not (Test-Path $EnvFile)) { New-Item -ItemType File -Path $EnvFile -Force | Out-Null }
    $lines = @()
    if (Test-Path $EnvFile) { $lines = @(Get-Content $EnvFile -Encoding UTF8 | Where-Object { $_ -notlike "$Key=*" }) }
    $lines += ("{0}={1}" -f $Key, $Value)
    Set-Content -Path $EnvFile -Value $lines -Encoding UTF8
    if ($Saved -notcontains $Key) { $Saved += $Key }
    Write-Host ("  ✓ 已记录 {0} → {1}" -f $Key, (Split-Path -Leaf $EnvFile)) -ForegroundColor Green
}

function Ask-Value {
    param([string]$Key, [string]$Prompt)
    $cur = Get-Saved $Key
    if ($cur) {
        Write-Host ("  {0} [回车沿用 {1}] " -f $Prompt, $cur) -ForegroundColor White -NoNewline
    } else {
        Write-Host ("  {0} " -f $Prompt) -ForegroundColor White -NoNewline
    }
    $in = Read-Host
    if ([string]::IsNullOrWhiteSpace($in)) { $in = $cur }
    if ([string]::IsNullOrWhiteSpace($in)) { Warn '这一项不能为空'; return Ask-Value $Key $Prompt }
    Save-Value $Key $in.Trim()
    return $in.Trim()
}

function Ask-Secret {
    param([string]$Key, [string]$Prompt)
    $cur = Get-Saved $Key
    if ($cur) { Write-Host ("  {0} [回车沿用已保存的] " -f $Prompt) -ForegroundColor White -NoNewline }
    else      { Write-Host ("  {0} " -f $Prompt) -ForegroundColor White -NoNewline }
    $sec = Read-Host -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
    if ([string]::IsNullOrEmpty($plain)) { $plain = $cur }
    if ([string]::IsNullOrEmpty($plain)) { Warn '这一项不能为空'; return Ask-Secret $Key $Prompt }
    Save-Value $Key $plain
    return $plain
}

function Get-Target { return ("{0}@{1}" -f (Get-Saved 'VPS_USER'), (Get-Saved 'VPS_HOST')) }

function Invoke-Ssh {
    param([string]$RemoteCommand)
    & ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 (Get-Target) $RemoteCommand
    $script:LastSshExit = $LASTEXITCODE
    return $script:LastSshExit
}

function Copy-ToServer {
    param([string]$LocalPath, [string]$RemoteName)
    & scp -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 $LocalPath ("{0}:{1}" -f (Get-Target), $RemoteName)
    return $LASTEXITCODE
}

function Copy-FromServer {
    param([string]$RemoteName, [string]$LocalPath)
    & scp -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 ("{0}:{1}" -f (Get-Target), $RemoteName) $LocalPath
    return $LASTEXITCODE
}

# ------------------------------------------------------------------ 阶段 1
Show-Banner

Show-Stage 1 '开一台新加坡/日本的机器'
Say '推荐用云厂商的"轻量应用服务器"：比 ECS 简单，价格透明，支付宝可付。二选一：'
Write-Host ''
Step '腾讯云轻量（推荐，页面最直观）：https://console.cloud.tencent.com/lighthouse'
Step '阿里云轻量：https://swas.console.aliyun.com/'
Write-Host ''
Say '下单时这样选（两家都差不多）：'
Step '地域：新加坡 或 日本（东京）'
Step '镜像：Ubuntu 22.04 LTS（不要选 Windows）'
Step '套餐：最低配即可（1 核 1G / 2G 都行）'
Step '时长：先买 1 个月，或按量付费（用完记得释放）'
Write-Host ''
Note '注意：国内站买境外地域是正常云服务采购，不是"翻墙工具"；需要账号实名。'
Note '如果页面让你选"带宽计费"，选按流量计费最便宜（我们只跑几 MB）。'
Open-Url 'https://console.cloud.tencent.com/lighthouse'
Pause-Wizard '买好、实例状态变成"运行中"后按回车'
if (-not (Confirm-Wizard '机器已经开好了吗')) { Warn '先开机器再来跑向导。'; exit 1 }

# ------------------------------------------------------------------ 阶段 2
Show-Stage 2 '记下公网 IP 和登录账号'
Say '回到实例列表，找到这台机器：'
Step '复制"公网 IP"（形如 43.xx.xx.xx）'
Step '登录名：Ubuntu 镜像一般是 root；腾讯云轻量是 ubuntu'
Step '如果还没设密码，在控制台点"重置密码"，设一个临时密码'
Write-Host ''
$null = Ask-Value 'VPS_HOST' '公网 IP：'
$null = Ask-Value 'VPS_USER' '登录名（直接回车用 root）：'
Note '下面是 SSH 密码。它只用于第 3 阶段配置密钥，配好后就不再需要，也不建议长期保存。'
$null = Ask-Secret 'VPS_PASS' '密码（输入不回显）：'
Write-Host ''
Warn "vps.env 里有明文密码，别提交到仓库、别发给任何人；第 6 阶段会提醒你清理。"

# ------------------------------------------------------------------ 阶段 3
Show-Stage 3 '配置免密登录（一次密码，后面都不用了）'
$keyPath = Join-Path $env:USERPROFILE '.ssh\id_ed25519'
if (-not (Test-Path $keyPath)) {
    Say '本机还没有 SSH 密钥，现在生成一个：'
    Note '如果提示 "Enter passphrase"，直接按两次回车（不设密码）。'
    New-Item -ItemType Directory -Path (Split-Path -Parent $keyPath) -Force | Out-Null
    & ssh-keygen -t ed25519 -f $keyPath
    if (-not (Test-Path $keyPath)) { Warn '生成失败或已跳过，可继续用密码登录。' }
}
$pub = "$keyPath.pub"
if (-not (Test-Path $pub)) {
    Warn '没找到公钥文件，跳过免密配置，后续每步都会要求输密码。'
} else {
    Say '把公钥装到服务器上（这一步会要求输入一次密码）：'
    $remote = 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys && echo KEY_OK'
    Get-Content $pub -Raw | & ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 (Get-Target) $remote
    if ($LASTEXITCODE -ne 0) { Warn '免密配置失败；后面仍可用密码，但会多输几次。' }
}

Say '验证一下能不能连上、系统是什么：'
Invoke-Ssh 'echo CONNECT_OK; uname -sr; curl --version | head -1' | Out-Null
if ($script:LastSshExit -ne 0) {
    Warn '连不上。常见原因：安全组没放行 22 端口 / IP 填错 / 密码错。'
    Note '可以先在云控制台点"登录"用网页终端，确认机器本身正常。'
} else {
    Write-Host '  ✓ 连接正常' -ForegroundColor Green
}
Note '如果这台机器连不上 HTTP(S) 外网，后面会立刻暴露出来，不用现在担心。'

# ------------------------------------------------------------------ 阶段 4
Show-Stage 4 '上传自检脚本并运行'
$localScript = Join-Path $ScriptDir 'check-connectivity.sh'
if (-not (Test-Path $localScript)) { Warn "找不到 $localScript，先确认文件在 tools 目录下。"; exit 1 }
Say '上传脚本：'
$null = Copy-ToServer $localScript 'check-connectivity.sh'
if ($LASTEXITCODE -ne 0) { Warn '上传失败，检查网络或改用网页终端手动粘贴。' }
Say '在服务器上运行自检（约 1–2 分钟）：'
Write-Host ''
& ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 (Get-Target) 'bash ~/check-connectivity.sh'
$selfCheckExit = $LASTEXITCODE
Write-Host ''
if ($selfCheckExit -eq 0) {
    Write-Host '  ✓ 自检通过：这台机器可以采集' -ForegroundColor Green
} elseif ($selfCheckExit -eq 2) {
    Warn '自检判定：环境不可达。换个地域再开一台（日本/新加坡互换），或换厂商。'
    if (-not (Confirm-Wizard '还要继续抓页面试试吗（可能也失败）')) { Warn '先解决可达性再回来。'; exit 2 }
} else {
    Warn '自检有警告（如 IP 被限流/需要登录），继续抓页面看实际情况。'
}
$null = Copy-FromServer 'check-output/connectivity-report.txt' (Join-Path $CaptureDir 'connectivity-report.txt')
Note '报告已拉回本机 tools\captured\connectivity-report.txt'

# ------------------------------------------------------------------ 阶段 5
Show-Stage 5 '抓 1 个真实页面（这是后面所有解析的依据）'
$ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
$rm = "curl -sS -L --compressed -A '$ua' -H 'Accept-Language: en-US,en;q=0.9' -o ~/profile.html -w 'HTTP %{http_code}  %{size_download} bytes  %{time_total}s' 'https://www.tiktok.com/@tiktok'"
Say '在服务器上抓 @tiktok 的主页并存成 profile.html：'
Write-Host ''
& ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 (Get-Target) $rm
Write-Host ''
Say '看看页面里有没有我们要的数据：'
Write-Host ''
& ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 (Get-Target) "ls -l ~/profile.html; echo '--- universal:'; grep -c '__UNIVERSAL_DATA_FOR_REHYDRATION__' ~/profile.html; echo '--- followerCount:'; grep -o 'followerCount[^,]*' ~/profile.html | head -3; echo '--- og:title:'; grep -c 'og:title' ~/profile.html"
Write-Host ''
Say '把页面拉回本机：'
$null = Copy-FromServer 'profile.html' (Join-Path $CaptureDir 'profile.html')
if (Test-Path (Join-Path $CaptureDir 'profile.html')) {
    $sz = (Get-Item (Join-Path $CaptureDir 'profile.html')).Length
    Write-Host ("  ✓ 已保存 {0}（{1:N0} 字节）" -f (Join-Path $CaptureDir 'profile.html'), $sz) -ForegroundColor Green
    if ($sz -lt 5000) { Warn '页面很小，可能是拦截页/空壳页。把文件发给我看。' }
} else {
    Warn '拉回失败。可在服务器上手动 scp，或把网页终端里的内容复制出来。'
}
Note '把这个 profile.html 发给我，我就能按真实结构写解析。'

# ------------------------------------------------------------------ 阶段 6
Show-Stage 6 '收尾：省钱 + 别泄漏'
Say '按顺序做三件事：'
Step '把公网 IP、地域、自检结论记进 README 的"运行前置条件"'
Step '包月机器：不用了就"关机"；按量付费：直接"释放/销毁"，否则继续计费'
Step '删掉本机的 tools\vps.env（里面有明文密码）'
Write-Host ''
if (Confirm-Wizard '现在就删掉 vps.env 吗（推荐，IP 已记在下面）') {
    Remove-Item $EnvFile -Force -ErrorAction SilentlyContinue
    Write-Host '  ✓ 已删除 vps.env' -ForegroundColor Green
}
Write-Host ''
Write-Host '  ── 本次记录 ──' -ForegroundColor Cyan
Write-Host ("  公网 IP : {0}" -f (Get-Saved 'VPS_HOST'))
Write-Host ("  登录名  : {0}" -f (Get-Saved 'VPS_USER'))
Write-Host ("  抓到的页面: {0}" -f (Join-Path $CaptureDir 'profile.html'))
Write-Host ("  自检报告: {0}" -f (Join-Path $CaptureDir 'connectivity-report.txt'))
Write-Host ''
Note '下一个动作：把 profile.html 发我，我按真实结构写解析器。'
Write-Host ''
