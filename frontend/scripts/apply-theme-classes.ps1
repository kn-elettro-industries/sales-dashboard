# Map legacy hex Tailwind classes to theme tokens (run from frontend/).
$root = Join-Path $PSScriptRoot "..\src"
Get-ChildItem -Path $root -Recurse -Include *.tsx,*.ts | ForEach-Object {
    $p = $_.FullName
    $c = [System.IO.File]::ReadAllText($p)
    $orig = $c
    $c = $c -replace 'border-l-4 border-\[#daa520\]', 'border-l-4 border-app-gold'
    $c = $c -replace 'bg-\[#0d1117\]/50', 'bg-app-bg/50'
    $c = $c -replace 'bg-\[#0d1117\]/40', 'bg-app-bg/40'
    $c = $c -replace 'bg-\[#0d1117\]/30', 'bg-app-bg/30'
    $c = $c -replace 'border-\[#30363d\]/50', 'border-app-border/50'
    $c = $c -replace 'border-\[#daa520\]/50', 'border-app-gold/50'
    $c = $c -replace 'border-\[#daa520\]/35', 'border-app-gold/35'
    $c = $c -replace 'shadow-\[#daa520\]/20', 'shadow-app-gold/20'
    $c = $c -replace 'hover:shadow-\[#daa520\]/20', 'hover:shadow-app-gold/20'
    $c = $c -replace 'from-\[#b8860b\] to-\[#daa520\]', 'from-app-gold-hover to-app-gold'
    $c = $c -replace 'bg-\[#0d1117\]', 'bg-app-bg'
    $c = $c -replace 'bg-\[#161b22\]', 'bg-app-card'
    $c = $c -replace 'divide-\[#30363d\]', 'divide-app-border'
    $c = $c -replace 'border-\[#30363d\]', 'border-app-border'
    $c = $c -replace 'bg-\[#21262d\]', 'bg-app-hover'
    $c = $c -replace 'hover:bg-\[#21262d\]', 'hover:bg-app-hover'
    $c = $c -replace 'hover:bg-\[#2d333b\]', 'hover:bg-app-muted'
    $c = $c -replace 'hover:bg-\[#30363d\]', 'hover:bg-app-border-strong'
    $c = $c -replace 'bg-\[#30363d\]', 'bg-app-border-strong'
    $c = $c -replace 'hover:bg-\[#2a2414\]', 'hover:bg-app-gold-muted'
    $c = $c -replace 'bg-\[#2a2414\]', 'bg-app-gold-muted'
    $c = $c -replace 'hover:bg-\[#b8860b\]', 'hover:bg-app-gold-hover'
    $c = $c -replace 'bg-\[#b8860b\]', 'bg-app-gold-hover'
    $c = $c -replace 'bg-\[#daa520\]', 'bg-app-gold'
    $c = $c -replace 'text-\[#daa520\]', 'text-app-gold'
    $c = $c -replace 'text-\[#0d1117\]', 'text-app-on-gold'
    $c = $c -replace 'border-\[#daa520\]', 'border-app-gold'
    $c = $c -replace 'focus:ring-\[#daa520\]', 'focus:ring-app-gold'
    $c = $c -replace 'focus:border-\[#daa520\]', 'focus:border-app-gold'
    $c = $c -replace 'ring-\[#daa520\]', 'ring-app-gold'
    $c = $c -replace 'accent-\[#daa520\]', 'accent-app-gold'
    if ($c -ne $orig) {
        [System.IO.File]::WriteAllText($p, $c)
        Write-Host "Updated $p"
    }
}
