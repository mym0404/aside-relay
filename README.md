# aside-relay

Use [Aside](https://aside.dev) from your phone or browser. This self-hosted web app
connects to the Aside app and CLI on your computer — macOS or Windows — with live
conversations, browser previews, interactive HTML visuals, and completion
notifications.

**Cloudflare and Cloudflare Access are optional.** You can use localhost,
Tailscale, your own VPN, or an HTTPS address on your own domain. The bridge has
its own access-token login; no separate AI API key is required.

## Screenshots

Current app UI captured in a phone-sized browser with public sample conversations
and controlled API fixtures. These are browser screenshots, not design mockups.
Device status bars and browser address bars are omitted. Browser previews show a
public sample documentation page; connection and task states are fixture data.
Click any image to view it at full size.

<table>
  <tr>
    <th>Code and conversation</th>
    <th>Interactive HTML</th>
    <th>Visual source</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/code-response.jpg"><img src="docs/screenshots/code-response.jpg" width="240" alt="A TypeScript stream reader in compact D2Coding above the anchored composer"></a></td>
    <td><a href="docs/screenshots/visual-preview.jpg"><img src="docs/screenshots/visual-preview.jpg" width="240" alt="An HTML workflow after tapping Next step to highlight Browse"></a></td>
    <td><a href="docs/screenshots/visual-source.jpg"><img src="docs/screenshots/visual-source.jpg" width="240" alt="The same HTML visual switched to its source view"></a></td>
  </tr>
  <tr>
    <th>Appearance and fonts</th>
    <th>Custom primary color</th>
    <th>Default light</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/appearance-settings.jpg"><img src="docs/screenshots/appearance-settings.jpg" width="240" alt="Nord selected with Inter for UI and content and JetBrains Mono for code"></a></td>
    <td><a href="docs/screenshots/primary-color.jpg"><img src="docs/screenshots/primary-color.jpg" width="240" alt="A teal primary color selected with Theme default available to reset it"></a></td>
    <td><a href="docs/screenshots/theme-light.jpg"><img src="docs/screenshots/theme-light.jpg" width="240" alt="The default light palette with Wanted Sans and D2Coding"></a></td>
  </tr>
  <tr>
    <th>Nord · Inter</th>
    <th>Dracula · Geist</th>
    <th>Solarized · IBM Plex Sans</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/theme-nord.jpg"><img src="docs/screenshots/theme-nord.jpg" width="240" alt="A streaming chat in Nord with Inter and JetBrains Mono"></a></td>
    <td><a href="docs/screenshots/theme-dracula.jpg"><img src="docs/screenshots/theme-dracula.jpg" width="240" alt="The same chat in Dracula with Geist and Geist Mono"></a></td>
    <td><a href="docs/screenshots/theme-solarized.jpg"><img src="docs/screenshots/theme-solarized.jpg" width="240" alt="The same chat in light Solarized with IBM Plex Sans and Fira Code"></a></td>
  </tr>
  <tr>
    <th>Tool activity</th>
    <th>Subagent status</th>
    <th>Task progress</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/tool-activity.jpg"><img src="docs/screenshots/tool-activity.jpg" width="240" alt="Expanded actions with colored subagent icons, browser and code icons, and a file path"></a></td>
    <td><a href="docs/screenshots/subagents.jpg"><img src="docs/screenshots/subagents.jpg" width="240" alt="Two completed subagents with distinct colors, models, reasoning levels and Open controls"></a></td>
    <td><a href="docs/screenshots/tasks.jpg"><img src="docs/screenshots/tasks.jpg" width="240" alt="A Tasks dialog listing completed mobile and browser checks"></a></td>
  </tr>
  <tr>
    <th>Queue and steering</th>
    <th>Edit a queued message</th>
    <th>Models and reasoning</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/queue-steering.jpg"><img src="docs/screenshots/queue-steering.jpg" width="240" alt="A queued message menu offering Edit message, Steer instead and Cancel message"></a></td>
    <td><a href="docs/screenshots/queue-edit.jpg"><img src="docs/screenshots/queue-edit.jpg" width="240" alt="A queued follow-up edited inline with Cancel and Save controls"></a></td>
    <td><a href="docs/screenshots/model-picker.jpg"><img src="docs/screenshots/model-picker.jpg" width="240" alt="The model dialog with OpenAI Codex models and a reasoning-effort selector"></a></td>
  </tr>
  <tr>
    <th>Recent conversations</th>
    <th>All conversations</th>
    <th>Conversation menu</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/conversation-drawer.jpg"><img src="docs/screenshots/conversation-drawer.jpg" width="240" alt="The drawer with a pinned chat, a running activity indicator and Show all"></a></td>
    <td><a href="docs/screenshots/conversation-filters.jpg"><img src="docs/screenshots/conversation-filters.jpg" width="240" alt="The expanded drawer with archive, project, status, ordering and layout controls"></a></td>
    <td><a href="docs/screenshots/conversation-menu.jpg"><img src="docs/screenshots/conversation-menu.jpg" width="240" alt="The conversation menu with pin, rename, files, project, unread, archive and share controls"></a></td>
  </tr>
  <tr>
    <th>Browser PiP</th>
    <th>Browser controls</th>
    <th>Zoomable browser preview</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/browser-pip.jpg"><img src="docs/screenshots/browser-pip.jpg" width="240" alt="A browser preview alongside its conversation with open, minimize and close controls"></a></td>
    <td><a href="docs/screenshots/browser-sheet.jpg"><img src="docs/screenshots/browser-sheet.jpg" width="240" alt="The browser sheet with address navigation, Control and Open in your browser"></a></td>
    <td><a href="docs/screenshots/browser-zoom.jpg"><img src="docs/screenshots/browser-zoom.jpg" width="240" alt="An expanded browser preview at 150 percent with zoom and reset controls"></a></td>
  </tr>
  <tr>
    <th>Workspace and preferences</th>
    <th>Skills</th>
    <th>MCP and permissions</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/workspace.jpg"><img src="docs/screenshots/workspace.jpg" width="240" alt="The workspace dialog with its fixed header and project, routine, memory, context, skill and connection cards"></a></td>
    <td><a href="docs/screenshots/workspace-skills.jpg"><img src="docs/screenshots/workspace-skills.jpg" width="240" alt="The Skills screen with a single header, Import, Add skill and editable installed skills"></a></td>
    <td><a href="docs/screenshots/workspace-connections.jpg"><img src="docs/screenshots/workspace-connections.jpg" width="240" alt="A connected MCP server with per-tool permissions and its available tools"></a></td>
  </tr>
  <tr>
    <th>Files and outputs</th>
    <th>Rename dialog</th>
    <th>Connection and notifications</th>
  </tr>
  <tr>
    <td><a href="docs/screenshots/files-preview.jpg"><img src="docs/screenshots/files-preview.jpg" width="240" alt="Conversation artifacts with a release-notes preview and file actions"></a></td>
    <td><a href="docs/screenshots/rename-dialog.jpg"><img src="docs/screenshots/rename-dialog.jpg" width="240" alt="A focused Rename conversation dialog with its name field, Cancel and Save"></a></td>
    <td><a href="docs/screenshots/settings.jpg"><img src="docs/screenshots/settings.jpg" width="240" alt="Settings showing bridge and browser connection state and response notifications"></a></td>
  </tr>
</table>

[Features](#features) · [Themes and fonts](#appearance) · [Setup guide](#setup-guide)

## Setup guide

- [Choose a hosting route](#choose-a-hosting-route)
- [Install and test on the Mac](#install-and-test-on-the-mac)
- [Authentication](#authentication)
- [Start automatically at login](#start-automatically-at-login)
- [Tailscale: private HTTPS](#tailscale-private-https)
- [Your domain: Caddy](#your-domain-caddy)
- [Your domain: Nginx](#your-domain-nginx)
- [Existing website or VPS](#existing-website-or-vps)
- [LAN or your own VPN](#lan-or-your-own-vpn)
- [Tailscale Funnel: public HTTPS](#tailscale-funnel-public-https)
- [Cloudflare Tunnel and Access: optional](#cloudflare-tunnel-and-access-optional)
- [iPhone installation and notifications](#iphone-installation-and-notifications)
- [Configuration reference](#configuration-reference)
- [Updates, backup, and removal](#updates-backup-and-removal)
- [Troubleshooting](#troubleshooting)
- [Deployment acceptance checks](#deployment-acceptance-checks)
- [Development and architecture](#development-and-architecture)

## Features

- Live streamed responses, searchable and virtualized history, Markdown,
  compact D2Coding code blocks, linked citations, and expandable tool activity.
- Draft cards for Aside's draft previews (email, iMessage, Slack, LinkedIn,
  calendar invites, X posts) with Copy and the same Send/Post action as the app.
- Interactive HTML visuals with preview/source switching, image zoom/pan, and
  file attachments. Browse conversation outputs and project files, preview
  documents and source, and rename or delete files within the permitted roots.
- Model, provider, and reasoning-effort selection.
- Follow-up queue with **Edit message**, **Steer instead**, and **Cancel message**.
  It shares Aside's native queue and follows its queue/steer preference.
  Stopping a response pauses its queue until resumed.
- Message menus offer copy, edit sent messages, branch, quote into the composer,
  start a side chat, and jump to an earlier turn. Long-press opens the menu on
  phones; releasing the touch keeps it open.
- Native approval, confirmation, and question prompts; task progress, outputs,
  and subagent status/model/duration. Subagents use Aside's eight-color icons
  consistently in activity and agent lists.
- Automatically updated browser tabs, a preview sheet, and a draggable PiP that
  remembers its position. Previews can be expanded, zoomed, panned, and dismissed
  with a gesture; pages can also open in your own browser. Live frames, page
  clicks, scrolling, typing, navigation, history, and bookmarks are available
  from the browser sheet.
- Pin, rename, share, archive, delete, mark read/unread, move to a project, and
  copy conversation links or session IDs. Pins and read state sync with Aside.
  Pins appear first; other conversations sort by their latest activity.
- Recent conversations with **Show all**, using Aside's ordinary-chat visibility
  rules. Subagents and temporary CLI sessions stay out of the ordinary list.
  Search covers conversation history; Show all also offers project, status,
  archive, and ordering filters. Running chats show activity indicators;
  unread completed chats show dots.
- New incognito and project conversations, plus tab, file, folder, and skill
  references in the composer. Dictation is offered where the browser supports it.
- **Settings → Workspace & preferences** connects projects and project instructions,
  routines and run history, memory, context awareness, installed skills,
  MCP connections and tool permissions, custom providers, account/devices,
  and native preferences. Controls follow the connected daemon's capabilities.
- Browser lists switch between **Chat tabs** (including tabs owned by its child
  agents) and **Show all** (web tabs in the conversation's browser window).
  Sleeping tabs stay visible with their state.
- Conversation deep links, last-conversation restoration, and notifications that
  open the matching conversation.
- Light/dark/system mode, 29 theme families (44 light/dark variants), custom primary colors,
  independent UI/content/code fonts, an anchored multiline composer, and mobile
  sheet/drawer transitions. The UI is English; messages keep their own language.
- Web Push completion alerts containing the actual answer preview when the device
  is away from the app. Optional ntfy completion alerts are also available.

[DESIGN.md](DESIGN.md) describes the interface and responsive behavior.

### Find the controls

| What you want to do | Where to go |
| --- | --- |
| Change colors, fonts or text size | Drawer → Settings → Appearance |
| Browse older chats or archived chats | Drawer → Show all; choose Chats or Archive, then filter by project or status |
| Pin, rename, mark unread, archive or share | Header → Session options, or long-press a conversation in the drawer |
| Edit, steer or cancel a queued follow-up | Send while a response runs, then open the queued message's three-dot menu |
| Change the model or reasoning effort | Focus the composer → model chip |
| Inspect an agent or task | Agents or tasks chip above the composer |
| Inspect a tool call | Expand its activity summary; Technical details shows its inputs and output |
| Browse generated files | Session options → Files & outputs |
| Switch between an HTML visual and its code | Source / Preview inside the visual card |
| Send an email, message, invite or post the agent drafted | Send or Post on the draft card, then tap again to confirm |
| Watch or control a browser tab | Open the PiP or Drawer → Browser; select a tab to click, scroll, type and use keys |
| Use a browser fullscreen | Expand browser view keeps page controls active; drag to scroll, use two fingers or zoom buttons to magnify |
| Manage projects, routines, skills or MCP | Drawer → Settings → Workspace & preferences |

Rename, confirmation, model, appearance and workspace controls use dialogs.
Workspace pages share one fixed header; only the body scrolls. Browser previews
use a sheet and a separate zoomable detail view. Available native controls and
models come from the connected Aside profile.

### Appearance

Open **Settings → Appearance** to choose a light palette and dark palette independently.
**System** follows your device's appearance and updates while the app is open.
The palettes cover the theme families available in the Codex desktop app, adapted to
aside-relay's chat surfaces. The aside-relay defaults keep the white/black backgrounds
and purple accent. Each preset supplies its own accent; **Primary color** overrides it,
and **Theme default** restores the preset's color. Send buttons, pins, unread markers,
menus and HTML visual previews use the same primary color. Button text automatically
uses black or white for contrast. The page's theme-color metadata follows the background.

The preset catalog has **29 families and 44 variants**, in addition to aside-relay's
own light and dark defaults:

| Available modes | Theme families |
| --- | --- |
| Light and dark | Absolutely, Catppuccin, Codex, Everforest, GitHub, Gruvbox, Linear, Notion, One, Raycast, Rose Pine, Solarized, VS Code Plus, Vercel, Xcode |
| Dark | Ayu, Dracula, Lobster, Material, Matrix, Monokai, Night Owl, Nord, OG, Oscurange, Sentry, Temple, Tokyo Night |
| Light | Proof |

Choose **Theme mode** first, then select that mode's palette. Both palette choices
are saved, so switching modes keeps each selection. Use a primary-color swatch
or the color picker for a custom accent. The custom accent applies to both modes
until you select **Theme default**. Text size offers 100%, 125%, 150%, 175% and 200%.

The gallery compares the same conversation across default light, Nord, Dracula
and Solarized, and shows a teal custom accent. Its font combinations are examples;
you can mix UI, content and code fonts independently.

| Font setting | Choices | Affects |
| --- | --- | --- |
| UI font | Wanted Sans, System, Inter, Geist, Noto Sans KR, IBM Plex Sans, Noto Serif KR | Headers, controls, menus and dialogs |
| Content font | Wanted Sans, System, Inter, Geist, Noto Sans KR, IBM Plex Sans, Noto Serif KR | Conversation messages and HTML previews |
| Code font | D2Coding, System Mono, JetBrains Mono, Fira Code, Geist Mono | Code blocks and visual source |

Wanted Sans remains the UI and content default. D2Coding remains the code default.
System fonts use the device's installed fonts. The other webfonts are
fetched through the bridge's same-origin allowlisted font proxy and cached locally;
Korean fonts use WOFF2 unicode-range subsets rather than downloading a whole family.
A system fallback remains available when a download fails.

Appearance and text size persist in this browser's local storage and apply before
React mounts. These choices belong to aside-relay and do not modify native Aside
preferences. New font downloads require the bridge to reach fonts.googleapis.com
and fonts.gstatic.com; Wanted Sans uses cdn.jsdelivr.net.

## Choose a hosting route

The **bridge and Aside run together on a Mac**. A VPS, NAS, or existing website can
provide the HTTPS front end, but it must forward requests to that Mac. Uploading
only `web/dist` to a static host does not provide conversations, agent execution,
browser tools, WebSockets, or push delivery.

```text
phone / browser
    │ HTTPS + WSS
    ▼
Tailscale Serve, Caddy, Nginx, or another HTTPS proxy
    │ private connection
    ▼
Mac: aside-relay :8799 → Aside CLI / local daemon / browser profile
```

| Route | Address | Requirements | Login |
| --- | --- | --- | --- |
| Local Mac | `http://127.0.0.1:8799` | Mac only | Automatic on loopback |
| Tailscale Serve — recommended for personal use | `https://mac-name.tailnet-name.ts.net` | Tailscale on Mac and phone; same tailnet | Paste bridge token once per browser/app |
| Own domain, Caddy or Nginx | `https://chat.example.com` | Domain, trusted TLS certificate, reachable proxy | Paste bridge token |
| Existing VPS + Mac | Your domain | HTTPS proxy plus Tailscale or SSH connection to Mac | Paste bridge token |
| LAN / WireGuard / another VPN | Private HTTPS hostname or IP | Private network plus a certificate trusted by each device | Paste bridge token |
| Tailscale Funnel | Public `https://…ts.net` | Funnel enabled; local proxy protecting token bootstrap | Paste bridge token |
| Cloudflare Tunnel + Access | Your domain | Cloudflare domain, tunnel, Access policy | Automatic after verified Access login |

For remote use, choose **HTTPS**, even over a VPN. Browser secure-context APIs,
Web Push, and service workers depend on it. Plain `http://192.168.…:8799` or
`http://100.…:8799` is not the phone-installation path described here.

Before installing, identify these values. Replace example addresses and paths
throughout the selected recipe; do not copy placeholder credentials literally.

| Input | Default / decision |
| --- | --- |
| Mac user | The signed-in macOS user who owns the Aside account and browser profile |
| Checkout | A permanent directory, such as `~/projects/aside-relay` |
| Aside CLI | `~/.local/bin/aside`, or the actual absolute executable path |
| Aside account | `u0`; use the account that owns the intended browser profile |
| Aside user directory | `u0` → `~/.aside/u/0`; `u1` → `~/.aside/u/1` |
| Bridge listener | `127.0.0.1:8799`; keep it private when using a local proxy |
| Remote address | One stable HTTPS origin at `/`, preferably a dedicated subdomain |
| Access route | Private Tailscale/VPN, or a public domain with bridge-token login |
| Notifications | Optional; iPhone needs the HTTPS Home Screen app |

On an existing installation, preserve its token and state, and edit only the
settings needed for the chosen route. Check existing proxy/Serve configuration
before assigning a hostname or port already used by another application.

## Install and test on the Mac

> **Windows:** the same steps apply with these substitutions — the walkthrough
> below is written for macOS. Install Python 3.11+ and Node from
> [python.org](https://www.python.org/downloads/) and [nodejs.org](https://nodejs.org)
> (check "Add to PATH"), then in PowerShell:
>
> ```powershell
> git clone https://github.com/mym0404/aside-relay.git
> cd aside-relay
> py -3.13 -m venv .venv
> .\.venv\Scripts\python -m pip install -r requirements.txt
> npm ci
> npm run build
> .\.venv\Scripts\python scripts\setup.py --yes
> .\.venv\Scripts\python server.py
> ```
>
> Differences from the macOS steps:
>
> - The Aside CLI comes with the app installer and lands on `PATH`
>   (`%LOCALAPPDATA%\Aside\CLI\current\aside.exe`); `aside --version` should work
>   in a new terminal. `ASIDE_BIN` defaults to it, so you usually do not set it.
> - No Homebrew, no `open -a Aside`, no `python3` — use `py`/`python` and start
>   the app from the Start menu or `Start-Process "$env:LOCALAPPDATA\Aside\Application\Aside.exe"`.
> - `scripts/setup.py --install-service` registers a Task Scheduler logon task
>   named `aside-relay` (instead of a launchd plist) and runs the bridge through
>   `pythonw` with logs in `<repo>\logs\`. Remove it with
>   `scripts\setup.py --uninstall-service`.
> - Six backend tests that need to create symlinks are skipped automatically
>   unless Windows Developer Mode (or an administrator shell) is enabled; enable
>   *Settings → System → For developers → Developer Mode* to run them.
> - Everything else (Tailscale Serve, Caddy/Nginx, Cloudflare Tunnel, the phone
>   PWA) is identical: the bridge still listens on `127.0.0.1:8799`.

### 1. Prerequisites

- macOS, with the [Aside app](https://aside.dev) installed and signed in.
- Aside CLI installed and authenticated for the same account as the browser profile.
- Python **3.11 or later**. The bridge uses `asyncio.timeout`; the WebSocket
  dependency also requires 3.11+. The setup wizard's older 3.10 check is insufficient.
- Node.js **22.22.2+ on 22.x, 24.15.0+ on 24.x, or 26+**, plus npm. These minimums
  include the test dependencies in the lockfile. Node is needed for builds/tests;
  the built app runs with Python and Aside.
- Git. If macOS offers to install Command Line Tools when running `git`, complete
  that installation first.

With [Homebrew](https://brew.sh) already installed, one option is:

```bash
brew install python@3.13 node@24
export PATH="$(brew --prefix node@24)/bin:$PATH"
python3.13 --version
node --version
npm --version
```

Use a compatible Python from another installer if preferred. Replace
`python3.13` in the next command with that interpreter. Do not install Python
packages into macOS's system Python.

### 2. Check Aside first

Open Aside, sign in, and open its browser profile for the account you intend to
use. On a standard install:

```bash
open -a Aside
~/.local/bin/aside --version
~/.local/bin/aside account list
~/.local/bin/aside --account u0 --host local session list
curl --fail --silent --show-error http://127.0.0.1:21420/health
```

Account/session output can include personal information; keep it out of public
logs. If the CLI is not authenticated, run `~/.local/bin/aside login` and select
the intended account. If its path differs, use that path in these commands and
set `ASIDE_BIN` below.

A reachable daemon alone does not prove that the browser profile is connected.
The Browser check in the web app and an actual browser task are the final tests.
Keep Aside and that profile running under the same logged-in Mac user.

### 3. Clone, isolate dependencies, and build

```bash
mkdir -p "$HOME/projects"
cd "$HOME/projects"
git clone https://github.com/mym0404/aside-relay.git
cd aside-relay
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
npm ci
npm run build
```

`npm run build` checks TypeScript and generates `web/dist`. Keep this checkout at
its permanent path before installing the login service.

### 4. Configure

For a fresh install with standard paths, run:

```bash
.venv/bin/python scripts/setup.py --yes
```

This checks prerequisites, creates the access token, and writes
`~/.aside-relay/env`. On a fresh installation it does not enable Cloudflare,
ntfy, or the login service. Existing settings are preserved, so `--yes` does
**not** remove an older Cloudflare configuration.

The interactive wizard is also available:

```bash
.venv/bin/python scripts/setup.py
```

(On Windows: `.\.venv\Scripts\python scripts\setup.py`.)

For Tailscale or your own domain, answer **no** to its Cloudflare question. Its
ntfy question is separate from built-in Web Push, which needs no ntfy service.
Answer no to service installation until the foreground test below passes.

For manual setup, first create its directory with `mkdir -p "$HOME/.aside-relay"`.
Then create/edit `~/.aside-relay/env` with the following values, or edit an
existing configuration to choose a different account. A config file is optional
with all defaults; the server generates a missing token itself.

```dotenv
ASIDE_RELAY_HOST=127.0.0.1
ASIDE_RELAY_PORT=8799
# macOS only — Windows finds the CLI on PATH / %LOCALAPPDATA%\Aside\CLI\current automatically
#ASIDE_BIN=~/.local/bin/aside
ASIDE_ACCOUNT=u0
ASIDE_USER_DIR=~/.aside/u/0
ASIDE_DAEMON_URL=http://127.0.0.1:21420
```

For an existing installation switching away from Access, set these entries empty
in that file and remove conflicting values from the process environment:

```dotenv
ASIDE_RELAY_ACCESS_TEAM=
ASIDE_RELAY_ACCESS_AUD=
ASIDE_RELAY_ACCESS_EMAILS=
ASIDE_RELAY_ACCESS_CNS=
```

Keep `ASIDE_ACCOUNT` and `ASIDE_USER_DIR` consistent. For example, change both to
`u1` and `~/.aside/u/1`. Protect the configuration:

```bash
chmod 600 "$HOME/.aside-relay/env"
```

File precedence and the complete settings table are in
[Configuration reference](#configuration-reference).

### 5. Run and verify locally

From the checkout:

```bash
.venv/bin/python server.py
```

Keep that terminal running. Open `http://127.0.0.1:8799` on the **same Mac**.
Local login is automatic. In another terminal:

```bash
curl --fail --silent --show-error http://127.0.0.1:8799/ > /dev/null
lsof -nP -iTCP:8799 -sTCP:LISTEN
```

In the app, check **Settings → Connection**: Bridge should be Connected, Aside
Running, and Browser Connected. Start a new chat, send a short prompt, and check
that a streamed answer appears. Ask it to open `https://example.com`, then check
the browser preview. A successful HTML page or health response alone does not
establish that chat and browser actions work.

Stop the foreground server with Ctrl-C before installing the login service.
Use a **single bridge process**; do not add multiple Uvicorn/Gunicorn workers.
Run state, WebSocket subscribers, and browser-process coordination live in that
process.

## Authentication

The bridge creates a random token in `~/.aside-relay/token` with mode `0600` if
none exists. It is a shared credential granting access to the connected Aside
account, including agent execution and its logged-in browser. Share it only with
people/devices you intend to give that access.

For Tailscale, your own domain, LAN/VPN, or Funnel:

1. On the Mac, copy the token without printing it into terminal output:

   ```bash
   pbcopy < "$HOME/.aside-relay/token"
   ```

2. Transfer it through a private channel to the phone if clipboard sharing is not
   available. Open the final HTTPS address.
3. Open **Settings → Access token**, paste it, and press **Connect**.
4. Bridge and Browser should connect; the conversation drawer should load.

Repeat once for each separate browser, Home Screen app, or new origin. The UI
stores the token in that origin's local storage and exchanges it for the
HttpOnly `ar_token` cookie used by images and WebSockets. The cookie lasts 30
days; saved-token login can renew it. Do not put tokens in URLs or screenshots.
If using `ASIDE_RELAY_TOKEN` or a custom token file, copy that configured token
instead of the default file.

Automatic `/api/web-token` login has only two paths: requests whose host **and**
client are loopback, or a cryptographically verified Cloudflare Access JWT.
Tailscale identity headers, VPN membership, generic SSO headers, and HTTP Basic
Auth do not trigger automatic bridge login. Tailscale/VPN access control and the
bridge token are separate checks, not independent multi-factor authentication.

For a custom proxy:

- Preserve the public `Host`, forward the HTTPS scheme, and forward `/ws` as a
  WebSocket. Keep frontend and API on the same origin.
- In non-Cloudflare public proxies, deny `/api/web-token` as in the recipes below.
  Rewriting both the host and client to loopback could otherwise activate local
  token issuance. A remote unauthenticated request must never return a token.
- Preserve `Authorization` and cookies. HTTP Basic Auth on the same proxy can
  conflict with the app's `Authorization: Bearer …` requests; it is not a
  drop-in login configuration for this app.
- Serve at `/`, not a prefix such as `/aside`. The app uses absolute API, asset,
  service-worker, and manifest paths.
- Trust forwarded headers only from the actual proxy. Uvicorn defaults to
  loopback proxy peers. For a proxy connecting directly from another machine,
  set `FORWARDED_ALLOW_IPS` to its exact private IP, never a public wildcard.

Conversation, browser-action, and upload APIs require the token. The static UI
and `/api/health` diagnostic endpoint are public; the latter includes operational
metadata. Use a private network or a front-door login if you also need to hide
that metadata. This is a personal bridge for one configured Aside account,
without separate user roles or per-user tokens.

## Start automatically at login

After the foreground test passes, from the permanent checkout:

```bash
.venv/bin/python scripts/setup.py --install-service
plutil -lint "$HOME/Library/LaunchAgents/com.aside-relay.plist"
launchctl print "gui/$(id -u)/com.aside-relay"
```

Invoking the installer with `.venv/bin/python` records that interpreter in
`~/Library/LaunchAgents/com.aside-relay.plist`. `--install-service` installs the
service only; it does not install dependencies or perform the setup checks.
The LaunchAgent starts at login and restarts after an unsuccessful exit. It runs
as your user, not root, and loads the configuration file on each server start.

Restart after a configuration edit, inspect logs, or remove the service:

```bash
launchctl kickstart -k "gui/$(id -u)/com.aside-relay"
tail -n 80 logs/bridge.err.log
tail -n 80 logs/bridge.out.log
# Remove only the bridge login service; configuration and conversations remain.
.venv/bin/python scripts/setup.py --uninstall-service
```

Keep Aside and your network/proxy app enabled at login too. A running bridge
cannot replace a disconnected browser profile. The Mac must remain awake and
online; a login LaunchAgent does not provide browser access before user login
or after logout. For a temporary foreground test, `caffeinate -i` prevents idle
system sleep until Ctrl-C. Closed-lid behavior still depends on the Mac's power
and display setup. Screen lock, system sleep, and browser-profile connectivity
are different conditions.

If you move the checkout or replace its virtual environment, rerun the service
installer with the new `.venv/bin/python` path.

On Windows the same flag registers a Task Scheduler logon task named
`aside-relay` instead of a LaunchAgent. It launches the bridge through
`pythonw` so no console window stays open:

```powershell
.\.venv\Scripts\python scripts\setup.py --install-service
Get-ScheduledTask -TaskName aside-relay        # inspect
Stop-ScheduledTask -TaskName aside-relay       # after a config edit:
Start-ScheduledTask -TaskName aside-relay      # reload it
Get-Content logs\bridge.err.log -Tail 80
.\.venv\Scripts\python scripts\setup.py --uninstall-service
```

No elevation is required; the task runs as your user at logon, and logs land in
`logs\bridge.out.log` / `logs\bridge.err.log`.

## Tailscale: private HTTPS

This route needs no public domain, router forwarding, or Cloudflare.
[Serve](https://tailscale.com/docs/features/tailscale-serve) gives a private HTTPS
address accessible to permitted devices in your tailnet.

1. Install Tailscale on the Mac and phone. Sign both into the same tailnet and
   enable the connection on both. On macOS, use the app's CLI integration.
   If `tailscale` is unavailable, use the bundled CLI:

   ```bash
   export TAILSCALE_BE_CLI=1
   alias tailscale="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
   ```

   See the [macOS CLI instructions](https://tailscale.com/docs/reference/tailscale-cli?tab=macos).
2. Leave the bridge on `127.0.0.1:8799`. Confirm it works locally first.
3. Inspect existing sharing, then create a dedicated HTTPS listener:

   ```bash
   tailscale status
   tailscale serve status
   tailscale serve --bg --https=443 http://127.0.0.1:8799
   tailscale serve status
   ```

4. Follow the command's HTTPS-enablement link if prompted. Open the exact
   `https://…ts.net` URL it prints on the phone with Tailscale connected.
5. Paste the bridge token using [Authentication](#authentication). A 401 from
   `/api/web-token` before token login is expected on this route.
6. Check chat and browser previews over cellular as well as Wi-Fi. Restrict
   access in the tailnet policy to the intended users/devices and serving port.

If port 443 is already assigned to another Serve application, choose a free
HTTPS port, for example `--https=8443`, and use the printed URL including its
port. Do not mount this app at `--set-path=/aside`.

The `--bg` setting persists across Tailscale restarts. Stop only this listener
with the corresponding flags; avoid `serve reset`, which clears other sharing:

```bash
tailscale serve --bg --https=443 off
```

Commands and persistence are documented in the
[Serve CLI reference](https://tailscale.com/docs/reference/tailscale-cli/serve).
Keep this listener private; Funnel changes who can reach it.

## Your domain: Caddy

Use a dedicated hostname, such as `chat.example.com`, with any DNS provider.
The HTTPS proxy can run on the Mac or on a VPS with a private connection to it.
For direct hosting on the Mac:

1. Give the Mac a stable LAN address. Point the hostname's A record to your public
   IPv4 address. Add an AAAA record only if IPv6 actually reaches the same proxy.
   Use dynamic DNS if your public address changes.
2. Forward router TCP ports 80 and 443 to **Caddy**, allow those ports through the
   firewall, and leave the bridge port 8799 unforwarded. If the ISP uses CGNAT or
   blocks inbound access, use Tailscale or the VPS route instead.
3. Install Caddy on the Mac:

   ```bash
   brew install caddy
   ```

4. Add the following site block to `$(brew --prefix)/etc/Caddyfile`, replacing
   `chat.example.com`. Preserve any existing site blocks.

   ```caddyfile
   chat.example.com {
       @bootstrap path /api/web-token
       respond @bootstrap 403
       reverse_proxy 127.0.0.1:8799 {
           header_up Host {hostport}
           header_up X-Forwarded-Proto {scheme}
       }
   }
   ```

5. Validate and start the Homebrew login service:

   ```bash
   caddy validate --config "$(brew --prefix)/etc/Caddyfile" --adapter caddyfile
   brew services start caddy
   brew services info caddy
   ```

   If Caddy already runs, apply the edited configuration with
   `caddy reload --config "$(brew --prefix)/etc/Caddyfile" --adapter caddyfile`.
6. Open `https://chat.example.com`, paste the bridge token, and perform the
   [acceptance checks](#deployment-acceptance-checks) from another network.

Caddy handles [WebSocket upgrades and proxy headers](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
Its certificate storage must persist and be
writable by the service user. For this Homebrew service, the data directory is
under `$(brew --prefix)/var/lib`; retain it during updates.
[Homebrew service details](https://formulae.brew.sh/formula/caddy).
[Automatic HTTPS requirements](https://caddyserver.com/docs/automatic-https)
cover DNS, reachable validation ports, and certificate renewal.

For a Debian/Ubuntu VPS, install Caddy using its official repository:

```bash
sudo apt-get update
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo chmod o+r /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install caddy
```

Add the site to `/etc/caddy/Caddyfile`, choose its Mac upstream as described in
[Existing website or VPS](#existing-website-or-vps), then run:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Installation commands: [Caddy packages](https://caddyserver.com/docs/install).
Do not run a second proxy on ports already owned by your existing web server.

## Your domain: Nginx

If you already have an HTTPS Nginx site, keep its certificate configuration and
add the proxy directives below to a dedicated hostname. The example assumes
Nginx and the bridge are on the same Mac, or an SSH tunnel exposes the Mac on the
proxy's loopback interface. For another upstream, replace the address accordingly.

For a fresh Debian/Ubuntu proxy, first point DNS to it, open TCP 80/443, and install:

```bash
sudo apt-get update
sudo apt-get install nginx certbot python3-certbot-nginx
sudo mkdir -p /var/www/aside-acme
```

Create `/etc/nginx/sites-available/aside-relay` with this temporary HTTP site
for certificate issuance:

```nginx
server {
    listen 80;
    server_name chat.example.com;
    location /.well-known/acme-challenge/ { root /var/www/aside-acme; }
    location / { return 404; }
}
```

For this new site only, enable it, validate, obtain the certificate, and then
replace the temporary file with the final configuration below:

```bash
sudo ln -s /etc/nginx/sites-available/aside-relay /etc/nginx/sites-enabled/aside-relay
sudo nginx -t
sudo systemctl reload nginx
sudo certbot certonly --webroot -w /var/www/aside-acme -d chat.example.com
```

Final configuration; replace every `chat.example.com`, including certificate paths.
Use the paths printed by Certbot if the certificate name has an added suffix:

```nginx
# At http context, outside server blocks; define this map only once.
map $http_upgrade $aside_connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    server_name chat.example.com;
    location /.well-known/acme-challenge/ { root /var/www/aside-acme; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    server_name chat.example.com;
    ssl_certificate /etc/letsencrypt/live/chat.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.example.com/privkey.pem;
    client_max_body_size 26m;

    location = /api/web-token { return 403; }
    location / {
        proxy_pass http://127.0.0.1:8799;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $aside_connection_upgrade;
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }
}
```

On Debian/Ubuntu, `sites-enabled` is included within `http`, so the map above can
remain in the site file. In another layout, put it in the main `http` context.
The 26 MiB proxy allowance accommodates the default 24 MiB file limit and
multipart overhead; increase both limits together if changing uploads.

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo certbot renew --dry-run
```

Ensure successful renewals reload Nginx to load the new certificate. For the
Debian/Ubuntu paths above, create an executable deploy hook at
`/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh` containing:

```sh
#!/bin/sh
/usr/sbin/nginx -t && /usr/bin/systemctl reload nginx
```

For these package paths, make the saved hook executable and enable/check renewal:

```bash
sudo chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo systemctl enable --now certbot.timer
sudo systemctl list-timers certbot.timer
sudo certbot renew --dry-run --run-deploy-hooks
```

If your Certbot installer uses a differently named timer or cron job, verify
that scheduler instead. These Nginx examples listen on IPv4. If publishing an
AAAA record, also add `listen [::]:80;` and `listen [::]:443 ssl;` to the
corresponding server blocks and verify IPv6 reachability. Open the HTTPS address,
paste the token, and test streamed replies and browser images. Explicit upgrade headers
are required for [Nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html).
[Certbot's Nginx/Webroot documentation](https://eff-certbot.readthedocs.io/en/stable/using.html)
explains certificate issuance and renewal hooks.

## Existing website or VPS

Keep your current website and add a dedicated subdomain for aside-relay.
Proxy the **entire** subdomain, including `/api/*`, `/ws`, `/assets/*`, `/sw.js`,
`/manifest.webmanifest`, `/icons/*`, and `/c/<session>` routes. Do not cache API,
authentication, HTML entry pages, or WebSocket traffic. Keep the application's
cache headers for hashed assets. Generic static hosting alone cannot run this
Mac bridge.

There are two ways to connect a remote proxy to the Mac without exposing 8799
on the public Internet.

### Option A: VPS reaches the Mac through Tailscale

Install Tailscale on the VPS and Mac in the same tailnet. On a Linux VPS without
an existing Tailscale installation, the official installer and login are:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Follow the login URL to join the intended tailnet.
[Linux installation instructions](https://tailscale.com/docs/install/linux).
Complete the Mac's private Serve recipe first. Permit the VPS to reach that Mac's Serve port in the
tailnet policy. From the VPS, an unauthenticated `/api/sessions` request to the
Mac's Serve URL should return 401, proving the private path is reachable.

For Caddy on the VPS, use this site instead of the loopback upstream:

```caddyfile
chat.example.com {
    @bootstrap path /api/web-token
    respond @bootstrap 403
    reverse_proxy https://mac-name.tailnet-name.ts.net {
        header_up Host {hostport}
        header_up X-Forwarded-Proto https
    }
}
```

Replace the upstream with the actual Serve URL, including its port if not 443.
Caddy uses that hostname
for TLS validation while preserving the public Host explicitly. Keep upstream
certificate verification enabled. The phone now needs only the public HTTPS
address and bridge token; Tailscale is needed on the **VPS and Mac** for this
route. The Mac and Serve listener must remain online.

### Option B: Mac creates an SSH reverse tunnel to the VPS

Use a VPS account that permits TCP forwarding. Verify the server's host-key
fingerprint through your VPS provider before accepting the first SSH connection.
If you do not already have a suitable key, create a dedicated one on the Mac
(do not overwrite an existing key), and install only its public key on the VPS:

```bash
ssh-keygen -t ed25519 -f "$HOME/.ssh/aside-relay-vps"
cat "$HOME/.ssh/aside-relay-vps.pub" | ssh bridge-user@vps.example.com 'umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys'
ssh-add --apple-use-keychain "$HOME/.ssh/aside-relay-vps"
```

Keep the private key on the Mac. To test the forwarding connection:

```bash
ssh -N -T \
  -i "$HOME/.ssh/aside-relay-vps" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -R 127.0.0.1:18799:127.0.0.1:8799 bridge-user@vps.example.com
```

Leave it running during the initial test. The VPS now has a **loopback-only**
port 18799 forwarding to the Mac bridge. In the Caddy/Nginx public-domain recipe,
use `127.0.0.1:18799` as the upstream instead of port 8799. Keep the bootstrap
block and public Host. Permit public 80/443 and SSH as required; do not publish
18799 or turn on wildcard `GatewayPorts`.

For automatic reconnection at Mac login, add a dedicated entry to `~/.ssh/config`:

```sshconfig
Host aside-relay-vps
    HostName vps.example.com
    User bridge-user
    IdentityFile ~/.ssh/aside-relay-vps
    IdentitiesOnly yes
    UseKeychain yes
    AddKeysToAgent yes
    BatchMode yes
    ExitOnForwardFailure yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
    RemoteForward 127.0.0.1:18799 127.0.0.1:8799
```

Use the actual private-key path. Test `ssh -N -T aside-relay-vps` interactively
first so host-key verification is complete. Then stop that test and save this
as `~/Library/LaunchAgents/com.aside-relay.ssh.plist`, replacing the log paths
with your **absolute** home path; plist strings do not expand `~`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.aside-relay.ssh</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/ssh</string><string>-N</string><string>-T</string>
    <string>aside-relay-vps</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>/Users/YOUR_USER/.aside-relay/ssh.out.log</string>
  <key>StandardErrorPath</key><string>/Users/YOUR_USER/.aside-relay/ssh.err.log</string>
</dict></plist>
```

```bash
plutil -lint "$HOME/Library/LaunchAgents/com.aside-relay.ssh.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.aside-relay.ssh.plist"
```

The SSH connection's keepalives detect failure; launchd restarts the process.
Check that the remote listening port is still loopback-only and that the HTTPS
app reconnects after a tunnel restart. SSH forwarding semantics are in the
[OpenSSH manual](https://man.openbsd.org/ssh#R).

## LAN or your own VPN

You can use WireGuard, a router VPN, or another private network without Tailscale
or Cloudflare. The recipe still needs an HTTPS name/address trusted by the phone:

- Put Caddy/Nginx on the Mac or a reachable private proxy.
- Make private DNS resolve the chosen name to that proxy.
- Use the public-domain TLS recipe if you already have a certificate for that
  name. A DNS-based ACME challenge can issue certificates without opening the
  private service publicly; its plugin/credentials depend on your DNS provider.
- Keep the bridge on loopback when the proxy runs on the Mac. If a separate LAN
  proxy must connect directly, bind `ASIDE_RELAY_HOST` to the Mac's specific
  LAN/VPN address, allow only the proxy through the firewall, and set
  `FORWARDED_ALLOW_IPS` to that proxy's exact private address. Use an encrypted
  VPN link for traffic crossing networks. Do not forward that bridge port publicly.

For a LAN-only installation with no domain/certificate provider, Caddy can issue
an internal certificate. Add a local DNS record, for example `aside.home.arpa`,
pointing to the Mac's stable LAN IP, then use this Caddy site:

```caddyfile
aside.home.arpa {
    tls internal
    @bootstrap path /api/web-token
    respond @bootstrap 403
    reverse_proxy 127.0.0.1:8799 {
        header_up Host {hostport}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

Find the **public root certificate** at `pki/authorities/local/root.crt` under
Caddy's data directory. For the Mac Homebrew service this is normally
`$(brew --prefix)/var/lib/caddy/pki/authorities/local/root.crt`; check the running
service's data directory if it differs. Transfer only that certificate to your
own devices, never `root.key` or other private keys.

On iPhone, install the downloaded certificate profile in Settings, then enable
it under **General → About → Certificate Trust Settings → Enable full trust for
root certificates**. Open `https://aside.home.arpa` and confirm there is no TLS
warning before installing the Home Screen app. Each client must trust this CA;
clicking through a certificate warning is not an installation test. Local DNS
must also be reachable through the VPN when away from home.
[Caddy internal TLS](https://caddyserver.com/docs/caddyfile/directives/tls),
[Apple certificate trust instructions](https://support.apple.com/en-us/102390).

## Tailscale Funnel: public HTTPS

Funnel is an alternative when you want an Internet-accessible `…ts.net` URL
without a personal domain. It makes the listener public, unlike private Serve.
Use the bridge token and a local bootstrap-blocking proxy. Do not convert an
existing private listener without checking who will gain access.

Install Caddy and start this separate loopback-only site, either by adding it to
your running Caddyfile or using a dedicated file:

```caddyfile
http://:8798 {
    bind 127.0.0.1
    @bootstrap path /api/web-token
    respond @bootstrap 403
    reverse_proxy 127.0.0.1:8799 {
        header_up Host {hostport}
        header_up X-Forwarded-Proto https
    }
}
```

Use one Caddy instance: if its login service already runs, add this block to its
existing Caddyfile and reload it. Otherwise create the directory with
`mkdir -p "$HOME/.config/aside-relay"`, save the dedicated file below, and test
it in the foreground. Do not start another instance using the same admin port.

For a dedicated file at `~/.config/aside-relay/Funnel.Caddyfile`:

```bash
caddy validate --config "$HOME/.config/aside-relay/Funnel.Caddyfile" --adapter caddyfile
caddy run --config "$HOME/.config/aside-relay/Funnel.Caddyfile" --adapter caddyfile
```

In another terminal, use a free Funnel HTTPS port (8443 here leaves a private
443 Serve listener intact):

```bash
tailscale funnel --bg --https=8443 http://127.0.0.1:8798
tailscale funnel status
```

Enable Funnel through the command's policy prompt if necessary. Open the printed
public URL, paste the token, and verify that an unauthenticated `/api/web-token`
returns 403. Add this Caddy site to the login service configuration for continued
use; the dedicated foreground command alone stops when its process exits.
To remove only this Funnel listener:

```bash
tailscale funnel --bg --https=8443 off
```

The `bind` directive keeps port 8798 loopback-only while accepting the forwarded
Funnel hostname. [Caddy binding reference](https://caddyserver.com/docs/caddyfile/directives/bind).
Funnel ports and prerequisites: [Funnel CLI](https://tailscale.com/docs/reference/tailscale-cli/funnel).
For identity-gated public access, place a compatible session-based login in
front, or choose the optional Access route below. Keep the bridge token too.

## Cloudflare Tunnel and Access: optional

Skip this entire section for Tailscale, VPN, or your own-domain token login.
This recipe uses a named, locally managed tunnel so its configuration is visible
on the Mac. Cloudflare also offers dashboard-managed tunnels.

1. Add your domain to Cloudflare and configure its nameservers.
2. Create a **self-hosted Access application** for `chat.example.com` and an
   Allow policy limited to your intended identity/email. Keep it enabled before
   publishing the hostname. Record its application AUD and your Access team
   domain; use the team domain without `https://` or a path. The AUD is available
   in the application configuration; [JWT validation instructions](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/) explain these values.
3. Install and create the tunnel:

   ```bash
   brew install cloudflared
   cloudflared tunnel login
   cloudflared tunnel create aside-relay
   ```

4. Record the generated UUID and credential-file path. Add this to
   `~/.cloudflared/config.yml`, replacing the hostname, UUID, and absolute path:

   ```yaml
   tunnel: YOUR_TUNNEL_UUID
   credentials-file: /Users/YOUR_USER/.cloudflared/YOUR_TUNNEL_UUID.json
   ingress:
     - hostname: chat.example.com
       service: http://127.0.0.1:8799
       originRequest:
         httpHostHeader: chat.example.com
     - service: http_status:404
   ```

5. Add these entries to `~/.aside-relay/env`, then restart the bridge:

   ```dotenv
   ASIDE_RELAY_ACCESS_TEAM=yourteam.cloudflareaccess.com
   ASIDE_RELAY_ACCESS_AUD=YOUR_ACCESS_APPLICATION_AUD
   ASIDE_RELAY_ACCESS_EMAILS=you@example.com
   ```

6. Validate the tunnel, create DNS, and test it in the foreground:

   ```bash
   cloudflared tunnel ingress validate
   cloudflared tunnel route dns aside-relay chat.example.com
   cloudflared tunnel run aside-relay
   ```

7. Open the HTTPS hostname, complete Access login, and check that the bridge
   connects without pasting a token. The bridge verifies the JWT signature,
   issuer, audience, expiry, and configured identity; it does not trust a plain
   email header. Keep `/api/web-token` reachable through the Access-protected
   tunnel, unlike the non-Access proxy recipes.
8. Stop the foreground tunnel after testing and install its user login service:

   ```bash
   cloudflared service install
   ```

The bridge and tunnel are separate services. Protect the tunnel credentials and
configuration with owner-only permissions. No inbound router port forwarding
is needed. Do not use a temporary unauthenticated quick-tunnel URL as a permanent
replacement for this policy.
[Access application setup](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/),
[named-tunnel setup](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/),
[macOS tunnel service](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/as-a-service/macos/).

## iPhone installation and notifications

1. Finish one HTTPS hosting route. For private Tailscale/VPN, connect the phone
   first. Use the final stable hostname, without certificate warnings.
2. Open it in Safari and connect using the bridge token if prompted.
3. Choose **Share → Add to Home Screen**, then open the installed app. Connect
   again if its storage is separate from Safari's.
4. On **iOS/iPadOS 16.4 or later**, choose **Settings → Notifications → Enable
   notifications** in that Home Screen app and allow the system prompt. Permission
   must follow this user action; a regular iPhone Safari tab is insufficient.
5. Send a message, switch away from the app before completion, and check the
   notification. It should contain the completed answer preview. Tap it to open
   that conversation and verify that the chat loads inside the app.

The Mac sends encrypted Web Push through the browser's push service. It needs
outbound HTTPS access to that service; the phone does not require an inbound
connection from your Mac to receive the OS alert. Opening a private conversation
still requires the phone's Tailscale/VPN connection and a reachable bridge.
Focused devices suppress completion alerts. Long previews are truncated to fit
the payload; stopping a response does not send a completion alert. Network,
system notification settings, and Focus modes can delay or suppress delivery.

Signing keys and subscriptions are created automatically in
`~/.aside-relay/web-push`; keep them across restarts and backups. No Apple
developer account, APNs certificate, or manually issued VAPID key is required.
Changing the hostname or losing the signing key requires enabling notifications
again for that origin. The service worker handles push; it does not turn the app
into an offline conversation client.
[WebKit's Home Screen Web Push requirements](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/).

### Optional ntfy

ntfy is independent of Home Screen Web Push. Set a server URL and a unique topic:

```dotenv
ASIDE_RELAY_NTFY=https://ntfy.sh
ASIDE_RELAY_NTFY_TOPIC=YOUR_PRIVATE_RANDOM_TOPIC
ASIDE_RELAY_NTFY_ENABLED=1
```

Restart the bridge and subscribe to the same topic in an ntfy client. Public
topics are not private merely because they have a name; use a high-entropy topic
or your own protected ntfy service. This bridge's ntfy configuration supplies a
URL and topic, without a separate ntfy username/password option.

## Configuration reference

Values resolve in this order, with the first value winning:

1. Actual environment variables of the server process.
2. `~/.aside-relay/env`.
3. The checkout's `.env`.
4. Built-in defaults.

Env files use `KEY=VALUE`, with optional full-line `#` comments. Do not add
`export`, shell commands, or inline comments. Values do not expand `$HOME`,
`$OTHER_VAR`, or command substitutions. For path settings use an absolute path
or `~`, which the bridge expands. An explicitly empty value in the first file
also overrides a later file. Restart after editing.

A terminal's exported settings are not automatically inherited by a login
LaunchAgent. Put persistent bridge settings in `~/.aside-relay/env`. A custom
`FORWARDED_ALLOW_IPS` value can go there too; Uvicorn reads it at startup. The
service sets `HOME`, and absolute Aside/interpreter paths avoid PATH differences.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASIDE_RELAY_HOST` | `127.0.0.1` | Bind address; normally leave loopback behind a local proxy |
| `ASIDE_RELAY_PORT` | `8799` | Bridge port; update the upstream when changing it |
| `ASIDE_RELAY_TOKEN_FILE` | `~/.aside-relay/token` | Shared token file; generated if absent/empty |
| `ASIDE_RELAY_TOKEN` | Unset | Explicit token override; takes precedence over the token file |
| `ASIDE_BIN` | macOS `~/.local/bin/aside`; Windows `PATH` lookup then `%LOCALAPPDATA%\Aside\CLI\current\aside.exe` | Aside CLI executable |
| `ASIDE_ACCOUNT` | `u0` | CLI account ID; must match its user directory |
| `ASIDE_USER_DIR` | `~/.aside/u/<account number>` | Aside account's sessions and uploads; `u0` uses `0` |
| `ASIDE_DAEMON_URL` | `http://127.0.0.1:21420` | Local Aside daemon |
| `ASIDE_RELAY_FOLLOWUPS_FILE` | `~/.aside-relay/followups.json` | Persistent queue state |
| `ASIDE_RELAY_WEB_PUSH_DIR` | `~/.aside-relay/web-push` | Push signing key and subscriptions |
| `ASIDE_RELAY_UPLOAD_MAX` | `25165824` | Maximum image file size, bytes: 24 MiB |
| `ASIDE_RELAY_MCP_KEEPALIVE` | `1500` | MCP keepalive interval, seconds |
| `ASIDE_RELAY_MCP_TIMEOUT` | `125` | Browser REPL call timeout, seconds |
| `ASIDE_RELAY_SHOT_TTL` | `60` | Screenshot cache lifetime, seconds |
| `ASIDE_RELAY_NTFY` | Empty | ntfy server URL; empty disables ntfy |
| `ASIDE_RELAY_NTFY_TOPIC` | `aside-relay-runs` | Completion-alert topic |
| `ASIDE_RELAY_NTFY_ENABLED` | `1` | ntfy is enabled only with a URL and value `1`; `0` disables |
| `ASIDE_RELAY_ACCESS_TEAM` | Empty | Optional Access team domain, without scheme |
| `ASIDE_RELAY_ACCESS_AUD` | Empty | Optional Access application audience tag |
| `ASIDE_RELAY_ACCESS_EMAILS` | Empty | Comma-separated allowed Access emails; set an explicit allowlist when using Access |
| `ASIDE_RELAY_CF_SERVICE_TOKEN_FILE` | `~/.aside-relay/cf_service_token.json` | Optional JSON with `client_id`/`client_secret` for a separately configured Access service-token client |
| `ASIDE_RELAY_ACCESS_CNS` | Empty | Additional allowed Access service-token common names, comma-separated |
| `FORWARDED_ALLOW_IPS` | Uvicorn's loopback default | Exact trusted proxy peer addresses; relevant when a proxy is on another machine |

The service-token file informs bridge identity verification; it does not make
the web UI send Cloudflare service credentials automatically. A separate client
must supply them to Access. Ordinary browser use needs only the email policy.

WebSocket heartbeats are fixed at 20 seconds. Tab-list caching is 5 seconds;
new-session detection and JSONL polling have internal defaults rather than
exposed environment settings. Start with defaults before changing browser timeouts.
[`.env.example`](.env.example) is also provided as a commented template.

## Updates, backup, and removal

### Update

Wait for active runs to finish and pause queued follow-ups before restarting.
From the checkout:

```bash
git status --short
git pull --ff-only
.venv/bin/python -m pip install -r requirements.txt
npm ci
npm run build
npm test
launchctl kickstart -k "gui/$(id -u)/com.aside-relay"
```

Resolve local changes without discarding them before pulling. For a foreground
server, stop and restart it instead of using `launchctl`. If a Python upgrade
replaces the virtual environment, reinstall the login service afterward.
Reload open clients after a build so they use the new asset bundle. Bypass
proxy caching for HTML/API/auth routes; never cache an authentication response.
Keep the Aside app/CLI compatible; `aside update` updates Aside separately from
this repository and can change its internal interfaces.

### Backup and restore

| State | Default location | Preserve? |
| --- | --- | --- |
| Bridge settings and access token | `~/.aside-relay/env`, `~/.aside-relay/token` | Yes; token is a secret |
| Follow-up queue | `~/.aside-relay/followups.json` | Yes; review queued work before resuming |
| Push keys/subscriptions | `~/.aside-relay/web-push/` | Yes; losing the key requires resubscription |
| Conversations and titles | `~/.aside/u/0/sessions/` | Yes; use the configured account's path |
| Image attachments | `~/.aside/u/0/uploads/` | Yes |
| Browser preferences, draft, PiP position | Client origin's browser storage | Device-specific; a new origin has separate state |
| Screenshots/media caches, logs, built UI | `cache/shots`, `cache/media`, `logs`, `web/dist` | Regenerable; not required for restoring conversations |
| Proxy/TLS/tunnel state | Caddy data, certificate files, proxy config, SSH keys, or tunnel credentials | Preserve separately for the chosen route |

For standard paths and account `u0`, stop the bridge after all runs are idle and
copy state to a private backup directory outside the repository:

```bash
.venv/bin/python scripts/setup.py --uninstall-service
umask 077
backup_dir="$HOME/Backups/aside-relay/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
ditto "$HOME/.aside-relay" "$backup_dir/bridge-state"
ditto "$HOME/.aside/u/0/sessions" "$backup_dir/sessions"
ditto "$HOME/.aside/u/0/uploads" "$backup_dir/uploads"
.venv/bin/python scripts/setup.py --install-service
```

Adjust source paths for custom account/state directories. Stop a foreground
server with Ctrl-C instead of uninstalling/reinstalling a service it never used.
Store backups privately: they contain tokens, messages, images, and subscription
credentials. Backing up bridge state does not transfer Aside's authenticated Mac
login or Keychain credentials to a new Mac.

To restore, first install and sign into Aside on the target Mac, stop the bridge,
then copy each saved directory/file back to the matching location in the table.
Restore only into an empty target or after separately preserving its current
state; `ditto` merges directories, so mixing two queue/session stores is not a
clean restore. Ensure the files belong to the target Mac user and that token,
configuration, and private keys retain owner-only permissions. Install the login
service again, start the selected proxy, and run the acceptance checks. Enable
notifications again if the origin or key changed.

### Rotate the access token

After active runs finish, stop the bridge and replace the configured token file
with a freshly generated credential. For the default token file:

```bash
.venv/bin/python - <<'PYTOKEN'
from pathlib import Path
import secrets
path = Path.home() / ".aside-relay/token"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(secrets.token_urlsafe(32) + "\n")
path.chmod(0o600)
PYTOKEN
```

Remove/update any `ASIDE_RELAY_TOKEN` override or the file change will have no
effect. Restart the bridge; old saved tokens/cookies stop working. Reconnect each
client through Settings, or verified Access login. Never rotate just to install
another client.

### Remove services

```bash
.venv/bin/python scripts/setup.py --uninstall-service
# If the optional SSH LaunchAgent was installed:
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.aside-relay.ssh.plist"
```

Remove that SSH plist after bootout. Disable only this app's Serve/Funnel listener
with its original flags, or remove its dedicated proxy site and reload the proxy.
Do not stop a shared proxy or clear all Tailscale routes when other apps use them.
Back up before deleting the checkout or account files; uninstalling the bridge
service alone leaves Aside and conversation data intact.

## Troubleshooting

| Symptom | Check and fix |
| --- | --- |
| `ModuleNotFoundError`, or `asyncio.timeout` missing | Use `.venv/bin/python`; verify Python ≥3.11 and install `requirements.txt` in that environment. The wizard's Python check alone is insufficient. |
| npm engine error | Check `node --version` against the lockfile minimums above; ensure the intended Homebrew Node is first on PATH, then run `npm ci`. |
| HTTP 503 “Web UI is not built” | Run `npm ci` and `npm run build` in this checkout. The server serves `web/dist`, not raw TSX. |
| Address already in use | Inspect `lsof -nP -iTCP:8799 -sTCP:LISTEN`; stop your duplicate foreground process or change port and proxy upstream together. |
| Works in a terminal, fails at login | Check the plist's absolute interpreter path, `ASIDE_BIN`, env-file permissions, and `logs/bridge.err.log`. Login services do not inherit your terminal PATH/exports. |
| Remote UI opens but conversations do not | Paste the correct token in Settings. A private/public proxy is not automatic token login. Verify `/api/auth` and cookie forwarding. |
| `/api/web-token` gives 401/403 without Access | Expected before manual login. Do not “fix” it by making the proxy pretend the request is localhost. |
| Remote `/api/web-token` returns a token without login | Remove public access immediately. Fix Host/client rewriting, add the non-Access bootstrap block, and rotate the exposed token before reopening. |
| Cookie/WebSocket auth fails behind a proxy | Preserve Host, `Authorization`, cookies, and `X-Forwarded-Proto: https`; trust only the actual proxy peer. Check `/ws` returns 101 after login. |
| Connection activity indicator keeps spinning or responses stop updating | Check WebSocket upgrade headers and idle timeouts. Exclude API/WS from caching; use the Nginx upgrade configuration above. Bridge heartbeat is 20 seconds. |
| Bridge reachable, Browser unavailable | Open Aside and the matching signed-in browser profile. Check account/path alignment and run an actual browser task; daemon health is insufficient. |
| New conversation fails / wrong account's history | Verify `ASIDE_ACCOUNT`, `ASIDE_USER_DIR`, CLI authentication, and selected profile. Do not delete sessions or rotate the bridge token to repair a profile connection. |
| A browser window closes or changes mode | Reopen the intended profile/window in Aside and retry. The bridge can repair some stale bindings, but cannot operate a profile that is unavailable. |
| Domain certificate fails | Check A/AAAA records, external reachability of the proxy on 80/443, CGNAT, other listeners, and writable persistent certificate storage. Remove an incorrect AAAA record. |
| Private Tailscale URL fails | Check both devices' Tailscale connection, HTTPS enablement, tailnet policy, `tailscale serve status`, and local bridge response. Use the full printed HTTPS URL. |
| VPS responds 502 | Test Mac reachability from the VPS. For SSH, check loopback port 18799 and tunnel logs; for Tailscale, check Mac Serve URL and tailnet permissions. |
| Image upload returns 413 | Match proxy body limits to the configured bridge file limit plus multipart overhead. Default Nginx allowance here is 26 MiB. |
| iPhone notification button unavailable | Use HTTPS and open the installed Home Screen app on iOS/iPadOS ≥16.4, not a Safari tab. |
| Notifications never arrive | Check OS permission/Focus, app is unfocused, Mac awake, outbound push connectivity, saved key/subscription, and bridge logs. Test a completed response rather than a stopped run. |
| Notification opens an unavailable conversation | Reconnect private VPN/Tailscale; verify the same origin/token and that the session still exists. |
| Old assets or blank UI after updating | Reload the client, verify current `/assets/*` return 200, and remove HTML/API cache rules in the proxy. If needed close/reopen the Home Screen app. |

Useful checks from the checkout:

```bash
.venv/bin/python --version
node --version
lsof -nP -iTCP:8799 -sTCP:LISTEN
curl --fail --silent --show-error http://127.0.0.1:21420/health
launchctl print "gui/$(id -u)/com.aside-relay"
tail -n 80 logs/bridge.err.log
```

Logs and CLI output can contain local paths and account/session details. Redact
secrets and personal data before sharing diagnostics.

## Deployment acceptance checks

Complete these after installation, a hostname change, or an update. Do not treat
an HTTP 200 from the UI or `/api/health` as the entire test.

| Check | Observable result |
| --- | --- |
| Local build and runtime | `/` loads the built UI; exactly one bridge owns the configured listener |
| Remote origin | Trusted HTTPS loads from the intended phone/network without a TLS warning |
| Unauthenticated access | A fresh browser cannot list conversations; `/api/sessions` returns 401 before bridge login, or the front-door identity policy intercepts it |
| Bootstrap | Non-Access remote `/api/web-token` returns 401/403 and never a token; Access issues one only after its allowed login |
| Login | Settings → Connect loads history and establishes a `/ws` connection; proxy sees status 101 |
| New conversation | One tap sends the draft, clears it, creates a chat, and streams the response |
| Continue and restore | A follow-up reaches the same conversation; reload or `/c/<session>` restores it |
| Queue and steer | During a run, another message queues; its menu can edit, cancel, or steer it immediately |
| Browser | Agent opens a public test page; title, sheet, and PiP preview update; “Open in your browser” opens the URL |
| Content | Code stays within its block; an HTML visual renders; uploaded image opens and can zoom/pan |
| History controls | Pin and rename survive reload; drawer sorts unpinned chats by latest activity |
| Native session controls | Archive/read state sync with Aside; a side chat opens separately; sent-message edit and branch target the selected turn |
| Agent interaction | Approval/question controls resume the correct session; tasks, outputs, and colored child agents update without moving the composer |
| Files and context | Uploaded files reach the agent; output previews open; files cannot escape their permitted root through a path or symlink |
| Workspace | Connected sections load; a project chat inherits its project; preference changes reach the native app and queue behavior |
| Phone layout | Keyboard/send, multiline drafts, anchored header/composer, and long responses do not cause horizontal page overflow |
| Notification | While away from the Home Screen app, a completed reply produces its answer preview; tapping opens that conversation |
| Services | After user login or a controlled service restart, bridge and selected proxy/tunnel recover without a manual terminal |

For a non-Access route, set your final origin and check unauthenticated endpoints
without sending a token:

```bash
app_origin='https://chat.example.com'
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$app_origin/"
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$app_origin/api/sessions"
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$app_origin/api/web-token"
```

Expected codes are `200`, `401`, and `401` or `403`, respectively. Use the browser
for authenticated checks so the token is not pasted into shell history. An
identity gateway may redirect unauthenticated clients instead; verify the
protected app after completing that gateway's login.

## Development and architecture

The [test guide](tests/README.md) maps current features to logic, backend,
production smoke, and Chromium/mobile WebKit checks, including failure and
recovery cases. Install the browser runtimes once before the aggregate suite:

```bash
npm ci
npx playwright install chromium webkit
npm test
.venv/bin/python server.py
```

For frontend development, run the backend on port 8800 in one terminal:

```bash
ASIDE_RELAY_PORT=8800 .venv/bin/python server.py
```

Then run Vite in another terminal:

```bash
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies API and WebSocket requests to port 8800.
Use the production build/HTTPS hosting route for Home Screen and push checks.

The frontend uses React, TypeScript, StyleX, React Compiler, Base UI, and Vite. Source is
in `web/src`; Python serves `web/dist`. Message rendering loads on demand; the
browser panel is included with the app shell.

Base UI dialogs handle conversation renaming and deletion, model selection,
settings, and tab opening and closing. They stay centered on phones, including
above the keyboard. Browser browsing and media previews use sheets. Action buttons
share secondary, primary, and destructive variants of Base UI Button.

The bridge uses Aside's installed CLI, a persistent MCP browser REPL, PTY-backed
agent runs, the local daemon, and session files. Intermediate messages stream
from `messages.jsonl` rather than waiting for a final CLI answer. Conversations
are stored under the configured Aside user directory; uploads go there so the
agent can read them within Aside's permitted roots.

Conversation visibility and titles come from `sessions.listPreviewItems`, the
same daemon query used by Aside's chat list. Disk messages supply activity times
and previews for those visible conversations. The sidebar starts with pinned
chats and the number of recent unpinned chats configured in Aside (three by
default); **Show all** expands the virtualized list. Search queries native
conversation history, including message content. Archived conversations stay
hidden by default and can be selected explicitly in Show all. Internal child
sessions remain available through their parent conversation's agent list.

Authenticated `/api/native` routes use the installed daemon's session, queue,
project, workspace, and browser contracts. Approvals, questions, branches,
side chats, pins, and read state therefore use the same underlying sessions as
the native app. File routes enforce canonical roots and reject escaping
symlinks; active file previews are sandboxed. Workspace responses remove
credentials, and provider/MCP secrets are write-only in forms.

Browser previews stream JPEG frames with polling fallback; they are not a
remote video/audio stream. Direct controls operate on the conversation's bound
browser page. Native history, bookmarks, and tab-group information come from
the matching browser profile.

### Native integration boundaries

The implementation was compared with Aside `1.26.1010.2149`. These native-only
operations still require Aside on the Mac because the installed daemon or
extension does not expose an applicable remote operation:

- Granting macOS context-awareness permissions, switching accounts/browser
  profiles, signing out the bridge's current device, or changing the avatar.
- Completing provider/MCP browser OAuth callbacks, managing subscriptions,
  and native Vault/Inbox screens.
- Reordering or automatically organizing browser tabs through restricted
  extension operations, capturing native tab video/audio, and restoring an
  archived project.
- Running project/incognito creation through a remote-host CLI connection;
  these creation paths currently require the local signed daemon.

Installed skills can be read, imported, edited, toggled, and copied for
customization. A remote skill marketplace is not exposed. Browser references
and composer context are sent as readable references rather than native binary
attachment metadata. Multi-key preference changes roll back on a failed write;
the native daemon does not provide a transaction that isolates simultaneous
changes made by another client.

Chat tabs use `sessions.tabs.list` so the parent chat includes its child agents'
owned tabs. Closed targets are omitted. **Show all** follows the browser window's
tab order and excludes browser-internal pages and Aside extension pages. It does
not mix tabs from other windows into the current conversation's browser list.

These integrations rely on Aside's internal behavior rather than a stable
public server API. The bridge uses the installed signed CLI to authorize daemon
operations and can repair some stale browser bindings. Aside updates can still
change CLI/daemon behavior; recheck new chats, continuation, steering, and
browser previews after updating. Keep the daemon local rather than exposing
port 21420. Treat bridge-token access like access to your logged-in browser and
agent tools, not a read-only chat viewer.

## License

This is an independently maintained repository derived from
[aside-remote](https://github.com/esc5221/aside-remote). Original copyright and
license notices are preserved.

MIT, except bundled third-party assets, which retain the licenses listed in
[NOTICE](NOTICE).
