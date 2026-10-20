# Participant guide

Everything you need for the hands-on part of the COmanage Registry PE workshop runs in one Docker container on
your laptop: COmanage Registry 5.2.0, its PostgreSQL database, a mail catcher (Mailpit) and the sample data. Nothing
is shared with other participants and you can't break anything you can't reset in a minute.

> **Demo only.** Anyone who can reach the Registry can log in as its administrator, so the ports are only opened on
> your own laptop (127.0.0.1). Don't change that, and don't put real people's data in it.

## Before the workshop (at home, please)

1. **Install Docker.**
   - macOS (Apple Silicon or Intel) and Windows: [Docker Desktop](https://docs.docker.com/desktop/). On Windows, use the
     WSL 2 backend (the installer's default).
   - Linux: Docker Engine with the Compose plugin (`docker compose version` should work).
   - Docker Desktop is free for personal use, education and small businesses, but professional use at larger
     organisations and government needs a paid subscription; check with your IT department. Rancher Desktop, Colima
     and Podman Desktop also work.
   - Give Docker at least 2 GB of memory and 3 GB of free disk. The container itself uses about 150 MB of memory.
2. **Get the workshop files.**
   ```bash
   git clone https://github.com/graemevarga/comanage-pe-workshop.git
   cd comanage-pe-workshop
   ```
   No git? Download the ZIP from the GitHub page and unzip it. On Windows, run the commands in a WSL terminal
   (for example Ubuntu) and keep the files in your Linux home directory, or use PowerShell.
3. **Download the image** (about 300 MB; it picks the right one for Apple Silicon, Intel or AMD automatically):
   ```bash
   docker compose pull
   ```
4. **Try it once**, following "Start" below, then stop it with `docker compose down`.

## Start

```bash
docker compose up -d
docker compose ps        # wait until STATUS shows (healthy), about ten seconds
```

Open **<https://localhost:8443/registry-pe/>**.

The first time, your browser warns that the connection is not private: the container uses a self-signed
certificate. Continue anyway:

- Chrome or Edge: **Advanced**, then **Proceed to localhost (unsafe)**.
- Firefox: **Advanced...**, then **Accept the Risk and Continue**.
- Safari: **Show Details**, then **visit this website**, and confirm.

Click **Login**. Your browser asks for a username and password:

- **Username: `admin`**, password: **leave it empty**. You are now the platform administrator.

## Logging in as other people

The workshop Registry accepts **any username with an empty password**, and you become whoever that username belongs to:

| Username | Who you are |
|---|---|
| `admin` | The platform administrator (all COs) |
| `ruth.spence`, `rachel.payne`, ... | People loaded from the HR file (after checkpoint `04-filesource-synced`); their login is their `uid` |
| anything new, e.g. `pat.newcomer` | Someone the Registry doesn't know yet: you see no COs, but you can sign up through an enrollment flow |

Tips:

- Use **lowercase**; usernames are case sensitive.
- Your browser remembers the username until you close it. To be someone else, open a **private (incognito) window**,
  or use <https://127.0.0.1:8443/registry-pe/> as a second address (the browser treats it as a different site).
- **Logout** ends your Registry session, but the browser may still log you in as the same person next time; close
  the private window to switch.

## Email

Every message the Registry sends lands in **Mailpit: <http://localhost:8025/>**. Nothing leaves your laptop.

## Catching up: checkpoints

If you fall behind or want to start a chapter fresh, restore the checkpoint for the chapter you're on. Your browser
session ends, so log in again afterwards.

```bash
docker compose exec registry workshop restore 04-filesource-synced
```

| Checkpoint | What is in it |
|---|---|
| `01-fresh` | The state you start in: platform admin `admin` (email `admin@workshop.test`), Mailpit configured as the outgoing mail server |
| `02-configuration` | FileConnector and PipelineToolkit plugins active; COs Discovery TNG, Redcurrant University, Guests, MESS |
| `03-connections` | Redcurrant University: pipeline "Process HR API Inputs" and API user `co_3.hr_api_user` |
| `04-filesource-synced` | Redcurrant University: the HR file loaded through a FileSource, 45 people |
| `05-org-structure` | COUs, the Access-wiki group, Lamar Martin, Ruth Spence's role, Claude Larkin in Discovery TNG |
| `06-enrollment` | Discovery TNG self-signup flow "Join Discovery TNG", with email verification through Mailpit |

Other useful commands (put `docker compose exec registry` in front of each):

| Command | What it does |
|---|---|
| `workshop list` | List the checkpoints (`*` marks the last one restored) |
| `workshop reset` | Back to the start (`01-fresh`) |
| `workshop status` | Is everything running? |
| `workshop sync 3 1` | Load the whole HR file now (full sync of External Identity Source 1 in CO 3) |
| `workshop help` | Everything else |

## Stopping, keeping and throwing away your work

| Command | Effect |
|---|---|
| `docker compose stop` and later `docker compose start` | Pauses; everything you did is kept |
| `docker compose down` | Throws the container away; the next `docker compose up -d` starts fresh |

## Troubleshooting

- **"port is already allocated"** when starting: another program uses 8443, 8080 or 8025. Copy `.env.example` to
  `.env`, change `HTTPS_PORT`, `HTTP_PORT` or `MAILPIT_PORT`, then `docker compose up -d` again and use your new port
  in the URLs.
- **"Too many redirects" (ERR_TOO_MANY_REDIRECTS)**: you are logged in as someone who may not see that page. Go back
  to <https://localhost:8443/registry-pe/>, or log out and in as `admin`.
- **The page doesn't load**: `docker compose ps` should say `(healthy)`. If not, `docker compose logs registry | tail -50`
  shows why; `docker compose down && docker compose up -d` starts over.
- **Login box keeps coming back**: type a username; the password may stay empty, but the username may not.
- **Windows**: if `docker` isn't found in WSL, enable WSL integration for your distribution in Docker Desktop
  (Settings, Resources, WSL integration).
- **Apple Silicon**: the image runs natively; no Rosetta needed.
- **Conference Wi-Fi**: if you couldn't pull the image beforehand, ask the instructors for a USB copy, then run
  `docker load -i comanage-pe-workshop-<arch>.tar`.
