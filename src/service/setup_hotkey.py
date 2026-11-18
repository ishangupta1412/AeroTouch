"""
AeroTouch Global Shortcut Registrar
Creates a native Windows system shortcut on Desktop and Start Menu with global hotkey Ctrl + Alt + A.
Requires zero background processes or CPU usage.
"""

import os
import subprocess


def register_global_hotkey(hotkey: str = "Ctrl+Alt+A") -> bool:
    ps_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $targets = @(
        "$env:USERPROFILE\\OneDrive\\Desktop\\AeroTouch.lnk",
        "$env:USERPROFILE\\Desktop\\AeroTouch.lnk",
        "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\AeroTouch.lnk"
    )

    foreach ($path in $targets) {{
        $dir = Split-Path $path
        if (Test-Path $dir) {{
            $Shortcut = $WshShell.CreateShortcut($path)
            $Shortcut.TargetPath = "$env:USERPROFILE\\OneDrive\\Desktop\\AeroTouch\\Start_AeroTouch.bat"
            $Shortcut.WorkingDirectory = "$env:USERPROFILE\\OneDrive\\Desktop\\AeroTouch"
            $Shortcut.Hotkey = "{hotkey}"
            $Shortcut.Description = "AeroTouch Spatial OS Hand Control"
            $Shortcut.IconLocation = "shell32.dll, 44"
            $Shortcut.Save()
            Write-Host "Registered Hotkey [{hotkey}] at: $path"
        }}
    }}
    """
    tmp_ps = os.path.join(os.path.dirname(__file__), "tmp_hotkey.ps1")
    with open(tmp_ps, "w", encoding="utf-8") as f:
        f.write(ps_script)

    res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", tmp_ps], capture_output=True, text=True)
    if os.path.exists(tmp_ps):
        os.remove(tmp_ps)

    print(res.stdout)
    return res.returncode == 0


if __name__ == "__main__":
    register_global_hotkey()
