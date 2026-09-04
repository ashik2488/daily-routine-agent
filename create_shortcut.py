import os
import subprocess

vbs_path = r"C:\Users\USER\.gemini\antigravity\scratch\routine-agent\open_app.vbs"
ico_path = r"C:\Users\USER\.gemini\antigravity\scratch\routine-agent\app_icon.ico"
work_dir = r"C:\Users\USER\.gemini\antigravity\scratch\routine-agent"

desktop_dirs = [
    os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Desktop")
]

for d in desktop_dirs:
    if os.path.exists(d):
        lnk_path = os.path.join(d, "Daily Routine.lnk")
        ps = f"""
$sh = New-Object -ComObject WScript.Shell
$sc = $sh.CreateShortcut('{lnk_path}')
$sc.TargetPath = 'wscript.exe'
$sc.Arguments = '"{vbs_path}"'
$sc.WorkingDirectory = '{work_dir}'
$sc.IconLocation = '{ico_path}, 0'
$sc.Description = 'Daily Routine Agent'
$sc.Save()
"""
        with open("make_lnk.ps1", "w", encoding="utf-8") as f:
            f.write(ps)
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "make_lnk.ps1"], check=True)
        if os.path.exists("make_lnk.ps1"):
            os.remove("make_lnk.ps1")
        print(f"Created shortcut at: {lnk_path}")
