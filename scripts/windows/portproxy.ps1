# portproxy.ps1 - Reenvía el puerto 8000 de Windows a la IP interna de WSL2.
# La IP de WSL cambia en cada reinicio, por eso se recalcula en cada arranque.
#
# Instalacion (PowerShell admin, una vez):
#   schtasks /create /tn "Tesorería portproxy" /tr "powershell -ExecutionPolicy Bypass -File C:\Scripts\portproxy.ps1" /sc onstart /ru SYSTEM /rl highest
#
# Requiere que WSL2 ya este iniciado (el servicio "LxssManager" arranca con el sistema).

param(
    [int]$Puerto = 8000
)

$wslIp = (wsl hostname -I).Trim()
if (-not $wslIp) {
    Write-Host "No se pudo obtener la IP de WSL2. Verifique que WSL este funcionando." -ForegroundColor Red
    exit 1
}
# wsl hostname -I devuelve todas las IPs; tomamos la primera
$wslIp = ($wslIp -split " ")[0]

# Quitar regla previa (si existe) y crear la nueva
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$Puerto 2>$null | Out-Null
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$Puerto connectaddress=$wslIp connectport=$Puerto

# Asegurar que el firewall permita el puerto (idempotente)
netsh advfirewall firewall delete rule name="Tesorería $Puerto" protocol=TCP localport=$Puerto 2>$null | Out-Null
netsh advfirewall firewall add rule name="Tesorería $Puerto" dir=in action=allow protocol=TCP localport=$Puerto | Out-Null

Write-Host "Portproxy: 0.0.0.0:$Puerto -> $wslIp`:$Puerto (listo)" -ForegroundColor Green