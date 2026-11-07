# ANNAMALAI — Personal Digital Universe

A database-driven Flask portfolio built as a single, long-form archive. The
public site combines a **TVA Archive**, **Digital Universe** and **Cinematic
Editorial** visual language: timeline coordinates, archive plates, scanlines,
film grain, oversized typography and a control-room terminal. Every piece of
public content is stored in SQLite and can be edited from the protected admin
dashboard.

The project runs entirely locally and makes no third-party network requests at
runtime. Fonts, GSAP/ScrollTrigger, icons and other assets are vendored in the
repository.

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Setup](#setup)
- [Run the application](#run-the-application)
- [The Tempad puzzle](#the-tempad-puzzle)
- [Admin access](#admin-access)
- [Content management](#content-management)
- [Configuration](#configuration)
- [Custom commands](#custom-commands)
- [Security notes](#security-notes)
- [Testing report](#testing-report)
- [Known limitations](#known-limitations)

---

## Features

### Public archive

- Single-page archive with these sections, in order:
  `HOME → ABOUT → ACHIEVEMENTS → TEAMS → PROJECTS → PEOPLE → GALLERY → CONTROL → CONTACT`
- Cinematic hero with scroll and reveal animations, optional uploaded background,
  archive-code typography and generated temporal-artifact artwork.
- About section with editable biography, philosophy and optional portrait.
- Achievements with placement, year, certificate/event images and an accessible
  image viewer.
- Organizations/teams with role, description, optional logo and website link.
- Featured and secondary projects with cover images, galleries, captions,
  technology lists and external/GitHub links.
- Collaborator constellation with optional photographs and websites.
- Gallery categories with multi-image upload, captions, descriptions and an
  accessible lightbox (keyboard navigation, focus management, Escape to close).
- Live archive telemetry derived from the database: project, achievement,
  organization, collaborator and gallery counts. No invented statistics.
- Contact transmission form with CSRF protection, validation, honeypot,
  per-IP throttling and database-backed inbox.
- Footer, archive clock, audio-less motion design and responsive navigation.
- Eight seeded hidden interactions (artifact, margin notes, timeline marks,
  constellation record, unseen frame, terminal frequency, footer signal and
  terminal handshake). Messages and visibility are editable in the dashboard.
- **Tempad secret terminal** with an ADW identity mark, a Miss Minutes-style
  clock, live time, moving eyes and hands, rotating dialogue, command shortcuts
  and keyboard history.
- **Sealed ARCHIVE CONTROL section.** The console does not open from a public
  button. Four access fragments are hidden inside Easter-egg records; visitors
  read each code and submit it in the Tempad with `UNLOCK <code>`. All published
  fragments unlock the console automatically, and progress survives reloads via
  `localStorage`. `RELOCK` re-seals the door.
- Reduced-motion support, lazy-loaded images, skip links, semantic landmarks,
  visible focus states and keyboard-operable overlays.
- Self-hosted fonts (Anton, Barlow Condensed, Space Mono, Inter, Cormorant
  Garamond, Caveat), Lucide SVG sprite and GSAP/ScrollTrigger.

### Control room (admin)

- Protected dashboard with real database counts and recent activity.
- Sidebar sections: **Overview, Profile, Achievements, Organizations, Projects,
  Collaborators, Gallery, Easter Eggs, Appearance, Messages, Account, Logout**.
- Full create/edit/delete/reorder flows for every public collection.
- Image uploads for portraits, certificates, event photos, logos, project covers,
  project galleries, collaborator photos, gallery images and the hero background.
- Individual image-removal actions that also delete the stored file.
- Appearance editor for site copy, section headings, hero copy, colors, section
  visibility, animations, grain and scanlines.
- Contact inbox with read/unread state, filters, read-all and delete actions.
- Account renaming and password change.
- Forced password change on first login; the control room remains locked until
  the initial password is replaced.
- CSRF protection on all state-changing requests, hashed passwords, login
  throttling and safe post-login redirects.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.13 (compatible with Python 3.11+) |
| Web framework | Flask 3.1 |
| ORM / database | Flask-SQLAlchemy + SQLite |
| Authentication | Flask-Login |
| Forms / CSRF | Flask-WTF |
| Password hashing | Werkzeug `generate_password_hash` (scrypt) |
| Image processing | Pillow |
| Templates | Jinja2 |
| Front end | HTML5, CSS3, vanilla JavaScript |
| Animation | GSAP 3.12.5 + ScrollTrigger (vendored) |
| Icons | Lucide static SVG sprite (vendored) |
| Fonts | Locally hosted WOFF2 files |
| Tests | Python `unittest` |

No React, Vue, Angular, Next.js, Java, paid service, CDN or remote API is used.

---

## Project structure

```text
PythonProject4/
├── app/
│   ├── __init__.py            # App factory, context/filters, security headers
│   ├── commands.py            # init-db, create-admin, set-admin-password
│   ├── extensions.py          # SQLAlchemy, LoginManager, CSRF, Migrate
│   ├── forms.py               # Public and admin WTForms
│   ├── models.py              # 12 database models and relationships
│   ├── schema.py              # Idempotent additive SQLite upgrades
│   ├── seed.py                # Idempotent initial archive content + fragments
│   ├── utils.py               # Upload validation/storage, helpers, throttling
│   ├── routes/
│   │   ├── main.py            # Public page, media serving, API, health check
│   │   ├── admin.py           # Control room, auth, CRUD, appearance, messages
│   │   └── contact.py         # Contact submission endpoint
│   ├── templates/
│   │   ├── base.html          # Public shell, navigation, overlays
│   │   ├── index.html         # Public archive composition
│   │   ├── sections/          # Hero, about, achievements, teams, projects,
│   │   │                      # people, gallery, control, contact, footer
│   │   ├── admin/             # Dashboards, lists, forms, login, account
│   │   ├── partials/          # Lightbox, terminal, secret modal
│   │   ├── macros/            # Public icon helper
│   │   └── errors/            # Error page
│   └── static/
│       ├── css/main.css       # Public design system
│       ├── css/admin.css      # Control-room design system
│       ├── js/main.js         # Navigation, animation, lightbox, terminal, eggs
│       ├── js/admin.js        # Sidebar, previews, confirmations, color sync
│       ├── js/theme-init.js   # Pre-paint theme values
│       ├── fonts/             # 28 local WOFF2 faces + fonts.css
│       ├── vendor/            # GSAP, ScrollTrigger, Lucide sprite
│       └── images/            # Favicon and generated design assets
├── tests/
│   └── test_app.py            # 16 end-to-end and CSRF regression tests
├── uploads/                   # Owner uploads, outside static/
│   ├── profiles/              # Portraits and collaborator photos
│   ├── achievements/          # Certificates and event images
│   ├── organizations/         # Logos
│   ├── projects/              # Covers and project gallery frames
│   ├── gallery/               # Gallery images
│   └── site/                  # Hero background
├── .env                       # Local secrets/configuration (not committed)
├── .env.example               # Documented environment template
├── .gitignore
├── annamalai.db               # SQLite database (generated)
├── config.py                  # Base/testing/production configuration
├── requirements.txt           # Pinned Python dependencies
└── run.py                     # Local entry point
```

---

## Setup

### Requirements

- Python 3.11 or newer (tested on Python 3.13.4)
- pip
- Windows, macOS or Linux

### 1. Open the project

```powershell
cd C:\Users\Dell\PycharmProjects\PythonProject4
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create the environment file

Copy `.env.example` to `.env` and set at least a strong `SECRET_KEY`:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(48))"
```

Paste the generated value into `SECRET_KEY`. The workspace already contains a
local `.env` and an initialized `annamalai.db`; you only need this step on a
fresh checkout.

### 5. Initialize / seed the database

The app auto-bootstraps when `AUTO_BOOTSTRAP=1` in `.env` and the database is
empty. To initialize explicitly:

```powershell
python -m flask --app run.py init-db
```

This creates the tables, the initial administrator, and the supplied archive
content. Existing records are never overwritten. Seeded long biography copy is
clearly editable placeholder prose; only the names, placements, organizations,
project link and collaborator links supplied by the owner are treated as facts.

To rebuild from scratch, delete `annamalai.db` and the contents of `uploads/`,
then run `init-db` again. This is destructive.

---

## Run the application

```powershell
.\.venv\Scripts\Activate.ps1
python run.py
```

Or without activating:

```powershell
.\.venv\Scripts\python.exe run.py
```

Open:

| Surface | URL |
| --- | --- |
| Public archive | <http://127.0.0.1:5000> |
| Admin login | <http://127.0.0.1:5000/admin/login> |
| Archive JSON snapshot | <http://127.0.0.1:5000/api/archive> |
| Health check | <http://127.0.0.1:5000/healthz> |

The development server binds to `127.0.0.1` by default. Set `HOST=0.0.0.0` and
`PORT=5000` only if you intentionally want to expose it on the local network.

---

## The Tempad puzzle

The CONTROL section is a sealed door. It never renders its console until the
visitor has recovered every published access fragment. This is a narrative game
layer, **not** an authentication or security boundary (see
[Security notes](#security-notes)).

### How visitors play

1. Explore the public archive and open the floating hidden-record nodes. Seeded
   records are the artifact in the hero, the margin note in About, the timeline
   mark in Achievements, the unseen frame in Gallery and the footer signal.
2. The hidden-record overlay reveals its **ACCESS FRAGMENT** and the exact
   terminal command to use.
3. Open the Tempad with `CTRL + SHIFT + A`, the terminal buttons, or the Tempad
   link in the hidden-record overlay.
4. Type `UNLOCK <fragment>` for each code, for example `UNLOCK ORIGIN`.
5. When every published fragment is recovered, the Tempad opens the ARCHIVE
   CONTROL console automatically. The complete key is stored in `localStorage`
   under `annamalai-archive-access`.
6. `RELOCK` clears the recovered fragments and re-seals the door. Removing site
   data or using a different browser also resets the puzzle.

### Seeded fragments

| Slot | Code | Hidden record | Section |
| --- | --- | --- | --- |
| 1 | `ORIGIN` | MARGIN NOTE / UNFILED | About |
| 2 | `SIGNAL` | TIMELINE MARK / UNLOGGED | Achievements |
| 3 | `ECHO` | UNSEEN FRAME / NO CAPTION | Gallery |
| 4 | `VARIANT` | FOOTER SIGNAL / CARRIER | Footer |

### Terminal commands

| Command | Purpose |
| --- | --- |
| `HELP` | List every command, including the firewall commands |
| `FRAGMENTS` | Show the fragment ledger and recovery progress |
| `UNLOCK <code>` | Submit one fragment (multiple codes may be submitted on one line) |
| `SCAN` | List every fragment's section and hidden-record title |
| `HINT` | Point at the next missing fragment |
| `OPEN CONTROL` | Open the console once the key is complete; emergency access when no fragments are published |
| `RELOCK` | Clear the recovered fragments and re-seal the console |
| `MISS` | Ask Miss Minutes for a line |
| `ABOUT`, `PROJECTS`, `TIMELINE`, `TEAMS`, `PEOPLE`, `GALLERY`, `STATS`, `EGG`, `CONTACT`, `DATE`, `LS`, `CLEAR`, `EXIT` | Existing archive queries and terminal controls |

All fragment data is rendered from the database into the sealed door and the
hidden-record nodes. The public JavaScript only compares submitted codes with
that published configuration.

### Editing fragments

In **Easter Eggs**, each record has two extra fields:

- **ACCESS CODE** — up to 24 characters, normalized to uppercase; letters,
  numbers, hyphens and underscores only.
- **FRAGMENT SLOT (0–4)** — `1`–`4` publishes the code as a fragment; `0` keeps
  the record outside the puzzle.

A code and slot must be supplied together, and both must be unique. Slots do not
have to be contiguous, but the console counts and displays only published
fragments. Leave all slots at `0` to remove the puzzle; `OPEN CONTROL` then grants
emergency access so the console is never unreachable.

Existing databases created before the puzzle was added are upgraded in place.
`init-db` and app startup call `app/schema.py`, which adds the two missing
`easter_eggs` columns without rewriting any content. The four seeded records are
backfilled only when the upgrade first adds the columns.

---

## Admin access

A freshly seeded database creates this bootstrap administrator:

```text
Username: futuremusic
Password: sucess
```

**On a fresh database the first login is forced to `/admin/change-password`.**
The dashboard remains unavailable until the password is replaced. The new
password must be at least 8 characters and contain at least one letter and one
number.

The `annamalai.db` in this workspace has already completed that rotation, so the
seed password no longer applies. Use the password set during setup. If it is
lost, reset it from the server console:

```powershell
python -m flask --app run.py set-admin-password --username futuremusic
```

The command prompts for the new password. There is intentionally no email-based
password recovery.

To create an additional administrator:

```powershell
python -m flask --app run.py create-admin
```

---

## Content management

| Public area | Control-room page | What can be edited |
| --- | --- | --- |
| Hero, copy, colors, visibility | Appearance | Site title/subtitle, archive code, meta description, every section heading and intro, hero lines, footer notes, all theme colors, section toggles, animations, grain, scanlines, hero background |
| About | Profile | Name, role line, tagline, intro, biography, philosophy, focus areas, location, email, phone, social URLs, portrait |
| Achievements | Achievements | Title, position, year, description, order, certificate image, event image |
| Teams | Organizations | Name, role, description, website, order, logo |
| Projects | Projects | Title, tagline, summary, long description, tech stack, links, featured flag, order, cover, gallery images and captions |
| People | Collaborators | Name, description, website, order, photo |
| Gallery | Gallery | Categories, category descriptions and order, multi-image uploads, captions, descriptions, image order |
| Hidden interactions | Easter Eggs | Key, title, message, section, interaction type, access-fragment code and slot, enabled flag, order |
| Contact inbox | Messages | Filter read/unread, mark read/unread, read all, delete |
| Account | Account | Rename administrator, change password |

All public text is read from the database. Images are processed and stored under
`uploads/`; replacing or removing an image deletes the previous file.

---

## Configuration

Environment variables are read from `.env` via `python-dotenv`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | development fallback | Session and CSRF signing key. Required outside debug mode. |
| `DATABASE_URL` | `sqlite:///annamalai.db` | SQLAlchemy database URI. |
| `ADMIN_USERNAME` | `futuremusic` | Bootstrap administrator username. |
| `ADMIN_PASSWORD` | `sucess` | Bootstrap administrator password; forced to change on first login. |
| `AUTO_BOOTSTRAP` | `1` | Create tables and seed content when the database is empty. |
| `FLASK_DEBUG` | `0` | Flask debug/reloader toggle. Keep `0` for normal use; use `1` only while developing locally. |
| `MAX_UPLOAD_MB` | `16` | Per-request upload limit. |
| `UPLOAD_FOLDER` | `<project>/uploads` | Absolute or relative upload storage path. |
| `SESSION_COOKIE_SECURE` | `0` | Set to `1` when serving over HTTPS. |
| `REMEMBER_COOKIE_SECURE` | `0` | Set to `1` when serving over HTTPS. |
| `SITE_TIMEZONE` | `Asia/Kolkata` | Display timezone for the archive clock. |
| `HOST` | `127.0.0.1` | Development bind address. |
| `PORT` | `5000` | Development port. |

---

## Custom commands

```powershell
# Create tables and seed initial content
python -m flask --app run.py init-db

# Create tables only, without seed content
python -m flask --app run.py init-db --no-seed

# Create an additional administrator (prompts, hashes password)
python -m flask --app run.py create-admin

# Reset an administrator password from the console
python -m flask --app run.py set-admin-password --username futuremusic
```

---

## Security notes

- Passwords are hashed with Werkzeug's scrypt implementation; plaintext passwords
  are never stored.
- All state-changing forms include Flask-WTF CSRF tokens. Requests with missing
  or invalid tokens are rejected.
- The admin blueprint is protected by Flask-Login and a blueprint-level guard.
  Unauthenticated requests are redirected to the login page; authenticated users
  with `must_change_password=True` can only reach the password-change page.
- Login attempts are limited to 6 failures per 10 minutes per client; contact
  submissions are limited to 8 per 5 minutes per client. Both limiters are
  in-memory and reset when the process restarts.
- The contact form includes a hidden honeypot field and server-side validation.
- Uploads are restricted to JPG, JPEG, PNG and WEBP, verified as real images with
  Pillow, capped by size and dimension, renamed with random UUIDs, and stored
  outside `static/`. The media route only serves known upload folders and rejects
  path traversal and non-image extensions.
- Requests for dotfiles, source-like extensions (`.py`, `.db`, `.env`, `.md`,
  `.map`, archives and secrets) and project directories are rejected with a 404
  before routing. `/static/` serves only whitelisted asset types such as CSS,
  JavaScript, SVG, images and fonts; raw docs and source maps are not exposed.
- Flask debug mode and the reloader are off by default, so tracebacks and
  interactive debugger pages are not rendered to visitors. Keep
  `FLASK_DEBUG=0` except during local development.
- Responses include a Content Security Policy, `X-Content-Type-Options:
  nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` and a
  same-origin resource policy.
- Session cookies are HTTP-only and `SameSite=Lax`. Enable the secure-cookie
  flags when deploying behind HTTPS.
- Secrets live in `.env`, which is excluded by `.gitignore`. Replace the
  bootstrap password and generate a fresh `SECRET_KEY` before any deployment.
- **HTML, CSS and JavaScript must be delivered to the browser, so their source
  cannot be made undiscoverable.** The request guard protects server-side source,
  templates, the database and environment files; it does not hide frontend code.
  Never place credentials or private records in client-side files.
- **The Tempad fragment gate is a narrative experience, not a security
  boundary.** Fragment codes are delivered to the browser so the terminal can
  validate them locally; anyone can inspect the page source, edit `localStorage`
  or call the DOM directly. The admin dashboard, uploads and mutations remain
  protected by Flask-Login, CSRF and server-side authorization. Do not hide
  sensitive data in the puzzle.

---

## Testing report

**Test date:** 2 November 2026
**Environment:** Windows, Python 3.13.4, local SQLite, headless Google Chrome.

### Automated regression suite

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Result: **17 tests passed, 0 failures, 0 errors.**

Coverage includes:

1. Public archive rendering, section IDs, archive JSON, health check, 404s and
   upload path-traversal rejection.
2. Login, forced password rotation, wrong-current-password rejection and weak
   password rejection.
3. Profile editing, portrait upload/serving, upload-preservation regression and
   portrait deletion.
4. Achievement CRUD, certificate/event uploads, image deletion and reordering.
5. Organization CRUD, logo upload/preservation/deletion.
6. Project CRUD, cover and multi-image uploads, captions, reordering, featured
   toggle, image deletion and cascade cleanup.
7. Collaborator CRUD, photo upload/preservation/deletion.
8. Gallery category CRUD, multi-image upload, caption/description editing,
   reordering and cascade deletion.
9. Easter egg CRUD, enable/disable toggle and ordering.
10. Seeded access fragments, fragment slot/code uniqueness validation, fragment
    creation through the admin, and rendering of the sealed door, fragment config
    and unlocked console markers on the public page.
11. Appearance persistence, hero-background upload, no-file preservation
    regression, live theme/CSS variable output, section toggles, color validation
    and background deletion.
12. Contact submission, honeypot rejection, inbox filtering, read/unread,
    read-all and deletion.
13. Account rename, logout guard and re-login with the new username.
14. Upload extension spoofing and invalid-image rejection.
15. Login throttling.
16. CSRF rejection without a token and acceptance with a valid token.
17. Source-exposure guards: dotfiles, project source, the SQLite database,
    Markdown/source maps and traversal paths return 404, while approved CSS, JS,
    SVG and font assets remain reachable and non-image uploads stay private.

The suite uses an isolated temporary SQLite database and upload directory. It
never modifies the real `annamalai.db` or `uploads/` contents.

### Browser / visual audit

A temporary Chrome DevTools Protocol harness audited 23 public and admin pages
at 1440 × 1000 desktop and 390 × 844 mobile. The temporary harness was removed
after the audit.

Result:

- **0 console errors or uncaught exceptions**
- **0 horizontal overflows**
- **0 missing or broken images**
- **0 empty image `src` requests**
- Section order confirmed as `home, about, achievements, teams, projects, people,
  gallery, control, contact`
- Public mobile menu opens, exposes links and closes correctly
- Admin mobile sidebar opens with all navigation links
- Admin login, forced password change, dashboard, all ten management pages,
  project form and appearance form render successfully
- JavaScript syntax checks pass for both `main.js` and `admin.js`

### Tempad and sealed-control audit

A second temporary CDP harness exercised the complete puzzle on the running
application at 1440 × 1000 and 390 × 844.

Result: **53 functional checks passed, 0 failures, 0 console errors.**

- Sealed gate, four fragments and four slots render from the database.
- Hidden-record overlay reveals `ORIGIN`, its slot and the exact `UNLOCK` command.
- “Open Tempad” closes the record and opens the terminal.
- Miss Minutes clock, live time, dialogue, hands and fragment HUD update.
- `UNLOCK ORIGIN`, `UNLOCK SIGNAL`, `UNLOCK ECHO` and `UNLOCK VARIANT` each
  register, persist to `localStorage` and update the sealed door.
- The fourth fragment closes the Tempad and opens the console automatically.
- The console shows live database records, six panels and an online status.
- Reload preserves the unlock; `CTRL + SHIFT + A` reopens the Tempad.
- `RELOCK` clears progress, re-seals the gate and restores
  `CONSOLE / SEALED`.
- Desktop and mobile layouts fit their viewports with no horizontal overflow.
- Reduced-motion mode renders the sealed gate without errors.

Screenshots of the sealed gate, fragment overlay, Tempad, unlocked console and
mobile layouts were inspected. Temporary QA scripts and screenshots were
removed after the audit.

### Mobile optimization audit

A third temporary CDP harness checked the public archive at 320 × 568,
360 × 640, 390 × 844, 414 × 896, 844 × 390 landscape, 320 × 480 short viewport
and 1440 × 900 desktop.

Result:

- **0 console errors, uncaught exceptions or horizontal overflows.**
- Mobile navigation opens with 62px links and a 44px close target; the panel
  scrolls safely on short screens.
- The mobile menu, terminal and hidden-record overlays respect safe-area insets
  and dynamic viewport heights (`dvh`).
- Public form fields and the Tempad input render at 16px on mobile to prevent
  iOS focus zoom.
- Terminal quick commands use a readable 3 × 2 grid with 42–44px targets; the
  terminal stays inside the viewport in portrait, landscape and short-viewport
  modes.
- The fragment board switches from four columns to a roomier 2 × 2 grid on
  phones, and all visible console buttons meet a 44px minimum target.
- The hidden-record dialog fits at 320px wide without overflow and scrolls when
  landscape height is constrained.
- The Tempad identity mark renders **ADW** at every tested width.

### Manual checks

- Desktop and mobile screenshots inspected for the public hero, about,
  achievements, teams, projects, people, gallery, control, contact, mobile menu
  and admin login/dashboard/appearance/project form.
- Upload previews, image deletion, section toggles and admin navigation exercised.
- Lightbox, hidden-record modal, Tempad terminal and mobile navigation are
  keyboard-operable and restore focus.
- Terminal command history, quick commands, `HELP`, `SCAN`, `HINT`,
  `FRAGMENTS`, `OPEN CONTROL` and `RELOCK` were exercised in the browser.

---

## Known limitations

- **SQLite is intended for local/single-instance use.** For production traffic,
  migrate to PostgreSQL or MySQL and use a production WSGI server such as
  Waitress or Gunicorn behind HTTPS.
- **No email delivery.** Contact messages are stored in the database and read in
  the control room; no SMTP notification is sent.
- **Local disk storage.** Uploads are not replicated to object storage or a CDN.
  Back up `annamalai.db` and `uploads/` together.
- **In-memory throttling.** Login and contact rate limits are per process and
  reset on restart. A multi-worker deployment needs shared rate limiting.
- **No automated password recovery.** Recovery requires server-console access via
  `set-admin-password`; this is deliberate.
- **No fabricated visual records.** Gallery categories are seeded empty and no
  portraits, certificates, project screenshots or logos are invented. Those
  areas remain in an intentional "awaiting record" state until the owner uploads
  real media.
- **Seed biography is editable placeholder prose.** It avoids inventing specific
  personal facts and should be replaced from the admin profile page.
- **No checked-in visual-regression suite.** The browser audit was a temporary
  verification harness; the persistent automated suite is `tests/test_app.py`.
- **Accessibility was verified manually and structurally, not with an automated
  audit tool such as axe.** Modern evergreen browsers are the supported target.
- **The Tempad gate is not a security control.** Fragment codes are published in
  the page and validated in the browser; `localStorage` can be edited. It is a
  narrative puzzle and should never protect private records. Admin
  authentication remains the only real access boundary.
- **Frontend source is always retrievable.** A browser must download HTML, CSS
  and JavaScript to run the site. The server-side guard prevents source files,
  databases, environment files and raw docs from being served, but it cannot
  hide the code that reaches the client.
- **Puzzle progress is per browser.** Clearing site data, using private browsing
  or switching devices resets recovered fragments and re-seals the console.
- **The development server is not production-ready.** Do not expose `run.py`
  directly to the internet.

---

Built as a living archive: every public record is database-driven, and every
control in the dashboard writes to a real record.
