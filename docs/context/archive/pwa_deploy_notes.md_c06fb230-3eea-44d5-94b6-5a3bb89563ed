# Curator PWA Desktop Installer — Deployment Notes

## Current State (Dev)

A `.desktop` file launches Curator in an isolated Chrome app-mode window with no extensions, using a dedicated profile directory. Works for single-user dev on LMDE with Chrome installed at `/opt/google/chrome/google-chrome` and Curator running on `localhost:8080`.

The install script:

```bash
#!/bin/bash
cat > ~/.local/share/applications/curator.desktop << EOF
[Desktop Entry]
Version=1.0
Terminal=false
Type=Application
Name=Curator — Navigate the Project Crew
Exec=/opt/google/chrome/google-chrome --app=http://localhost:8080 --user-data-dir=/home/$USER/.config/curator-pwa-profile --disable-extensions --no-default-browser-check --no-first-run
Icon=chrome-cpdpbfelifklonephgpieimdpcecgoen-Default
StartupWMClass=crx_cpdpbfelifklonephgpieimdpcecgoen
EOF

mkdir -p /home/$USER/.config/curator-pwa-profile
chmod +x ~/.local/share/applications/curator.desktop
echo "Curator shortcut installed."
```

---

## Before Public Deployment — Things to Resolve

### 1. Chrome path varies by distro/install method
- `/opt/google/chrome/google-chrome` — Chrome via .deb on Debian/Ubuntu/LMDE
- `google-chrome` or `google-chrome-stable` — may be on PATH
- `chromium` or `chromium-browser` — Chromium (open source build)

The install script should detect which browser is available, or ask the user, rather than hardcoding the path.

### 2. Icon
The current `Icon=` value (`chrome-cpdpbfelifklonephgpieimdpcecgoen-Default`) was auto-generated when the PWA was installed in Carolyn's Default Chrome profile. It won't exist for other users.

Fix: bundle a proper Curator icon (PNG, ideally 512×512) with the installer and reference it by absolute path, e.g.:
```ini
Icon=/opt/curator/curator-icon.png
```

### 3. Port
Currently hardcoded to port 8080. If Curator moves to a different port, the installer needs to know. Consider:
- A config file or environment variable the installer reads
- Or a prompt during install

### 4. Real PWA (Option B)
For a proper installable PWA experience (OS-level app entry, offline capability, install prompt in browser), Curator needs:
- A `manifest.json` served as a static file
- A `<link rel="manifest">` in `base.html`
- Icons in multiple sizes (192×192, 512×512 minimum)
- Optionally a service worker for offline support

This is a Curator code change, scoped as its own changedoc when deployment prep begins.

### 5. Multi-browser support
The current approach is Chrome-only. For deployment to users on Firefox or other browsers, either:
- Detect the browser and generate the appropriate launch command
- Or implement Option B (real PWA manifest) which gives Firefox and other browsers a native install path

### 6. Install page — generated `.desktop` file
Add a FastAPI route (Captain-gated) that renders an install page showing the correct `.desktop` file content in a code block, pre-filled with the configured port. User copies it, pastes it into `~/.local/share/applications/curator.desktop`, and runs `chmod +x` on it. Not elegant but requires no server-side filesystem writes, no permissions complexity, and works for any user on any machine. Good fallback for tech-comfortable users until a proper installer exists.

### 7. `start.sh` integration
The desktop shortcut currently assumes Curator is already running. Eventually the `Exec=` line should call a wrapper script that:
1. Starts Curator (`start.sh` or equivalent)
2. Waits for it to be ready (poll `localhost` or use a health check endpoint)
3. Then launches the Chrome app window

```bash
#!/bin/bash
/path/to/start.sh &
# wait for Curator to be ready
until curl -s http://localhost:8080 > /dev/null; do sleep 0.5; done
exec /opt/google/chrome/google-chrome --app=http://localhost:8080 \
  --user-data-dir=/home/$USER/.config/curator-pwa-profile \
  --disable-extensions --no-default-browser-check --no-first-run
```
