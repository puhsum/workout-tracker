$sourceDir = "c:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\Notion\workout-tracker"
$outputDir = "c:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\workout-converted"

Get-ChildItem -Path $sourceDir -Filter "*.md" | ForEach-Object {
    Write-Host "Processing: $($_.Name)"
    $content = Get-Content -Path $_.FullName -Raw -Encoding UTF8
    
    # Simple placeholder - just copy for now to test
    Set-Content -Path "$outputDir\$($_.Name)" -Value $content -Encoding UTF8
}

Write-Host "Test conversion complete"
