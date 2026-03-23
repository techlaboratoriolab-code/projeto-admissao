$ErrorActionPreference = 'Stop'

$start = [datetime]'2026-03-02'
$end   = [datetime]'2026-03-19 23:59:59'

$files = Get-ChildItem "backend/logs" -Filter "api_admissao.log*" |
    Where-Object { $_.Name -ne 'nul' } |
    Sort-Object LastWriteTime

$accessByDayLogin  = @{}
$successByDayLogin = @{}
$accessByLogin     = @{}
$successByLogin    = @{}

$currentUser = 'PADRAO'

foreach ($file in $files) {
    Get-Content $file.FullName | ForEach-Object {
        $line = $_

        if ($line -match '^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})') {
            $dt = [datetime]::ParseExact(($matches[1] + ' ' + $matches[2]), 'yyyy-MM-dd HH:mm:ss', $null)
            if ($dt -lt $start -or $dt -gt $end) { return }

            $day = $matches[1]

            if ($line -match '\[SalvarAdmissao\] Credenciais apLIS:.*usuario=([^\s]+)') {
                $u = $matches[1]
                if ([string]::IsNullOrWhiteSpace($u)) { $u = 'PADRAO' }
                $currentUser = $u

                $k = "$day|$currentUser"
                if (-not $accessByDayLogin.ContainsKey($k)) { $accessByDayLogin[$k] = 0 }
                $accessByDayLogin[$k]++

                if (-not $accessByLogin.ContainsKey($currentUser)) { $accessByLogin[$currentUser] = 0 }
                $accessByLogin[$currentUser]++
            }

            if ($line -match '\[SalvarAdmissao\].*Sucesso! CodRequisicao:') {
                $u2 = $currentUser
                if ([string]::IsNullOrWhiteSpace($u2)) { $u2 = 'PADRAO' }

                $k2 = "$day|$u2"
                if (-not $successByDayLogin.ContainsKey($k2)) { $successByDayLogin[$k2] = 0 }
                $successByDayLogin[$k2]++

                if (-not $successByLogin.ContainsKey($u2)) { $successByLogin[$u2] = 0 }
                $successByLogin[$u2]++
            }
        }
    }
}

$out = New-Object System.Text.StringBuilder

[void]$out.AppendLine('=== ACESSOS POR DIA E LOGIN (02-19/03) ===')
$rows1 = $accessByDayLogin.GetEnumerator() | Sort-Object Name | ForEach-Object {
    $p = $_.Name.Split('|')
    [pscustomobject]@{ Dia = $p[0]; Login = $p[1]; Acessos = $_.Value }
}
[void]$out.AppendLine(($rows1 | Format-Table -AutoSize | Out-String))

[void]$out.AppendLine('=== REQUISICOES CADASTRADAS COM SUCESSO POR DIA E LOGIN (02-19/03) ===')
$rows2 = $successByDayLogin.GetEnumerator() | Sort-Object Name | ForEach-Object {
    $p = $_.Name.Split('|')
    [pscustomobject]@{ Dia = $p[0]; Login = $p[1]; Requisicoes = $_.Value }
}
[void]$out.AppendLine(($rows2 | Format-Table -AutoSize | Out-String))

[void]$out.AppendLine('=== TOTAL DE ACESSOS POR LOGIN (02-19/03) ===')
$rows3 = $accessByLogin.GetEnumerator() | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{ Login = $_.Key; Acessos = $_.Value }
}
[void]$out.AppendLine(($rows3 | Format-Table -AutoSize | Out-String))

[void]$out.AppendLine('=== TOTAL DE REQUISICOES CADASTRADAS POR LOGIN (02-19/03) ===')
$rows4 = $successByLogin.GetEnumerator() | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{ Login = $_.Key; Requisicoes = $_.Value }
}
[void]$out.AppendLine(($rows4 | Format-Table -AutoSize | Out-String))

[void]$out.AppendLine('=== DIAS COM DADOS NO PERIODO ===')
$days = @()
$accessByDayLogin.Keys  | ForEach-Object { $days += $_.Split('|')[0] }
$successByDayLogin.Keys | ForEach-Object { $days += $_.Split('|')[0] }
[void]$out.AppendLine(($days | Sort-Object -Unique | Out-String))

$outPath = 'backend/logs/relatorio_acessos_2026-03-02_a_2026-03-19.txt'
Set-Content -Path $outPath -Value $out.ToString() -Encoding UTF8
Write-Output "RELATORIO_GERADO: $outPath"