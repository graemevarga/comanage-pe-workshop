# Participant guide

In the workshop you run your own COmanage Registry PE 5.2.0 on your laptop and follow along. It is the release as
delivered: the Registry container the upstream build script produces, PostgreSQL, and a mail catcher (Mailpit), all
started with one command. Nothing is shared with other participants, and you can start over at any time.

> **Demo only.** In the workshop Registry, anyone who can reach it can log in as its administrator, so it is only
> reachable from your own laptop (127.0.0.1). Don't change that, and don't put real people's data in it.

## Before the workshop (about 20 minutes, please do it at home)

The first start downloads about 500 MB, which is slow on conference Wi-Fi, so please do this beforehand.

### 1. Install what you need

- **A laptop** with macOS (Apple Silicon or Intel), Windows 10 or 11, or Linux; at least 8 GB of memory and 5 GB of
  free disk. You need administrator rights to install software.
- **Docker.**
  - macOS and Windows: [Docker Desktop](https://docs.docker.com/desktop/). On Windows, keep the installer's default
    (WSL 2); it may ask you to restart.
  - Linux: [Docker Engine](https://docs.docker.com/engine/install/) with the Compose plugin; `docker compose version`
    should work.
  - Docker Desktop is free for personal use, education and small businesses, but professional use at larger
    organisations and government needs a paid subscription; check with your IT department.
  - **Apple Silicon Macs:** the Registry image is built for Intel/AMD, as the release builds it, and Docker Desktop
    runs it under emulation. In Docker Desktop, *Settings → General*, keep **Use Rosetta for x86_64/amd64 emulation on
    Apple Silicon** turned on.
- **Git**, to download the workshop files.
  - macOS: type `git --version` in Terminal; if Git is missing, macOS offers to install it.
  - Windows: [Git for Windows](https://git-scm.com/download/win) (the default options are fine).
  - Linux: your package manager (`sudo apt install git`, `sudo dnf install git`).
  - No Git? On <https://github.com/graemevarga/comanage-pe-workshop>, click **Code → Download ZIP**, unzip it, and
    open the terminal in the unzipped folder instead of the first two commands below.
- **A web browser.**

### 2. Download and start the workshop

Start Docker Desktop (on Linux, the Docker service) and wait until it says it is running. Then open a terminal:
**Terminal** on macOS, **PowerShell** on Windows (Start menu → type "PowerShell"), any terminal on Linux. Run:

```bash
git clone https://github.com/graemevarga/comanage-pe-workshop.git
cd comanage-pe-workshop
docker compose up --wait
```

The last command downloads the images, starts the containers and waits until everything is ready. That takes a few
minutes the first time and a few seconds after that (longer on Apple Silicon Macs, which run the Registry under
emulation). It is done when you get your prompt back and the last lines say `Healthy`.

### 3. Check that it works

1. Open **<https://localhost:8443/registry/>**. Your browser warns that the connection is not private, because the
   workshop uses a self-signed certificate. Continue anyway:
   - Chrome or Edge: **Advanced**, then **Proceed to localhost (unsafe)**.
   - Firefox: **Advanced...**, then **Accept the Risk and Continue**.
   - Safari: **Show Details**, then **visit this website**, and confirm.
2. Click **Login**. Your browser asks for a username and password: type **`admin`** and leave the password
   **empty**. You should see "This is the COmanage CO, which is used for platform wide configurations."
3. Open **<http://localhost:8025/>**: the (empty) mailbox of Mailpit, where the Registry's email will arrive.

### 4. Clear it for the workshop

```bash
docker compose down -v
```

This removes the containers and the database; the downloaded images stay, so on the day the start takes seconds.

If any step fails, see [Troubleshooting](#troubleshooting). If you are still stuck, send the output of
`docker compose ps -a` and `docker compose logs` to the workshop organisers before the workshop.

## At the workshop

Start Docker Desktop, open your terminal, and run:

```bash
cd comanage-pe-workshop
docker compose up --wait
```

Then open <https://localhost:8443/registry/> and log in as `admin` (empty password). If the organisers announce an
update to the workshop files, run `git pull` before `docker compose up --wait`.

## What's in your Registry

A fresh install, plus only what the lesson needs around it. You build everything else yourself during the lesson.

| | |
|---|---|
| **The Registry** | <https://localhost:8443/registry/>. Only the COmanage CO and the platform administrator `admin` exist. The plugins are installed but not active; you activate the ones you need during the lesson. |
| **Mail** | The Registry's outgoing mail already goes to Mailpit, <http://localhost:8025/>. Nothing leaves your laptop. |
| **Files for the FileSource** | `hr.csv` and `registrar.csv` in the `filesource` folder (fictional people). The Registry sees them as `/srv/filesource/hr.csv` and `/srv/filesource/registrar.csv`. |
| **File Provisioner output** | `output.jsonl` in the `provisioned` folder: open it on your laptop to see what the Registry writes (one JSON record per line). The Registry sees it as `/srv/provisioned/output.jsonl`. |
| **SQL Provisioner target** | A separate PostgreSQL database for the Registry to write to: host `target-database`, port 5432, database `target`, username `target_user`, password `password`. |

## Logging in as other people

The workshop Registry accepts **any username with an empty password**, and you become whoever that username belongs
to:

- `admin` is the platform administrator.
- A username the Registry doesn't know yet is a new person: you see no COs, but you can accept an invitation or sign
  up through an enrollment flow.
- Use **lowercase**; usernames are case sensitive.
- Your browser remembers the username until you close it. To be someone else, open a **private (incognito) window**,
  or use <https://127.0.0.1:8443/registry/> as a second address (the browser treats it as a different site).

## Commands you may need

Run them in the `comanage-pe-workshop` folder. They work the same in Terminal, PowerShell and Linux shells.

| To | Run |
|---|---|
| Start, or resume after a pause | `docker compose up --wait` |
| Pause (your work is kept) | `docker compose stop` |
| Start over from a fresh install | `docker compose down -v`, then `docker compose up --wait` |
| Run a full FileSource sync (the lesson gives you the numbers) | `docker compose exec -u www-data -w /srv/comanage-registry/app registry ./bin/cake job -c <CO id> -j CoreJob.SyncJob -s external_identity_source_id=<source id>` |
| Look at the SQL Provisioner's tables | `docker compose exec target-database psql -U target_user -d target` (then `\dt`, and `\q` to quit) |
| See the Registry's log | `docker compose logs registry` |

On macOS, Linux and in Git Bash, `./workshop help` lists shortcuts for some of these; each prints the full command
it runs.

## Troubleshooting

- **"Cannot connect to the Docker daemon"**, **"error during connect"** or **"The system cannot find the file
  specified"**: Docker isn't running. Start Docker Desktop, wait until it says it is running, and try again.
- **"port is already allocated"**: another program uses port 8443, 8080 or 8025. Copy `.env.example` to `.env`,
  change `HTTPS_PORT`, `HTTP_PORT` or `MAILPIT_PORT`, run `docker compose up --wait` again, and use your port in the
  addresses.
- **`docker compose up --wait` ends with "unhealthy" or "didn't complete successfully"**: run
  `docker compose logs registry` (or `docker compose logs workshop-setup`) and send the output to the organisers.
  `docker compose down -v` and `docker compose up --wait` starts over.
- **Downloads fail** (for example "denied" or a timeout from `ghcr.io`): a VPN or corporate proxy may block GitHub's
  container registry. Try again off the VPN or on another network.
- **Apple Silicon: "The requested image's platform (linux/amd64) does not match the detected host platform"**:
  expected; the Registry runs under emulation.
- **"Too many redirects" (ERR_TOO_MANY_REDIRECTS)**: you are logged in as someone who may not see that page. Go back
  to <https://localhost:8443/registry/>, or log out and in as `admin`.
- **The login box keeps coming back**: type a username; the password may stay empty, but the username may not.
- **Linux: "the Registry cannot write provisioned/output.jsonl"**: run
  `chmod 0777 provisioned && chmod 0666 provisioned/output.jsonl`, then `docker compose up --wait`.
- **Windows, Git Bash**: use PowerShell for the commands above. Git Bash changes arguments that look like paths
  (`/srv/...`), which breaks them; `./workshop` handles that for you.

## After the workshop

To remove everything, including the downloaded images: `docker compose down -v --rmi all`, then delete the
`comanage-pe-workshop` folder. To build and run the same Registry in your own environment, see
[Running it yourself](at-home.md).
