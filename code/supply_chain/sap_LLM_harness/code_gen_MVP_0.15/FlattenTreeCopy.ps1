[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string]$SourceDir,
    
    [Parameter(Mandatory=$true)]
    [string]$DestDir
)

# Function to write formatted log messages
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Level] $Message"
}

# Function to convert a path to a flattened filename
function Convert-PathToFlattenedName {
    param(
        [string]$FilePath,
        [string]$BaseSourcePath
    )
    
    # Get the relative path by removing the base source path
    $relativePath = $FilePath.Substring($BaseSourcePath.Length).TrimStart('\')
    
    # Replace directory separators with underscores
    $flattenedName = $relativePath.Replace('\', '_')
    
    return $flattenedName
}

# Function to generate mapping documentation
function Write-MappingDocument {
    param(
        [hashtable]$Mappings,
        [string]$DestDir
    )
    
    $mappingPath = Join-Path $DestDir "mapping.md"
    
    # Create the markdown content
    $markdown = @"
# File Mapping Documentation
Generated on: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

This document maps the original file paths to their flattened equivalents.

| Original Path | Flattened Name |
|--------------|----------------|
"@

    # Add each mapping to the markdown content
    foreach ($mapping in $Mappings.GetEnumerator() | Sort-Object Key) {
        $markdown += "`n| $($mapping.Key) | $($mapping.Value) |"
    }

    # Write the markdown file
    $markdown | Out-File -FilePath $mappingPath -Encoding UTF8
    Write-Log "Generated mapping documentation at: $mappingPath"
}

# Main script execution starts here
try {
    Write-Log "Script started"
    Write-Log "Source Directory: $SourceDir"
    Write-Log "Destination Directory: $DestDir"

    # Create a hashtable to store the mappings
    $fileMappings = @{}

    # Validate source directory exists
    if (-not (Test-Path -Path $SourceDir -PathType Container)) {
        throw "Source directory does not exist: $SourceDir"
    }

    # Create destination directory if it doesn't exist
    if (-not (Test-Path -Path $DestDir -PathType Container)) {
        Write-Log "Creating destination directory: $DestDir" "INFO"
        New-Item -Path $DestDir -ItemType Directory | Out-Null
    }

    # Get the full path for both directories
    $sourceFullPath = (Resolve-Path $SourceDir).Path
    $destFullPath = (Resolve-Path $DestDir).Path

    Write-Log "Resolved Source Path: $sourceFullPath"
    Write-Log "Resolved Destination Path: $destFullPath"

    # Get all files from source directory and subdirectories
    $files = Get-ChildItem -Path $sourceFullPath -Recurse -File

    Write-Log "Found $($files.Count) files to process"

    foreach ($file in $files) {
        try {
            # Generate the flattened filename
            $flattenedName = Convert-PathToFlattenedName -FilePath $file.FullName -BaseSourcePath $sourceFullPath
            $destPath = Join-Path $destFullPath $flattenedName

            Write-Log "Processing: $($file.FullName)"
            Write-Log "Destination: $destPath"

            # Copy the file to destination
            Copy-Item -Path $file.FullName -Destination $destPath -Force

            # Store the mapping using relative paths
            $relativeSourcePath = $file.FullName.Substring($sourceFullPath.Length).TrimStart('\')
            $fileMappings[$relativeSourcePath] = $flattenedName

            Write-Log "Successfully copied file" "INFO"
        }
        catch {
            Write-Log "Failed to process file: $($file.FullName)" "ERROR"
            Write-Log "Error: $_" "ERROR"
        }
    }

    # Generate the mapping documentation
    Write-Log "Generating mapping documentation"
    Write-MappingDocument -Mappings $fileMappings -DestDir $destFullPath

    Write-Log "Script completed successfully"
}
catch {
    Write-Log "Script failed with error: $_" "ERROR"
    throw $_
}