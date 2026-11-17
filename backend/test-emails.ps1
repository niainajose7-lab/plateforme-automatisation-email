$base = "http://127.0.0.1:8000"

$corps = '{"email":"niainajose7@gmail.com","mot_de_passe":"1234"}'
$r = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType "application/json" -Body $corps
if (-not $r.access_token) {
    Write-Host "Login echoue : le serveur tourne-t-il ?"
    return
}

$entete = @{ Authorization = "Bearer $($r.access_token)" }

$boites = Invoke-RestMethod -Uri "$base/emails/" -Headers $entete
$boites | Format-Table

$id = $boites[0].id
Invoke-RestMethod -Uri "$base/emails/$id" -Headers $entete | Format-List