$Market = "en-IN"
$OutputDir = "$PWD"

$ApiUrl = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=$Market"

Write-Host "Fetching metadata..."
$response = Invoke-RestMethod -Uri $ApiUrl -Method Get

$imgPath = $response.images[0].url
$baseUrl = "https://www.bing.com$imgPath"

# Extract filename from id parameter
if ($baseUrl -match "id=([^&]+)") {
    $originalFileName = $matches[1]
} else {
    throw "Could not extract filename."
}

# Build UHD filename correctly (replace resolution suffix)
$uhdFileName = $originalFileName -replace "_\d+x\d+\.jpg$", "_UHD.jpg"

$uhdUrl = $baseUrl -replace [regex]::Escape($originalFileName), $uhdFileName
$originalUrl = $baseUrl

function Test-ValidImage {
    param ($Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200 -and $response.RawContentLength -gt 100000) {
            return $true
        }
    } catch {
        return $false
    }

    return $false
}

Write-Host "Testing UHD URL..."
if (Test-ValidImage $uhdUrl) {
    Write-Host "UHD available. Downloading..."
    $finalUrl = $uhdUrl
    $finalFileName = $uhdFileName
} else {
    Write-Host "UHD not available. Falling back to 1080p."
    $finalUrl = $originalUrl
    $finalFileName = $originalFileName
}

$dest = Join-Path $OutputDir $finalFileName

Write-Host "Downloading from:"
Write-Host $finalUrl

Invoke-WebRequest -Uri $finalUrl -OutFile $dest -UseBasicParsing

$file = Get-Item $dest
Write-Host "Download complete."
Write-Host "File size: $($file.Length) bytes"

Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($dest)
Write-Host "Resolution: $($img.Width)x$($img.Height)"
$img.Dispose()