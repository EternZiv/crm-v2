$scriptsDirectory = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..\venv\Scripts")
)
$scriptsPrefix = $scriptsDirectory.TrimEnd("\") + "\"

Get-CimInstance Win32_Process |
    Where-Object {
        $_.ExecutablePath -and
        $_.ExecutablePath.StartsWith(
            $scriptsPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
    }
