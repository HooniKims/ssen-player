$ErrorActionPreference='Stop'
[Console]::InputEncoding=New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Security
$req=[Console]::In.ReadToEnd() | ConvertFrom-Json
$path=Join-Path $env:LOCALAPPDATA 'SsenSeries\Auth\v4.bin'
$entropy=[Text.Encoding]::UTF8.GetBytes('SsenSeries.Auth.v4')
$mutex=New-Object System.Threading.Mutex($false,'Local\SsenSeriesAuthV4')
$held=$false
$storeStage='lock'
try {
 try {$held=$mutex.WaitOne(10000)} catch [System.Threading.AbandonedMutexException] {$held=$true}
 if(!$held){throw 'STORE_BUSY'}
 $revision=0L;$state=$null
 if([IO.File]::Exists($path)){
  try {
   $storeStage='decrypt'
   $raw=[Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($path),$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
   $storeStage='decode'
   $data=[Text.Encoding]::UTF8.GetString($raw) | ConvertFrom-Json
   if($null -eq $data.revision -or $data.state -isnot [System.Management.Automation.PSCustomObject] -or $data.revision -lt 0 -or [math]::Truncate($data.revision) -ne $data.revision){throw 'invalid'}
   $revision=[long]$data.revision;$state=$data.state
  } catch {throw 'STORE_CORRUPT'}
 }
 if($req.op -eq 'read'){$result=@{revision=$revision;state=$state}}
 elseif($req.op -eq 'write'){
  if($null -eq $req.revision -or [long]$req.revision -ne $revision){throw 'STORE_CONFLICT'}
  if($req.state -isnot [System.Management.Automation.PSCustomObject]){throw 'STORE_CORRUPT'}
  $storeStage='encode'
  $json=@{revision=($revision+1);state=$req.state}|ConvertTo-Json -Depth 100 -Compress
  $storeStage='encrypt'
  $bytes=[Security.Cryptography.ProtectedData]::Protect([Text.Encoding]::UTF8.GetBytes($json),$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
  $storeStage='directory'
  [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path))|Out-Null
  $temp=$path+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
  try {$storeStage='temp-write';[IO.File]::WriteAllBytes($temp,$bytes);if([IO.File]::Exists($path)){ $storeStage='replace';[IO.File]::Replace($temp,$path,[System.Management.Automation.Language.NullString]::Value)}else{$storeStage='create';[IO.File]::Move($temp,$path)}}finally{if([IO.File]::Exists($temp)){[IO.File]::Delete($temp)}}
  $result=@{revision=($revision+1)}
 }else{throw 'BAD_OPERATION'}
 $result|ConvertTo-Json -Depth 100 -Compress
}catch{
 $cause=$_.Exception.GetBaseException().GetType().Name
 if($cause -notin @('UnauthorizedAccessException','IOException','CryptographicException','ArgumentException','InvalidOperationException')){$cause='Unclassified'}
 $code=$_.Exception.Message
 if($code -notin @('STORE_BUSY','STORE_CONFLICT','STORE_CORRUPT','BAD_OPERATION')){$code='STORE_ERROR'}
 @{bridgeError=$code;storeCause=$cause;storeStage=$storeStage}|ConvertTo-Json -Compress
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
