param(
    [string]$Username,
    [string]$Password
)

Add-Type -AssemblyName System.Windows.Forms

$designer = Get-Process | Where-Object {$_.MainWindowTitle -eq 'Login - Ignition'} | Select-Object -First 1

if ($designer) {
    # Bring to foreground and ensure focus
    Add-Type -TypeDefinition @'
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    }
'@

    # Restore window if minimized and bring to front
    [Win32]::ShowWindow($designer.MainWindowHandle, 9)  # SW_RESTORE
    Start-Sleep -Milliseconds 500  # Increased from 200ms for more reliable window restoration
    [Win32]::SetForegroundWindow($designer.MainWindowHandle)
    Start-Sleep -Milliseconds 300  # Increased from 200ms
    [Win32]::SetForegroundWindow($designer.MainWindowHandle)  # Call twice to ensure focus
    Start-Sleep -Milliseconds 300  # Increased from 200ms
    [Win32]::SetForegroundWindow($designer.MainWindowHandle)  # Third call for stubborn cases
    Start-Sleep -Milliseconds 800  # Longer wait for window to be fully ready (total: 1900ms)

    # Enter username (field should already have focus when window opens)
    [System.Windows.Forms.SendKeys]::SendWait($Username)
    Start-Sleep -Milliseconds 100

    # Tab to password
    [System.Windows.Forms.SendKeys]::SendWait('{TAB}')
    Start-Sleep -Milliseconds 100

    # Enter password
    [System.Windows.Forms.SendKeys]::SendWait($Password)
    Start-Sleep -Milliseconds 100

    # Submit
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')

    Write-Output 'success'
} else {
    Write-Output 'failed - window not found'
}
