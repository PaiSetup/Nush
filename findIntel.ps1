# Find Intel driver path
$vendorsRegistryAddress="HKEY_LOCAL_MACHINE\SOFTWARE\Khronos\OpenCL\Vendors"
echo "Looking for Intel OpenCL path in $vendorsRegistryAddress..."
$intelOpenclPath = Get-Item -Path Registry::$vendorsRegistryAddress |
    Select-Object -ExpandProperty Property                          |
    Select-String -Pattern "IntelOpenCL64\.dll$"                    |
    %{$_.Line}
if (!$intelOpenclPath) {
    echo "Intel OpenCL not installed!"
}
if (![System.IO.File]::Exists($intelOpenclPath)) {
    echo "Found reference to $intelOpenclPath in registry, but it does not exist"
}
$intelDriverDirectory = [System.IO.Path]::GetDirectoryName($intelOpenclPath)
echo "Found Intel graphics driver in $intelDriverDirectory"
