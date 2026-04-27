# Phase 1 report — Project Solleclaire
Session handoff — completed April 2026

---

## Hardware

| | |
|---|---|
| AI machine | Steam Deck + official dock (SteamOS, KDE Plasma desktop mode) |
| Controller | Windows 11 laptop |
| Link | Direct ethernet cable — laptop ↔ dock ethernet port |

---

## Network

| | |
|---|---|
| Laptop IP | 192.168.50.1 |
| Steam Deck IP | 192.168.50.2 |
| Connection name | solleclaire-eth (nmcli) |
| Config type | Static — no router, direct link only |

---

## Users

### deck (default SteamOS user)
- Sudo: yes
- SSH auth: password required (key copy failed, left as-is)
- Desktop session: gaming mode autologin by default

### sol (project AI user)
- Sudo: none — intentional, limits AI blast radius
- SSH auth: passwordless — key at `C:\\Users\\weilo\\.ssh\\id_ed25519`
- Linger: enabled (`loginctl enable-linger sol`)
- Desktop session: KDE Plasma via user switch (see below)

---

## SSH access

```
ssh sol@192.168.50.2    # passwordless — use this for all project work
ssh deck@192.168.50.2   # password required — use only for sudo tasks
```

> If SSH starts rejecting the config file, run:
> `icacls %USERPROFILE%\.ssh\config /inheritance:r`
> `icacls %USERPROFILE%\.ssh\config /grant:r "%USERNAME%:F"`

---

## SSH config (C:\\Users\\weilo\\.ssh\\config)

```
Host deck-deck
    HostName 192.168.50.2
    User deck
    IdentityFile ~/.ssh/id_ed25519

Host deck-sol
    HostName 192.168.50.2
    User sol
    IdentityFile ~/.ssh/id_ed25519
```

---

## VS Code Remote SSH

Connect via Remote Explorer → `deck-sol`.

Required settings in `settings.json` to prevent connection hanging:

```json
"remote.SSH.useExecServer": false,
"remote.SSH.useLocalServer": true
```

> Without these settings VS Code hangs at "Install and start server if needed" indefinitely.

---

## User switching

SteamOS does not support concurrent desktop sessions. Switching users requires swapping the SDDM autologin config and rebooting.

| | |
|---|---|
| deck → sol | `~/Desktop/switch-to-sol.sh` |
| sol → deck | `~/Desktop/switch-to-deck.sh` |
| Config files | `/home/deck/steamos.conf.sol` and `steamos.conf.deck` |

Scripts copy the appropriate config to `/etc/sddm.conf.d/steamos.conf` then call `qdbus org.kde.Shutdown` to log out.

Sol's config uses `Session=plasma.desktop` — boots into KDE desktop mode directly, skipping gaming mode.

> **Warning:** Do NOT blank out or delete steamos.conf. Disabling autologin entirely prevents SDDM from showing a login screen, requiring a full OS reinstall to recover.

### Switch flow (one-time sol setup)
1. On deck's desktop, double-click `switch-to-sol.sh`
2. Deck reboots into sol's gaming mode (Steam first-time wizard runs once)
3. Complete Steam account setup for sol, then switch to desktop mode from Steam menu
4. Sol is now in KDE desktop mode — this is the AI working environment
5. To return: double-click `switch-to-deck.sh` on sol's desktop

---

## Phase 1 checklist

- [x] sshd running and enabled on Deck
- [x] Static IPs configured — 192.168.50.1 laptop, 192.168.50.2 Deck
- [x] ping 192.168.50.2 succeeds from laptop
- [x] Project user sol created with no sudo
- [x] loginctl enable-linger sol done
- [x] SSH key auth working for sol (passwordless)
- [x] VS Code Remote SSH connects to deck-sol
- [x] User switching working via desktop shortcut scripts
