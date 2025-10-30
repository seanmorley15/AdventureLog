# Test Bucket List Functionality
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing Bucket List Functionality" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if API is accessible
Write-Host "Test 1: Checking API accessibility..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8016/api/bucketlist/items/' -UseBasicParsing
    Write-Host "✓ API is accessible - Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "  Current items: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "✗ API error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 2: Check if frontend page loads
Write-Host "Test 2: Checking frontend page..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8015/bucketlist' -UseBasicParsing
    Write-Host "✓ Frontend page loads - Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "✗ Frontend error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 3: Check backend logs for errors
Write-Host "Test 3: Checking backend logs..." -ForegroundColor Yellow
docker compose logs server --tail 20 --since 5m
Write-Host ""

# Test 4: Check database tables
Write-Host "Test 4: Checking if bucket list tables exist..." -ForegroundColor Yellow
docker compose exec -T db psql -U postgres -d postgres -c "\dt bucketlist_*"
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Instructions for Manual Testing:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Open http://localhost:8015 in your browser" -ForegroundColor White
Write-Host "2. Log in with admin/admin (from .env file)" -ForegroundColor White
Write-Host "3. Navigate to Bucket List (Target icon in navbar)" -ForegroundColor White
Write-Host "4. Click 'Add Item' button" -ForegroundColor White
Write-Host "5. Fill in the form and submit" -ForegroundColor White
Write-Host "6. Check if the item appears in the list" -ForegroundColor White
Write-Host ""
Write-Host "If items don't appear, check browser console for errors (F12)" -ForegroundColor Yellow
