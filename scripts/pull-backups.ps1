<#
.SYNOPSIS
  Baja a este PC los backups de PostgreSQL que deja deploy/backup-db.sh en el servidor.

.DESCRIPTION
  Copia /home/ubuntu/backups/{daily,weekly}/*.sql.gz a una carpeta LOCAL y comprueba que cada archivo bajado es un
  gzip integro. Nunca borra nada, ni en el servidor ni aqui. Es de solo lectura sobre el servidor.

  - La IP y la ruta de la clave se leen de SERVER_INFO.local.md (gitignorado); este script no lleva datos del servidor.
  - Usa la clave de ADMINISTRACION (la de ssh normal). La clave de logs (qa_portfolio_logs) es de solo lectura con
    comando forzado y NO sirve para scp; la de deploy tampoco.
  - Los dumps contienen los datos de la base (proyectos y el usuario admin con su hash): el destino debe quedar FUERA
    de cualquier repositorio git. El script se niega a escribir dentro de uno y avisa si el destino esta en OneDrive.
  - StrictHostKeyChecking=yes: si la huella del servidor cambia, falla en vez de aceptarla en silencio.

.PARAMETER Destination
  Carpeta local. Por defecto C:\Users\<tu usuario>\Documents\qa-portfolio-backups.

.PARAMETER DryRun
  No se conecta: solo muestra que haria (ruta de la clave, usuario, destino y comandos).

.EXAMPLE
  powershell -File scripts\pull-backups.ps1 -DryRun
  powershell -File scripts\pull-backups.ps1
#>
[CmdletBinding()]
param(
    [string]$Destination = (Join-Path $env:USERPROFILE 'Documents\qa-portfolio-backups'),
    [string]$ServerInfo,
    [string]$HostName,
    [string]$KeyPath,
    [string]$User = 'ubuntu',
    [string]$RemoteDir = '/home/ubuntu/backups',
    [string]$ScpPath,   # solo para pruebas: sustituir scp por un doble local
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Fail([string]$msg) { Write-Host "pull-backups: $msg" -ForegroundColor Red; exit 1 }

# (en Windows PowerShell 5.1 $PSScriptRoot no esta disponible en los valores por defecto de param())
if (-not $ServerInfo) { $ServerInfo = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\SERVER_INFO.local.md' }

# ---------- 1. Datos de conexion (de SERVER_INFO.local.md salvo que se pasen por parametro)
if (-not $HostName -or -not $KeyPath) {
    if (-not (Test-Path -LiteralPath $ServerInfo)) { Fail "no existe $ServerInfo y faltan -HostName / -KeyPath" }
    $info = Get-Content -LiteralPath $ServerInfo -Raw
    if (-not $HostName) {
        $m = [regex]::Match($info, '(?m)IP p\S*:\*\*\s*(\d{1,3}(?:\.\d{1,3}){3})')
        if (-not $m.Success) { Fail 'no encontre la IP en SERVER_INFO.local.md; usa -HostName' }
        $HostName = $m.Groups[1].Value
    }
    if (-not $KeyPath) {
        $m = [regex]::Match($info, 'ssh -i "([^"]+)"')
        if (-not $m.Success) { Fail 'no encontre la ruta de la clave en SERVER_INFO.local.md; usa -KeyPath' }
        $KeyPath = $m.Groups[1].Value
    }
}
if ($KeyPath -match 'qa_portfolio_(logs|deploy)') { Fail 'esa clave tiene comando forzado y no sirve para scp: usa la de administracion' }
if (-not (Test-Path -LiteralPath $KeyPath)) { Fail "no existe la clave: $KeyPath" }

# ---------- 2. El destino no puede estar dentro de un repositorio git (los dumps llevan datos de la base)
$Destination = [System.IO.Path]::GetFullPath($Destination)
$probe = $Destination
while ($probe) {
    if (Test-Path -LiteralPath (Join-Path $probe '.git')) { Fail "el destino esta dentro de un repositorio git ($probe): elige otra carpeta" }
    $parent = Split-Path -Parent $probe
    if ($parent -eq $probe) { break }
    $probe = $parent
}
if ($env:OneDrive -and $Destination.StartsWith($env:OneDrive, [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host 'AVISO: el destino esta dentro de OneDrive: los dumps se sincronizarian a la nube.' -ForegroundColor Yellow
}

# ---------- 3. Cliente scp: el de Windows si existe (el de Git Bash usa otras reglas de permisos de claves)
$scp = $ScpPath
if (-not $scp) { $scp = Join-Path $env:SystemRoot 'System32\OpenSSH\scp.exe' }
if (-not (Test-Path -LiteralPath $scp)) { $scp = (Get-Command scp -ErrorAction Stop).Source }

$sshOpts = @('-i', $KeyPath, '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20')

Write-Host "Servidor : $User@$HostName"
Write-Host "Clave    : $KeyPath"
Write-Host "Destino  : $Destination"
Write-Host "scp      : $scp"

if ($DryRun) {
    foreach ($kind in 'daily', 'weekly') {
        Write-Host "[DryRun] scp $($sshOpts -join ' ') ${User}@${HostName}:${RemoteDir}/$kind/db-*.sql.gz -> $Destination\$kind"
    }
    Write-Host '[DryRun] no se conecto a nada ni se creo ninguna carpeta.'
    exit 0
}

# ---------- 4. Descarga (solo lectura sobre el servidor) y verificacion de cada archivo
function Test-GzipFile([string]$path) {
    # Lee el archivo entero a traves del descompresor: falla si esta cortado o corrupto.
    $fs = [System.IO.File]::OpenRead($path)
    try {
        $gz = New-Object System.IO.Compression.GZipStream($fs, [System.IO.Compression.CompressionMode]::Decompress)
        $buf = New-Object byte[] 65536
        $total = 0
        while (($n = $gz.Read($buf, 0, $buf.Length)) -gt 0) { $total += $n }
        return ($total -gt 0)
    } catch { return $false } finally { $fs.Dispose() }
}

$bad = 0; $ok = 0; $new = 0
foreach ($kind in 'daily', 'weekly') {
    $dir = Join-Path $Destination $kind
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $before = @(Get-ChildItem -LiteralPath $dir -Filter 'db-*.sql.gz' -ErrorAction SilentlyContinue | ForEach-Object Name)

    Write-Host "==> $kind"
    # El glob lo expande el shell del servidor. Si weekly/ esta vacio (lunes a sabado) scp falla: no es un error del backup.
    & $scp @sshOpts "${User}@${HostName}:${RemoteDir}/$kind/db-*.sql.gz" $dir
    if ($LASTEXITCODE -ne 0) {
        if ($kind -eq 'weekly') { Write-Host '    (sin copias semanales todavia, o no se pudo leer: se sigue)' -ForegroundColor Yellow; continue }
        Fail "scp fallo para $kind (codigo $LASTEXITCODE)"
    }

    foreach ($f in Get-ChildItem -LiteralPath $dir -Filter 'db-*.sql.gz') {
        if (Test-GzipFile $f.FullName) { $ok++ } else { $bad++; Write-Host "    CORRUPTO: $($f.Name)" -ForegroundColor Red }
        if ($before -notcontains $f.Name) { $new++ }
    }
}

Write-Host ''
Write-Host "Archivos verificados: $ok (nuevos en esta corrida: $new). Corruptos: $bad."
if ($bad -gt 0) { Fail 'hay archivos corruptos: NO los des por buenos; vuelve a correr el script' }
$latest = Get-ChildItem -LiteralPath $Destination -Recurse -Filter 'db-*.sql.gz' | Sort-Object Name -Descending | Select-Object -First 1
if ($latest) { Write-Host "El mas reciente: $($latest.FullName) ($($latest.Length) bytes)" }
