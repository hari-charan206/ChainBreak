$log = ".freebuff/preview-4892b949-e66b-40f0-9ada-6a7f20b88acf.log"
$err = ".freebuff/preview-4892b949-e66b-40f0-9ada-6a7f20b88acf.err"
Set-Location backend
$p = Start-Process python.exe -ArgumentList "-m","uvicorn","app.main:app","--port","8089" `
  -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden -PassThru
Write-Output $p.Id
Start-Sleep 6
try {
  $g = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
} catch {
  $g = $null
}
if ($g) {
  Write-Output "ALIVE:" $g.Id $g.ProcessName $g.StartTime
} else {
  Write-Output "DEAD"
}
