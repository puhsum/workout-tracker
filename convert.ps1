param()

function CleanExerciseName($name) {
    $name = $name.Trim()
    # Simple case-insensitive replacement
    if ($name -match '^(Bb|bb|Bb|BB)(.*)$') {
        $name = 'Barbell' + $matches[2]
    }
    if ($name -match '^(Db|db|DB|Db)(.*)$') {
        $name = 'Dumbbell' + $matches[2]
    }
    # Try replacing within the string
    $name = $name -replace '(\s|^)(Bb|bb|BB)(\s|$)', '$1Barbell$3'
    $name = $name -replace '(\s|^)(Db|db|DB)(\s|$)', '$1Dumbbell$3'
    
    $words = $name -split '\s+'
    $titleCased = @()
    foreach ($word in $words) {
        if ($word) {
            $titleCased += (Get-Culture).TextInfo.ToTitleCase($word.ToLower())
        }
    }
    return $titleCased -join ' '
}

function ParseSets($setPart) {
    $setsList = @()
    if ($setPart -like '*(*)*') {
        $entries = $setPart -split ','
        foreach ($entry in $entries) {
            $entry = $entry.Trim()
            if ($entry -match '^(\d+\.?\d*)\s*kg?\s*\((\d+)\)') {
                $weight = $matches[1]
                $reps = $matches[2]
                $setsList += "$weight($reps)"
            }
        }
    } elseif ($setPart -like '*x*') {
        $entries = $setPart -split ','
        foreach ($entry in $entries) {
            $entry = $entry.Trim()
            if ($entry -match '^(\d+\.?\d*)\s*kg?\s+(\d+)\s*x\s*(\d+)') {
                $weight = $matches[1]
                $numSets = [int]$matches[2]
                $reps = $matches[3]
                for ($i = 0; $i -lt $numSets; $i++) {
                    $setsList += "$weight($reps)"
                }
            }
        }
    }
    if ($setsList.Count -eq 0) {
        return "$setPart # TODO: check format"
    }
    return $setsList -join ', '
}

function ParseExercise($line) {
    $line = $line.Trim()
    # Remove markdown bold markers
    $line = $line -replace '^\*\*', ''
    $line = $line -replace '\*\*$', ''
    $line = $line.Trim()
    
    if ($line -match '^(.+?)\s+(\d+\.?\d*)\s*(min|mins|sec|secs)(.*)$') {
        $name = $matches[1].Trim()
        $duration = $matches[2]
        $unit = $matches[3].ToLower()
        $name = CleanExerciseName $name
        if ($unit -in 'min', 'mins') {
            return @{ name = $name; sets = "duration: ${duration}min" }
        } else {
            return @{ name = $name; sets = "duration: ${duration}${unit}" }
        }
    }
    $match = [regex]::Match($line, '(\d+\.?\d*\s*(?:kg|x|\(|\d))')
    if (-not $match.Success) {
        $name = CleanExerciseName $line
        return @{ name = $name; sets = '(?) # TODO: check format' }
    }
    $exerciseName = $line.Substring(0, $match.Index).Trim()
    $setPart = $line.Substring($match.Index).Trim()
    # Remove trailing ** from setPart if present
    $setPart = $setPart -replace '\*\*$', ''
    $setPart = $setPart.Trim()
    
    $exerciseName = CleanExerciseName $exerciseName
    $sets = ParseSets $setPart
    return @{ name = $exerciseName; sets = $sets }
}

$sourceDir = 'c:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\Notion\workout-tracker'
$outputDir = 'c:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\workout-converted'

if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$files = Get-ChildItem -Path $sourceDir -Filter '*.md' | Sort-Object Name
$total = $files.Count
$count = 0

Write-Host "Found $total markdown files to convert"

foreach ($file in $files) {
    $count++
    try {
        $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
        $fmMatch = [regex]::Match($content, '^---\n(.*?)\n---\n(.*)$', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        
        if (-not $fmMatch.Success) {
            Write-Host "[$count/$total] SKIP: $($file.Name)"
            continue
        }
        
        $fmText = $fmMatch.Groups[1].Value
        $body = $fmMatch.Groups[2].Value
        
        $fm = @{}
        foreach ($line in $fmText -split "`n") {
            $line = $line.Trim()
            if ($line -and $line -notlike '-*' -and $line -like '*:*') {
                $parts = $line -split ':', 2
                $key = $parts[0].Trim()
                $value = if ($parts.Count -gt 1) { $parts[1].Trim() } else { '' }
                $fm[$key] = $value
            }
        }
        
        $createdTime = [DateTime]::MinValue
        $lastEditedTime = [DateTime]::MinValue
        
        if ($fm['Created time']) {
            try { $createdTime = [DateTime]::Parse($fm['Created time']) } catch {}
        }
        if ($fm['Last edited time']) {
            try { $lastEditedTime = [DateTime]::Parse($fm['Last edited time']) } catch {}
        }
        
        $dateStr = $fm['Date']
        $done = $fm['Done'] -eq 'true'
        
        $createdStr = if ($createdTime -ne [DateTime]::MinValue) { $createdTime.ToString('yyyy-MM-dd HH:mm') } else { '' }
        $logInStr = if ($createdTime -ne [DateTime]::MinValue) { $createdTime.ToString('HH:mm') } else { '' }
        $logOutStr = if ($lastEditedTime -ne [DateTime]::MinValue) { $lastEditedTime.ToString('HH:mm') } else { '' }
        
        $durationStr = ''
        if ($createdTime -ne [DateTime]::MinValue -and $lastEditedTime -ne [DateTime]::MinValue) {
            $duration = [int](($lastEditedTime - $createdTime).TotalMinutes)
            $durationStr = $duration.ToString()
        }
        
        $exercises = @()
        $noteLines = @()
        
        foreach ($line in $body -split "`n") {
            $trimmed = $line.Trim()
            if (-not $trimmed) { continue }
            
            if ($trimmed -match '\d+\s*(?:x|kg|\(|\)|min)' -or $trimmed -match '(?:min|mins|sec|secs)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase) {
                $ex = ParseExercise $trimmed
                if ($ex) {
                    $exercises += $ex
                }
            } else {
                $noteLines += $trimmed
            }
        }
        
        $outputFM = "created: $createdStr`ndate: $dateStr`nlog-in: $logInStr`nlog-out: $logOutStr`nduration: $durationStr`ntags:`n  - project/workout`n  - status/$( if ($done) { 'done' } else { 'not-started' } )`n"
        
        if ($exercises.Count -gt 0) {
            $outputFM += "exercises:`n"
            foreach ($ex in $exercises) {
                $outputFM += "  - name: $($ex.name)`n    sets: $($ex.sets)`n"
            }
        }
        
        $outputContent = "---`n$outputFM---`n`n## Notes`n`n"
        if ($noteLines.Count -gt 0) {
            $outputContent += ($noteLines -join "`n") + "`n"
        } else {
            $outputContent += "<!-- No notes imported from Notion -->`n"
        }
        
        $outputFile = Join-Path $outputDir $file.Name
        Set-Content -Path $outputFile -Value $outputContent -Encoding UTF8 -NoNewline
        
        if ($count % 50 -eq 0 -or $count -eq 1) {
            Write-Host "[$count/$total] Converted: $($file.Name)"
        }
    } catch {
        Write-Host "[$count/$total] ERROR: $($file.Name) - $_"
    }
}

Write-Host "`n[$total/$total] Conversion complete!"
