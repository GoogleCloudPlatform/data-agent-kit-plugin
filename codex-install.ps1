# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

param(
    [Parameter(Mandatory = $false)]
    [string]$Tag
)

if (-not $Tag -and $env:CODEX_TAG) {
    $Tag = $env:CODEX_TAG
}

$ErrorActionPreference = "Stop"

$pluginName = "data-agent-kit-starter-pack"
$repoUrl = "https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack"
$pluginsRoot = Join-Path $HOME ".agents\plugins"
$installDir = Join-Path $pluginsRoot $pluginName
$marketplaceFile = Join-Path $pluginsRoot "marketplace.json"

function Invoke-GitCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )

    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git $($Arguments -join ' ')"
    }
}

function Write-TextFileNoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,

        [Parameter(Mandatory = $true)]
        [string] $Content
    )

    if ($PSVersionTable.PSVersion.Major -ge 6) {
        $Content | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
        return
    }

    # Windows PowerShell 5.1 lacks utf8NoBOM. For this file we only emit ASCII JSON,
    # so ASCII preserves valid JSON bytes while avoiding a UTF-8 BOM.
    $Content | Set-Content -LiteralPath $Path -Encoding ascii
}

Write-Host "--- $pluginName Installer for Codex ---"

Write-Host "GCP Project ID"
$projectId = Read-Host "Project ID when using the MCP toolbox for databases"

Write-Host "GCP Region"
$gcpRegion = Read-Host "Region for GCP services (e.g. us-west1)"

Write-Host "BigQuery Location"
$bigqueryLocation = Read-Host "Location for BigQuery datasets (e.g. US)"

New-Item -ItemType Directory -Force -Path $pluginsRoot | Out-Null

if (Test-Path $installDir) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupName = "$pluginName" + "_backup_" + $timestamp
    $backupPath = Join-Path (Split-Path $installDir) $backupName
    Write-Host "Backing up existing plugin to $backupPath..."
    Rename-Item -LiteralPath $installDir -NewName $backupName
    Write-Host "Notice: Your previous installation has been backed up to $backupPath."
    Write-Host "You can delete it if you do not need it."
}

if ($Tag) {
    Write-Host "Cloning plugin version $Tag to $installDir..."
    Invoke-GitCommand -Arguments @("clone", "--depth", "1", "--branch", $Tag, $repoUrl, $installDir)
} else {
    Write-Host "Cloning plugin default branch to $installDir..."
    Invoke-GitCommand -Arguments @("clone", "--depth", "1", $repoUrl, $installDir)
}

Write-Host "Removing git metadata..."
Remove-Item -LiteralPath (Join-Path $installDir ".git") -Recurse -Force

$targetMcp = Join-Path $installDir "mcp.json"

# Apply configuration
Write-Host "Applying configuration..."
$mcpContent = Get-Content -LiteralPath $targetMcp -Raw
$mcpContent = $mcpContent.Replace('$PROJECT_ID', $projectId)
$mcpContent = $mcpContent.Replace('$GCP_REGION', $gcpRegion)
$mcpContent = $mcpContent.Replace('$BIGQUERY_LOCATION', $bigqueryLocation)
Write-TextFileNoBom -Path $targetMcp -Content $mcpContent

if (-not (Test-Path $marketplaceFile)) {
    Write-Host "Creating new personal marketplace..."
    Write-TextFileNoBom -Path $marketplaceFile -Content '{"name":"personal","plugins":[]}'
}

Write-Host "Registering plugin in $marketplaceFile..."
$pluginJson = @"
{
  "name": "$pluginName",
  "interface": {
    "displayName": "Data Agent Kit Starter Pack"
  },
  "source": {
    "source": "local",
    "path": "./.agents/plugins/$pluginName"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
"@

$marketplace = Get-Content -LiteralPath $marketplaceFile -Raw | ConvertFrom-Json
$newPlugin = $pluginJson | ConvertFrom-Json

if ($null -eq $marketplace.plugins) {
    $marketplace | Add-Member -MemberType NoteProperty -Name plugins -Value @()
} else {
    $marketplace.plugins = @($marketplace.plugins | Where-Object { $_.name -ne $pluginName })
}

$marketplace.plugins += $newPlugin
$marketplaceJson = $marketplace | ConvertTo-Json -Depth 10
$marketplaceJson = $marketplaceJson -replace '":\s+', '": '
Write-TextFileNoBom -Path $marketplaceFile -Content $marketplaceJson

Write-Host "Done! Restart Codex to use the $pluginName plugin."
