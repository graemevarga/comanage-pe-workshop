# Participant guide

The workshop runs COmanage Registry 5.2.0 on your laptop exactly as the release delivers it: the Registry container
upstream's build script produces, a PostgreSQL container and a mail catcher (Mailpit). Nothing is shared with other
participants, and everything can be reset in a minute. Afterwards you can build the same thing from the release
yourself: see [Running it yourself](at-home.md).

> **Demo only.** For the workshop, anyone who can reach the Registry can log in as its administrator, so the ports are
> only opened on your own laptop (127.0.0.1). Don't change that, and don't put real people's data in it.

## Before the workshop (at home, please)

1. **Install Docker.**
   - macOS (Apple Silicon or Intel) and Windows: [Docker Desktop](https://docs.docker.com/desktop/). On Windows, use the
     WSL 2 backend (the installer's default).
   - Linux: Docker Engine with the Compose plugin (`docker compose version` should work).
   - Docker Desktop is free for personal use, education and small businesses, but professional use at larger
     organisations and government needs a paid subscription; check with your IT department. Rancher Desktop, Colima
     and Podman Desktop are free alternatives, but haven't been tested with this kit yet.
   - Give Docker at least 4 GB of memory and 5 GB of free disk.
   - **Apple Silicon:** the Registry image is built for Intel/AMD (amd64), as the release builds it. Docker Desktop runs
     it under emulation; keep *Settings → General → Use Rosetta for x86_64/amd64 emulation on Apple Silicon* turned on.
2. **Get the workshop files.**
   ```bash
   git clone https://github.com/graemevarga/comanage-pe-workshop.git
   cd comanage-pe-workshop
   ```
   On Windows, run the commands in a WSL terminal (for example Ubuntu) and keep the files in your Linux home
   directory.
3. **Download the images** (the Registry, PostgreSQL and Mailpit):
   ```bash
   docker compose pull
   ```
4. **Try it once**, following "Start" below, then `./workshop reset` or `docker compose down -v`.

## Start

```bash
docker compose up -d
docker compose ps        # wait until the registry service shows (healthy)
```

The first start creates the database and the platform administrator; it takes a few seconds, or a minute or two
under emulation on Apple Silicon.

Open **<https://localhost:8443/registry/>**. The first time, your browser warns that the connection is not private:
the workshop uses a self-signed certificate. Continue anyway:

- Chrome or Edge: **Advanced**, then **Proceed to localhost (unsafe)**.
- Firefox: **Advanced...**, then **Accept the Risk and Continue**.
- Safari: **Show Details**, then **visit this website**, and confirm.

Click **Login**. Your browser asks for a username and password: **username `admin`**, password **empty**. You are
now the platform administrator.

## Logging in as other people

The workshop Registry accepts **any username with an empty password**, and you become whoever that username belongs to:

| Username | Who you are |
|---|---|
| `admin` | The platform administrator (all COs) |
| `ruth.spence`, `rachel.payne`, ... | People loaded from the HR file (from checkpoint `04-filesource-synced` on); their login is their `uid` |
| anything new, e.g. `pat.newcomer` | Someone the Registry doesn't know: you see no COs, but you can sign up through an enrollment flow |

- Use **lowercase**; usernames are case sensitive.
- Your browser remembers the username until you close it. To be someone else, open a **private (incognito) window**,
  or use <https://127.0.0.1:8443/registry/> as a second address (the browser treats it as a different site).

## Email

Every message the Registry sends lands in **Mailpit: <http://localhost:8025/>**. Nothing leaves your laptop. Inside
the workshop, the mail server's name is `mailpit`, port `1025`, no TLS.

## Catching up: checkpoints

If you fall behind, restore the checkpoint for the chapter you're on (your browser session may end; log in again):

```bash
./workshop list
./workshop restore 04-filesource-synced
```

| Checkpoint | What is in it |
|---|---|
| (fresh start) | Only the platform administrator: what `docker compose up -d` gives you the first time |
| `01-email` | Mailpit configured as the outgoing mail server; `admin` has a verified address (`admin@workshop.test`) |
| `02-configuration` | FileConnector and PipelineToolkit plugins active; COs Discovery TNG, Redcurrant University, Guests, MESS |
| `03-connections` | Redcurrant University: pipeline "Process HR API Inputs" and API user `co_3.hr_api_user` |
| `04-filesource-synced` | Redcurrant University: the HR file loaded through a FileSource, 45 people |
| `05-org-structure` | COUs, the Access-wiki group, Lamar Martin, Ruth Spence's role, Claude Larkin in Discovery TNG |
| `06-enrollment` | Discovery TNG self-signup flow "Join Discovery TNG", with email verification through Mailpit |

`./workshop` is a small bash script around `docker compose` (it prints each command it runs). It works on macOS,
Linux, WSL and Git Bash. `./workshop help` lists the rest: `status`, `reset`, `sync`, `cake`, `psql`, `logs`.

From PowerShell, a restore is these commands (replace the name):

```powershell
docker compose cp checkpoints\04-filesource-synced.dump registry-database:/tmp/checkpoint.dump
docker compose exec registry-database dropdb -U registry_user --force registry
docker compose exec registry-database createdb -U registry_user registry
docker compose exec registry-database pg_restore -U registry_user --no-owner -d registry /tmp/checkpoint.dump
docker compose restart registry
```

## Stopping, keeping and throwing away your work

| Command | Effect |
|---|---|
| `docker compose stop` / `docker compose start` | Pause and resume |
| `docker compose down` / `docker compose up -d` | Remove and recreate the containers; the database (a named volume) is kept |
| `./workshop reset` (or `docker compose down -v`, then `up -d`) | Delete the database and start fresh |

## Troubleshooting

- **"port is already allocated"**: another program uses 8443, 8080 or 8025. Copy `.env.example` to `.env`, change
  `HTTPS_PORT`, `HTTP_PORT` or `MAILPIT_PORT`, run `docker compose up -d` again, and use your port in the URLs.
- **"Too many redirects" (ERR_TOO_MANY_REDIRECTS)**: you are logged in as someone who may not see that page. Go back
  to <https://localhost:8443/registry/>, or log out and in as `admin`.
- **The page doesn't load**: `docker compose ps` should show `registry` as `(healthy)`. If it stays `starting` or
  turns `unhealthy`, `docker compose logs registry | tail -50` shows why.
- **"The requested image's platform (linux/amd64) does not match the detected host platform"** on Apple Silicon:
  expected; the Registry runs under emulation.
- **Login box keeps coming back**: type a username; the password may stay empty, but the username may not.
- **Windows**: if `docker` isn't found in WSL, enable WSL integration for your distribution in Docker Desktop
  (Settings, Resources, WSL integration).
- **Conference Wi-Fi**: if you couldn't pull the images beforehand, ask the instructors for a USB copy, then
  `docker load -i <file>` for each.
