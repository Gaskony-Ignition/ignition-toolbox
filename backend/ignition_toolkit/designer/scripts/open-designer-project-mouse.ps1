param(
    [string]$ProjectName
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$designer = Get-Process | Where-Object {$_.MainWindowTitle -like '*Open/Create Project*'} | Select-Object -First 1

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
        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        [StructLayout(LayoutKind.Sequential)]
        public struct RECT {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }
    }
'@

    # Restore and bring to front
    [Win32]::ShowWindow($designer.MainWindowHandle, 9)
    Start-Sleep -Milliseconds 200
    [Win32]::SetForegroundWindow($designer.MainWindowHandle)
    Start-Sleep -Milliseconds 200
    [Win32]::SetForegroundWindow($designer.MainWindowHandle)
    Start-Sleep -Milliseconds 300

    # Get window position
    $rect = New-Object Win32+RECT
    [Win32]::GetWindowRect($designer.MainWindowHandle, [ref]$rect)

    $windowWidth = $rect.Right - $rect.Left
    $windowHeight = $rect.Bottom - $rect.Top

    # Click in search box (approximately 50% across, 20% down from top)
    $searchX = $rect.Left + ($windowWidth * 0.5)
    $searchY = $rect.Top + ($windowHeight * 0.2)
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($searchX, $searchY)
    Start-Sleep -Milliseconds 100

    # Click
    Add-Type @'
    using System;
    using System.Runtime.InteropServices;
    public class MouseClick {
        [DllImport("user32.dll")]
        public static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);
        public const int MOUSEEVENTF_LEFTDOWN = 0x02;
        public const int MOUSEEVENTF_LEFTUP = 0x04;
    }
'@

    [MouseClick]::mouse_event([MouseClick]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 50
    [MouseClick]::mouse_event([MouseClick]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 150

    # Clear and type project name
    [System.Windows.Forms.SendKeys]::SendWait('^a')
    Start-Sleep -Milliseconds 50
    [System.Windows.Forms.SendKeys]::SendWait($ProjectName)
    Start-Sleep -Milliseconds 200

    # Double-click on the project row (approximately 20% across, 32% down - on the project name)
    $projectRowX = $rect.Left + ($windowWidth * 0.20)
    $projectRowY = $rect.Top + ($windowHeight * 0.32)
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($projectRowX, $projectRowY)
    Start-Sleep -Milliseconds 150

    # Double-click to open project
    [MouseClick]::mouse_event([MouseClick]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 50
    [MouseClick]::mouse_event([MouseClick]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 100
    [MouseClick]::mouse_event([MouseClick]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 50
    [MouseClick]::mouse_event([MouseClick]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    Write-Output 'success'
} else {
    Write-Output 'failed - window not found'
}
