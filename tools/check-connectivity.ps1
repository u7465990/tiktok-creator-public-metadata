#requires -Version 5.1
<#
  TikTok 采集连通性自检（只读）
  ------------------------------------------------------------
  作用：判断"这台机器能不能采集 TikTok 公开主页"，不采集、不落库、不改任何东西。
  依赖：Windows 10/11 自带 curl.exe，PowerShell 5.1+，无需安装任何包。
  用法：powershell -ExecutionPolicy Bypass -File .\check-connectivity.ps1
  可选：-ProbeHandle tiktok   -TimeoutSec 25
  输出：控制台一张表 + check-output\connectivity-report.txt
#>
[CmdletBinding()]
param(
    [string]$ProbeHandle    = 'tiktok',
    [string]$NotFoundHandle = 'zzzz_no_such_user_9f3a2b',
    [int]$TimeoutSec        = 25
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$UA   = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
$Base = 'https://www.tiktok.com'
$outDir = Join-Path $PSScriptRoot 'check-output'
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

$report = New-Object System.Collections.ArrayList
$facts  = @{
    CurlOk = $false; ControlCode = 0; DnsOk = $false; DnsIps = @(); DnsSuspect = $false; DnsPolluted = $false
    ProfileExit = -1; ProfileCode = 0; ProfileSize = 0; LoginRedirect = $false
    HasUniversal = $false; HasSigi = $false; HasFields = $false; Captcha = $false
    NotFoundCode = 0; NotFoundText = $false
    RobotsOk = $false; RobotsDisallowsProfile = $false
    AvatarTried = $false; AvatarOk = $false
}

function Out-Line {
    param([string]$Text, [string]$Color = 'Gray')
    Write-Host $Text -ForegroundColor $Color
    [void]$report.Add($Text)
}

function Add-Result {
    param([string]$Name, [ValidateSet('PASS','WARN','FAIL','INFO')][string]$State, [string]$Detail)
    $color = @{ PASS = 'Green'; WARN = 'Yellow'; FAIL = 'Red'; INFO = 'Gray' }[$State]
    Out-Line ("  [{0}] {1,-30} {2}" -f $State, $Name, $Detail) $color
}

function Get-Probe {
    param([string]$Url, [string]$Tag)
    $body = Join-Path $outDir "$Tag.body.html"
    $head = Join-Path $outDir "$Tag.headers.txt"
    $raw = & curl.exe -sS -L --compressed --max-redirs 5 --connect-timeout 10 --max-time $TimeoutSec `
        -A $UA -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' `
        -H 'Accept-Language: en-US,en;q=0.9' -H 'Referer: https://www.tiktok.com/' `
        -o $body -D $head `
        -w '%{http_code}|%{url_effective}|%{size_download}|%{time_total}|%{content_type}' $Url 2>$null
    $exit = $LASTEXITCODE
    $w = if ($raw) { ($raw -join '') } else { '' }
    $p = $w -split '\|'
    $size = 0
    if (Test-Path $body) { $size = (Get-Item $body).Length }
    $text = ''
    if (Test-Path $body) { $text = Get-Content -Raw -Encoding UTF8 -ErrorAction SilentlyContinue $body }
    [pscustomobject]@{
        Exit = $exit
        Code = if ($p.Count -ge 1 -and $p[0] -match '^\d+$') { [int]$p[0] } else { 0 }
        EffUrl = if ($p.Count -ge 2) { $p[1] } else { '' }
        Size = $size
        Time = if ($p.Count -ge 4) { $p[3] } else { '' }
        Type = if ($p.Count -ge 5) { $p[4] } else { '' }
        BodyPath = $body
        Text = $text
    }
}

function Test-PrivateIp {
    param([string]$Ip)
    if ($Ip -match '^(10\.|127\.|0\.|169\.254\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)') { return $true }
    if ($Ip -match '^(::1|fe80:|fc|fd)') { return $true }
    if ($Ip -match '^2001:0:') { return $true }   # Teredo，典型污染特征
    return $false
}

function Test-PollutedIp {
    # 已知的 DNS 污染"替身"网段：多为 Facebook/Meta 的地址块。
    # 命中不代表 100% 污染，但配合 TLS 失败即可定性。
    param([string]$Ip)
    $o = $Ip.Split('.')
    if ($o.Count -ne 4) { return $false }
    $a = [int]$o[0]; $b = [int]$o[1]; $c = [int]$o[2]
    if ($a -eq 69 -and $b -eq 171 -and $c -ge 224) { return $true }                          # 69.171.224.0/19
    if ($a -eq 31 -and $b -eq 13 -and $c -ge 64 -and $c -le 127) { return $true }             # 31.13.64.0/18
    if ($a -eq 179 -and $b -eq 60 -and $c -ge 192 -and $c -le 195) { return $true }           # 179.60.192.0/22
    if ($a -eq 157 -and $b -eq 240) { return $true }                                          # 157.240.0.0/16
    if ($a -eq 173 -and $b -eq 252 -and $c -ge 64 -and $c -le 127) { return $true }           # 173.252.64.0/18
    if ($a -eq 66 -and $b -eq 220 -and $c -ge 144 -and $c -le 159) { return $true }           # 66.220.144.0/20
    if ($a -eq 185 -and $b -eq 60 -and $c -ge 216 -and $c -le 219) { return $true }           # 185.60.216.0/22
    if ($a -eq 8 -and $b -eq 7 -and $c -eq 198) { return $true }                              # 8.7.198.0/24
    return $false
}

# ============================================================ 0. 环境
Out-Line ''
Out-Line '=============================================================='
Out-Line ' TikTok 采集连通性自检（只读，不采集任何数据）'
Out-Line (" 时间：{0}   主机：{1}" -f (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'), $env:COMPUTERNAME)
Out-Line '=============================================================='
Out-Line ''

$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) {
    Add-Result 'curl 可用' 'FAIL' '找不到 curl.exe（Windows 10 1803+ 自带；也可装 Git for Windows）'
    Out-Line ''
    Out-Line '结论：无法执行自检。请安装 curl 后重试。' 'Red'
    $report | Set-Content -Path (Join-Path $outDir 'connectivity-report.txt') -Encoding UTF8
    exit 2
}
$facts.CurlOk = $true
Add-Result 'curl 可用' 'PASS' ((& curl.exe --version 2>$null) -split "`n")[0]

# 对照组：证明"工具 + 出口网络"本身是通的
Out-Line ''
Out-Line '-- 1. 对照组（证明不是工具/网络整体坏了）--'
$ctl = Get-Probe 'https://example.com/' 'control'
$facts.ControlCode = $ctl.Code
if ($ctl.Code -eq 200) {
    Add-Result '对照组 example.com' 'PASS' ("HTTP {0}，{1} 字节" -f $ctl.Code, $ctl.Size)
} else {
    Add-Result '对照组 example.com' 'FAIL' ("HTTP {0}，curl 退出码 {1}（工具或整体网络异常）" -f $ctl.Code, $ctl.Exit)
}

# DNS
Out-Line ''
Out-Line '-- 2. DNS 解析 --'
try {
    $a = Resolve-DnsName -Name 'www.tiktok.com' -Type A -ErrorAction Stop
    $facts.DnsIps = @($a | Where-Object { $_.IPAddress } | Select-Object -ExpandProperty IPAddress)
    $facts.DnsOk = $facts.DnsIps.Count -gt 0
} catch {
    $facts.DnsOk = $false
}
if (-not $facts.DnsOk) {
    Add-Result 'DNS 解析 www.tiktok.com' 'FAIL' '解析失败（域名可能被污染或不可达）'
} else {
    $suspect = @($facts.DnsIps | Where-Object { Test-PrivateIp $_ })
    $polluted = @($facts.DnsIps | Where-Object { Test-PollutedIp $_ })
    $facts.DnsSuspect = $suspect.Count -gt 0
    $facts.DnsPolluted = $polluted.Count -gt 0
    if ($facts.DnsSuspect) {
        Add-Result 'DNS 解析 www.tiktok.com' 'FAIL' ("解析到非公网地址：" + ($facts.DnsIps -join ', ') + "（典型 DNS 污染）")
    } elseif ($facts.DnsPolluted) {
        Add-Result 'DNS 解析 www.tiktok.com' 'FAIL' ("解析到 Facebook/Meta 网段：" + ($facts.DnsIps -join ', ') + "（DNS 被污染，不是 TikTok 的地址）")
    } else {
        Add-Result 'DNS 解析 www.tiktok.com' 'PASS' ($facts.DnsIps -join ', ')
    }
}

# ============================================================ 主站探针
Out-Line ''
Out-Line '-- 3. 主页探针（无登录）--'
$url = "$Base/@$ProbeHandle"
Out-Line ("  请求：{0}" -f $url)
$probe = Get-Probe $url 'profile'
$facts.ProfileExit = $probe.Exit
$facts.ProfileCode = $probe.Code
$facts.ProfileSize = $probe.Size

if ($probe.Exit -ne 0) {
    $errName = @{ 6 = 'DNS 解析失败'; 7 = '无法建立连接'; 28 = '超时'; 35 = 'TLS 握手失败'; 56 = '接收数据失败' }[[int]$probe.Exit]
    if (-not $errName) { $errName = 'curl 错误' }
    Add-Result 'HTTP 请求' 'FAIL' ("curl 退出码 {0}：{1}" -f $probe.Exit, $errName)
} else {
    Add-Result 'HTTP 请求' 'PASS' ("HTTP {0}，{1} 字节，{2}s" -f $probe.Code, $probe.Size, $probe.Time)
}

$t = $probe.Text
if ($probe.Code -gt 0) {
    $facts.LoginRedirect = ($probe.EffUrl -match '/login') -or ($t -match 'Log in to TikTok|login-modal|登录以继续')
    $facts.HasUniversal  = ($t -match '__UNIVERSAL_DATA_FOR_REHYDRATION__')
    $facts.HasSigi       = ($t -match 'SIGI_STATE')
    $facts.HasFields     = ($t -match '"followerCount"\s*:\s*\d+') -or ($t -match 'property="og:title"')
    $facts.Captcha       = ($t -match 'captcha|Just a moment|_cf_chl|verify you are human|请完成验证')

    if ($facts.LoginRedirect) { Add-Result '是否跳登录' 'FAIL' ("被重定向到登录/登录弹窗：" + $probe.EffUrl) }
    else { Add-Result '是否跳登录' 'PASS' ('未跳转，最终地址：' + $probe.EffUrl) }

    if ($facts.Captcha) { Add-Result '验证码 / CF 挑战' 'FAIL' '页面含验证码或 Cloudflare 挑战标记' }
    else { Add-Result '验证码 / CF 挑战' 'PASS' '未检测到验证码标记' }

    if ($facts.HasUniversal) { Add-Result '结构化数据 UNIVERSAL' 'PASS' '找到 __UNIVERSAL_DATA_FOR_REHYDRATION__' }
    elseif ($facts.HasSigi)  { Add-Result '结构化数据 UNIVERSAL' 'WARN' '只有旧版 SIGI_STATE，主路径需用兜底' }
    else                     { Add-Result '结构化数据 UNIVERSAL' 'WARN' '未找到内嵌 JSON（可能靠 DOM/og 标签）' }

    if ($facts.HasFields) { Add-Result '关键字段' 'PASS' '页面含 followerCount 或 og:title' }
    else                  { Add-Result '关键字段' 'FAIL' '未找到粉丝数/展示名字段' }

    if ($probe.Size -lt 5000 -and -not $facts.HasUniversal) {
        Add-Result '页面体积' 'WARN' ("仅 {0} 字节，疑似软拦截空壳页" -f $probe.Size)
    } else {
        Add-Result '页面体积' 'PASS' ("{0} 字节" -f $probe.Size)
    }
}

# ============================================================ 不存在账号
if ($probe.Code -eq 200) {
    Out-Line ''
    Out-Line '-- 4. 不存在的账号（确认 404 还是 200+文案）--'
    Start-Sleep -Seconds 2
    $nf = Get-Probe "$Base/@$NotFoundHandle" 'notfound'
    $facts.NotFoundCode = $nf.Code
    $facts.NotFoundText = ($nf.Text -match "Couldn't find this account|找不到|could not be found")
    Add-Result '不存在账号的返回' 'INFO' ("HTTP {0}；含未找到文案：{1}" -f $nf.Code, $facts.NotFoundText)
}

# ============================================================ robots
Out-Line ''
Out-Line '-- 5. robots.txt --'
$rb = Get-Probe "$Base/robots.txt" 'robots'
if ($rb.Code -eq 200) {
    $facts.RobotsOk = $true
    $lines = @($rb.Text -split "`n" | Where-Object { $_ -match '^\s*(User-agent|Allow|Disallow|Sitemap)' })
    $star = @(); $inStar = $false
    foreach ($l in $lines) {
        if ($l -match '^\s*User-agent:\s*(.+)$') { $inStar = ($matches[1].Trim() -eq '*') }
        elseif ($inStar -and $l -match '^\s*(Allow|Disallow):\s*(\S+)') { $star += $l.Trim() }
    }
    $star = @($star | Select-Object -First 40)
    $lines | Select-Object -First 30 | ForEach-Object { Out-Line ("    " + $_.Trim()) 'DarkGray' }
    if ($star.Count -eq 0) {
        Add-Result 'robots 规则' 'WARN' '未找到 User-agent: * 组，需人工核对'
    } else {
        $dis = @($star | Where-Object { $_ -match '^Disallow:\s*/$' })
        $allowAt = @($star | Where-Object { $_ -match '^Allow:\s*/@' })
        $disAt = @($star | Where-Object { $_ -match '^Disallow:\s*/@' })
        $facts.RobotsDisallowsProfile = ($dis.Count -gt 0 -and $allowAt.Count -eq 0) -or ($disAt.Count -gt 0)
        if ($facts.RobotsDisallowsProfile) {
            Add-Result 'robots 是否允许 /@' 'WARN' '"/" 被 Disallow 且无 Allow: /@ → 程序应记 blocked(robots_disallow)'
        } else {
            Add-Result 'robots 是否允许 /@' 'PASS' '未见针对 /@ 的禁止规则（仍需以原文为准）'
        }
    }
} else {
    Add-Result 'robots.txt' 'WARN' ("HTTP {0}，未取得原文" -f $rb.Code)
}

# ============================================================ 头像
if ($probe.Code -eq 200 -and $probe.Text -match 'https://[^"''\\ ]*tiktokcdn[^"''\\ ]*') {
    Out-Line ''
    Out-Line '-- 6. 头像 CDN --'
    $avatarUrl = $Matches[0]
    $facts.AvatarTried = $true
    $ab = Join-Path $outDir 'avatar.probe.bin'
    $aw = & curl.exe -sS -L --connect-timeout 10 --max-time $TimeoutSec -A $UA `
        -H 'Referer: https://www.tiktok.com/' -r 0-4095 -o $ab `
        -w '%{http_code}|%{content_type}|%{size_download}' $avatarUrl 2>$null
    $ap = (($aw -join '') -split '\|')
    $acode = if ($ap[0] -match '^\d+$') { [int]$ap[0] } else { 0 }
    $acts  = if ($ap.Count -ge 2) { $ap[1] } else { '' }
    $facts.AvatarOk = ($acode -in 200, 206) -and ($acts -match '^image/')
    if ($facts.AvatarOk) {
        Add-Result '头像可匿名下载' 'PASS' ("HTTP {0}，{1}" -f $acode, $acts)
    } else {
        Add-Result '头像可匿名下载' 'WARN' ("HTTP {0}，{1}（可能校验 Referer 或已过期）" -f $acode, $acts)
    }
}

# ============================================================ 结论
Out-Line ''
Out-Line '-- 结论 --'
$verdict = ''; $advice = @()
if (-not $facts.CurlOk) {
    $verdict = '工具缺失'
} elseif ($facts.ControlCode -ne 200) {
    $verdict = '本机网络整体异常（连 example.com 都不通）'
    $advice = @('先解决本机网络/代理，再谈 TikTok。')
} elseif ($facts.DnsPolluted -or $facts.DnsSuspect) {
    $verdict = 'DNS 被污染：拿到的是假地址'
    $advice = @('解析结果不属于 TikTok，重试/换 UA/降速都没用。',
                '换境外云主机（新加坡/日本）运行，或向招聘方申请运行环境。')
} elseif ($facts.ProfileExit -in 6, 7, 28, 35) {
    $verdict = '环境不可达：DNS/连接层被拦'
    $advice = @('这台机器无法访问 TikTok，不要在这里跑采集。',
                '换境外云主机（新加坡/日本）运行，或向招聘方申请运行环境。')
} elseif ($facts.ProfileCode -in 403, 429) {
    $verdict = 'IP 被限流/封禁'
    $advice = @('降低频率、换网络出口；不要试图绕过。',
                '如实记 blocked，并在报告里写明 IP 受限。')
} elseif ($facts.LoginRedirect) {
    $verdict = '需要登录才能看主页'
    $advice = @('按题面要求记 blocked，不要加 Cookie。')
} elseif ($facts.ProfileCode -eq 200 -and $facts.HasFields) {
    $verdict = '可用：可采集'
    if ($facts.HasUniversal) { $advice = @('走内嵌 JSON 解析；仍保留 og: 标签兜底。') }
    else { $advice = @('没有内嵌 JSON，先用 og:title/og:description 兜底，再评估 DOM 解析。') }
    if ($facts.RobotsDisallowsProfile) { $advice += 'robots 可能禁止主页，需在程序里做守卫并如实记录。' }
} elseif ($facts.ProfileCode -eq 200) {
    $verdict = '页面可访问但未找到数据（疑似改版或软拦截）'
    $advice = @('保存的页面已存到 check-output\profile.body.html，发回来人工看一下。')
} else {
    $verdict = ("未知情况（HTTP {0}，curl 退出码 {1}）" -f $facts.ProfileCode, $facts.ProfileExit)
    $advice = @('把 check-output 整个目录发回来。')
}

Out-Line ("  判定：{0}" -f $verdict) 'White'
foreach ($a in $advice) { Out-Line ("  → " + $a) 'Cyan' }
Out-Line ''
Out-Line ("  产物目录：{0}" -f $outDir)
Out-Line '  （report + 抓到的页面原文；不含任何 Cookie/凭据）'

$report | Set-Content -Path (Join-Path $outDir 'connectivity-report.txt') -Encoding UTF8

if ($verdict -like '可用*') { exit 0 }
elseif ($verdict -like '环境不可达*' -or $verdict -like '工具缺失*' -or $verdict -like '本机网络*' -or $verdict -like 'DNS 被污染*') { exit 2 }
else { exit 1 }
