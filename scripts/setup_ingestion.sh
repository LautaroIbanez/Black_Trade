#!/bin/bash
# Script to set up data ingestion pipeline
# This script initializes historical data and verifies the setup

set -e  # Exit on error

echo "======================================================================"
echo "Black Trade - Data Ingestion Setup"
echo "======================================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Verify database connection
echo -e "${YELLOW}Step 1: Verifying database connection...${NC}"
python -c "
from backend.db.session import engine
try:
    conn = engine.connect()
    conn.close()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
" || exit 1

# Step 2: Check if bootstrap should be run
echo -e "\n${YELLOW}Step 2: Checking existing data...${NC}"
python -c "
from backend.ingestion.bootstrap import DataBootstrap
import os

bootstrap = DataBootstrap()
symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0]
timeframes = os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')

report = bootstrap.verify_data(symbol, timeframes)

if report['overall_status'] == 'ok':
    print('✓ Data already available and fresh')
    exit(0)
else:
    print('⚠ Data missing or incomplete, bootstrap required')
    exit(1)
"

NEEDS_BOOTSTRAP=$?

# Step 3: Run bootstrap if needed
if [ $NEEDS_BOOTSTRAP -ne 0 ]; then
    echo -e "\n${YELLOW}Step 3: Running historical data bootstrap...${NC}"
    echo "This may take several minutes depending on the amount of data needed..."
    
    python -m backend.ingestion.bootstrap --verify || {
        echo -e "${RED}✗ Bootstrap failed${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✓ Bootstrap completed${NC}"
else
    echo -e "\n${GREEN}Step 3: Skipping bootstrap (data already available)${NC}"
fi

# Step 4: Final verification
echo -e "\n${YELLOW}Step 4: Final verification...${NC}"
python -c "
from backend.ingestion.bootstrap import DataBootstrap
import os
import sys

bootstrap = DataBootstrap()
symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0]
timeframes = os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')

report = bootstrap.verify_data(symbol, timeframes)

print(f'\nVerification for {symbol}:')
print(f'Overall status: {report[\"overall_status\"]}')
print()

all_ok = True
for tf, data in report['timeframes'].items():
    status = data.get('status', 'unknown')
    count = data.get('count', 0)
    issues = data.get('issues', [])
    
    if status == 'ok':
        print(f'  ✓ {tf}: {status} ({count} candles)')
    else:
        print(f'  ✗ {tf}: {status} ({count} candles)')
        all_ok = False
        for issue in issues:
            print(f'    ⚠ {issue}')

if not all_ok:
    print('\n⚠ Some timeframes have issues. Review above.')
    sys.exit(1)
else:
    print('\n✓ All timeframes verified successfully')
    sys.exit(0)
" || {
    echo -e "${RED}✗ Verification failed${NC}"
    exit 1
}

# Step 5: Summary
echo -e "\n${GREEN}======================================================================"
echo "Setup Complete!"
echo "======================================================================"
echo -e "${NC}"
echo "Next steps:"
echo "1. Start the backend: python -m uvicorn backend.app:app --reload"
echo "2. The ingestion pipeline will start automatically"
echo "3. Monitor ingestion status: GET /api/ingestion/status"
echo "4. Verify data: GET /api/ingestion/verify"
echo ""
echo "For more information, see: docs/ingestion_setup.md"

