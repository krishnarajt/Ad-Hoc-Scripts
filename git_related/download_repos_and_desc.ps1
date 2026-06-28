# GitHub Repo Fetcher
# Usage: .\get-repos.ps1 -Token "ghp_yourtoken"

param(
    [Parameter(Mandatory=$true)]
    [string]$Token,

    [string]$OutputFile = "repos.csv"
)

$headers = @{
    "Authorization" = "Bearer $Token"
    "Accept"        = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$allRepos = @()
$page = 1

Write-Host "Fetching repos..." -ForegroundColor Cyan

do {
    $url = "https://api.github.com/user/repos?per_page=100&page=$page&sort=updated"
    $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get

    if ($response.Count -eq 0) { break }

    $allRepos += $response
    Write-Host "  Page $page - $($response.Count) repos fetched"
    $page++

} while ($response.Count -eq 100)

Write-Host ""
Write-Host "Total repos found: $($allRepos.Count)" -ForegroundColor Green

$repoData = $allRepos | Select-Object `
    @{Name="Name";        Expression={$_.name}},
    @{Name="Description"; Expression={if ($_.description) {$_.description} else {"(no description)"}}},
    @{Name="Private";     Expression={$_.private}},
    @{Name="Language";    Expression={$_.language}},
    @{Name="Stars";       Expression={$_.stargazers_count}},
    @{Name="URL";         Expression={$_.html_url}},
    @{Name="UpdatedAt";   Expression={$_.updated_at}}

$repoData | Format-Table -AutoSize

$repoData | Export-Csv -Path $OutputFile -NoTypeInformation -Encoding UTF8
Write-Host ""
Write-Host "Saved to $OutputFile" -ForegroundColor Green