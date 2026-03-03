param(
    [string]$name = "aio-sandbox_run",
    [int]$p8080 = 9020,
    [int]$p30001 = 8081,
    [int]$p10086 = 8085,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$IMAGE_NAME = "aio-sandbox-image"

if ($Help) {
    Write-Host "Usage: .\deploy.ps1 [options]"
    exit 0
}

Write-Host "===========================" -ForegroundColor Cyan
Write-Host "1. Build Docker image..." 
Write-Host "===========================" -ForegroundColor Cyan
docker build -t $IMAGE_NAME .

Write-Host "===========================" -ForegroundColor Cyan
Write-Host "Run container with port mappings..." 
Write-Host "===========================" -ForegroundColor Cyan

$dockerArgs = @(
    "run", "-d",
    "--name", $name,
    "--security-opt", "seccomp=unconfined",
    "--shm-size=2gb",
    "--memory=8g",
    "--cpus=4",
    "--add-host=host.docker.internal:host-gateway",
    "-p", "$($p8080):8080",
    "-p", "$($p30001):30001",
    "-p", "$($p10086):10086",
    "-e", "XMODIFIERS=@im=fcitx" ,
    "-e", "QT_IM_MODULE=fcitx",
    "-e", "GTK_IM_MODULE=fcitx",
    $IMAGE_NAME
)
& docker $dockerArgs

Write-Host "Waiting for container init (5s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "===========================" -ForegroundColor Cyan
Write-Host "2. Copy and execute 1.sh (as root)..." 
Write-Host "===========================" -ForegroundColor Cyan
docker cp 1.sh "$($name):/home/gem/1.sh"
docker exec -u root $name chown gem:gem /home/gem/1.sh
docker exec -u gem $name bash /home/gem/1.sh

Write-Host "===========================" -ForegroundColor Cyan
Write-Host "3. Force copy all files from src into container..."
Write-Host "===========================" -ForegroundColor Cyan
docker cp src/. "$($name):/home/gem/"
docker exec -u root $name chown -R gem:gem /home/gem/

Write-Host "===========================" -ForegroundColor Cyan
Write-Host "4. Start Backend & Frontend services (Parallel)..." 
Write-Host "===========================" -ForegroundColor Cyan
Write-Host "Launching run.sh inside the container (waiting for completion)..." -ForegroundColor Yellow
# 核心变化：取消 -d 参数，使用交互式或普通模式等待 run.sh 的就绪逻辑完成
docker exec -u gem $name bash /home/gem/run.sh

Write-Host "===========================" -ForegroundColor Green
Write-Host "🎉 SUCCESS! All services are running and ready." 
Write-Host "Container Name: $name" 
Write-Host "MOMA UI: http://localhost:$p8080"
Write-Host "Next.js Frontend: http://localhost:$p30001"
Write-Host "===========================" -ForegroundColor Green
