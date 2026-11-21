# subliminal download -l en The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4 is what downloads the subtitle
# Navigate to the base folder before running this script

# Define the subtitle language
$language = "en"

# Get all video files in subdirectories
$videoFiles = Get-ChildItem -Path . -Recurse -File | Where-Object { $_.Extension -match "\.mp4|\.mkv|\.avi|\.mov|\.wmv" }

foreach ($video in $videoFiles) {
    # Construct the command to download subtitles
    $command = "subliminal download -l $language `"$($video.FullName)`""

    # Run the command
    Write-Host "Downloading subtitles for: $($video.FullName)"
    Invoke-Expression $command
}
