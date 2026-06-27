#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick launcher for MetaTrader MCP Server + AI Trading Pipeline

.DESCRIPTION
    Starts either the MCP server or AI trading pipeline with minimal configuration

.PARAMETER Mode
    'mcp' = MCP Server (for Claude Desktop/ChatGPT)
    'pipeline' = AI Trading Pipeline (automated trading)
    'both' = Start both in separate terminals

.PARAMETER Login
    MT5 login ID (default: read from .env)

.PARAMETER Password
    MT5 password (default: read from .env)

.PARAMETER Server
    MT5 server name (default: read from .env)

.PARAMETER Symbol
    Trading symbol for pipeline (default: EURUSD)

.PARAMETER Timeframe
    Timeframe for pipeline (default: H1)

.EXAMPLE
    .\run.ps1 -Mode mcp
    .\run.ps1 -Mode pipeline -Symbol GBPUSD
    .\run.ps1 -Mode both -Login 12345678 -Password mypass -Server demo

#>

param(
    [ValidateSet('mcp', 'pipeline', 'both')]
    [string]$Mode = 'pipeline',
    
    [string]$Login,
    [string]$Password,
    [string]$Server,
    
    [string]$Symbol = 'EURUSD',
    [string]$Timeframe = 'H1'
)

# Load .env if exists
if (Test-Path '.env') {
    $env_content = Get-Content '.env'
    foreach ($line in $env_content) {
        if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
        $key, $value = $line -split '=', 2
        [System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim())
    }
}

# Get credentials
if (-not $Login) {
    $Login = $env:MT5_LOGIN
    if (-not $Login) {
        $Login = Read-Host "Enter MT5 Login"
    }
}

if (-not $Password) {
    $Password = $env:MT5_PASSWORD
    if (-not $Password) {
        $Password = Read-Host "Enter MT5 Password" -AsSecureString
        $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($Password))
    }
}

if (-not $Server) {
    $Server = $env:MT5_SERVER
    if (-not $Server) {
        $Server = Read-Host "Enter MT5 Server (default: MetaQuotes-Demo)"
        if (-not $Server) { $Server = "MetaQuotes-Demo" }
    }
}

Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "MetaTrader AI Trading System Launcher" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Run MCP Server
if ($Mode -eq 'mcp' -or $Mode -eq 'both') {
    Write-Host "Starting MCP Server..." -ForegroundColor Green
    Write-Host "  Login: $Login" -ForegroundColor Gray
    Write-Host "  Server: $Server" -ForegroundColor Gray
    Write-Host ""
    
    if ($Mode -eq 'both') {
        # Start in background for 'both' mode
        Start-Process pwsh -ArgumentList @"-Command", "metatrader-mcp-server --login $Login --password '$Password' --server $Server"
        Write-Host "MCP Server started in new window" -ForegroundColor Green
        Start-Sleep -Seconds 2
    } else {
        # Run in foreground for 'mcp' mode
        & metatrader-mcp-server --login $Login --password $Password --server $Server
        exit
    }
}

# Run Trading Pipeline
if ($Mode -eq 'pipeline' -or $Mode -eq 'both') {
    Write-Host "Starting AI Trading Pipeline..." -ForegroundColor Green
    Write-Host "  Symbol: $Symbol" -ForegroundColor Gray
    Write-Host "  Timeframe: $Timeframe" -ForegroundColor Gray
    Write-Host "  Config: config/pipeline.yaml" -ForegroundColor Gray
    Write-Host ""
    
    # Verify config exists
    if (-not (Test-Path 'config/pipeline.yaml')) {
        Write-Host "ERROR: config/pipeline.yaml not found!" -ForegroundColor Red
        Write-Host "Create it first:" -ForegroundColor Yellow
        Write-Host "  Copy config/pipeline.yaml.example to config/pipeline.yaml" -ForegroundColor Yellow
        exit 1
    }
    
    # Run pipeline
    & python -m trading_ai_pipeline.pipeline.runner `
        --config config/pipeline.yaml `
        --symbol $Symbol `
        --timeframe $Timeframe
}
