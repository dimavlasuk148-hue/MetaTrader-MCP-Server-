#!/bin/bash

# MetaTrader MCP Server + AI Trading Pipeline launcher
# Usage: ./run.sh [mcp|pipeline|both] [--login LOGIN] [--password PASSWORD] [--server SERVER]

set -e

MODE="${1:-pipeline}"
SYMBOL="${SYMBOL:-EURUSD}"
TIMEFRAME="${TIMEFRAME:-H1}"

# Parse arguments
while [[ $# -gt 1 ]]; do
    case $2 in
        --login)
            LOGIN="$3"
            shift 2
            ;;
        --password)
            PASSWORD="$3"
            shift 2
            ;;
        --server)
            SERVER="$3"
            shift 2
            ;;
        --symbol)
            SYMBOL="$3"
            shift 2
            ;;
        --timeframe)
            TIMEFRAME="$3"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Get credentials
LOGIN="${LOGIN:-${MT5_LOGIN}}"
PASSWORD="${PASSWORD:-${MT5_PASSWORD}}"
SERVER="${SERVER:-${MT5_SERVER}}"

if [ -z "$LOGIN" ]; then
    read -p "Enter MT5 Login: " LOGIN
fi

if [ -z "$PASSWORD" ]; then
    read -sp "Enter MT5 Password: " PASSWORD
    echo
fi

if [ -z "$SERVER" ]; then
    read -p "Enter MT5 Server (default: MetaQuotes-Demo): " SERVER
    SERVER="${SERVER:-MetaQuotes-Demo}"
fi

echo ""
echo "════════════════════════════════════════"
echo "MetaTrader AI Trading System Launcher"
echo "════════════════════════════════════════"
echo ""

# Run MCP Server
if [ "$MODE" = "mcp" ] || [ "$MODE" = "both" ]; then
    echo "Starting MCP Server..."
    echo "  Login: $LOGIN"
    echo "  Server: $SERVER"
    echo ""
    
    if [ "$MODE" = "both" ]; then
        metatrader-mcp-server --login "$LOGIN" --password "$PASSWORD" --server "$SERVER" &
        sleep 2
    else
        exec metatrader-mcp-server --login "$LOGIN" --password "$PASSWORD" --server "$SERVER"
    fi
fi

# Run Trading Pipeline
if [ "$MODE" = "pipeline" ] || [ "$MODE" = "both" ]; then
    echo "Starting AI Trading Pipeline..."
    echo "  Symbol: $SYMBOL"
    echo "  Timeframe: $TIMEFRAME"
    echo "  Config: config/pipeline.yaml"
    echo ""
    
    if [ ! -f config/pipeline.yaml ]; then
        echo "ERROR: config/pipeline.yaml not found!"
        echo "Create it first using QUICKSTART.md"
        exit 1
    fi
    
    python -m trading_ai_pipeline.pipeline.runner \
        --config config/pipeline.yaml \
        --symbol "$SYMBOL" \
        --timeframe "$TIMEFRAME"
fi
