# COmanage Registry PE 5.2.0 workshop

A hands-on environment for COmanage Registry PE (v5) that runs on your laptop with one command. It is the
**delivered project, not a special workshop build**: the Registry image is the one the upstream 5.2.0 release builds
with its own `container/build.sh` (basic-auth variant, unmodified), configured only through upstream's documented
environment variables, next to standard PostgreSQL and Mailpit containers. What you do here is what you'll do at
home; see [Running it yourself](docs/at-home.md).

> **Demo only.** The workshop's one customisation is anonymous login: anyone who can reach the Registry can log in
> as the platform administrator. The ports are published on 127.0.0.1 only; keep it that way and use only fictional
> data.

## Quick start

You need Docker (Docker Desktop on macOS and Windows, Docker Engine with Compose on Linux) and Git. Then, in a
terminal (Terminal on macOS, PowerShell on Windows):

```bash
git clone https://github.com/graemevarga/comanage-pe-workshop.git
cd comanage-pe-workshop
docker compose up --wait
```

The first run downloads about 1.5 GB of images. When the command returns, everything is ready:

- **Registry:** <https://localhost:8443/registry/>. Accept the self-signed certificate, click **Login**, type
  username **`admin`** and leave the password empty.
- **Mail:** <http://localhost:8025/> (Mailpit). Everything the Registry sends lands here.

Participants: the [participant guide](docs/participant-guide.md) has the full instructions, including what to do
before the workshop.

## What you get

A fresh install, plus only what the lesson needs around it. Everything else you build yourself during the lesson.

| | |
|---|---|
| Registry | Upstream's first start: the COmanage CO and the platform administrator `admin`. Plugins are installed but not active; you activate them during the lesson. |
| Mail | The Registry's outgoing mail already goes to Mailpit (an Outgoing SMTP Server on the COmanage CO, host `mailpit`, port 1025) |
| FileSource input | `filesource/hr.csv` and `filesource/registrar.csv` (fictional people, CSV v3), at `/srv/filesource/` in the Registry |
| File Provisioner output | The `provisioned/` folder, at `/srv/provisioned/` in the Registry |
| SQL Provisioner target | A separate PostgreSQL database: host `target-database`, database `target`, user `target_user`, password `password` |

## What is running

| Service | Image | Role |
|---|---|---|
| `registry` | `ghcr.io/graemevarga/comanage-registry:5.2.0-basic-auth-1`: upstream's 5.2.0 basic-auth image, built by [this repository's workflow](.github/workflows/publish.yml) with upstream's `build.sh` | COmanage Registry (Apache + PHP), at `/registry/` |
| `registry-database` | `postgres:17` | The Registry database (named volume `registry-database`) |
| `target-database` | `postgres:17` | Stands in for an application database the SQL Provisioner writes to |
| `mailpit` | `axllent/mailpit` | Catches outgoing mail; stands in for your SMTP relay |
| `workshop-setup` | `postgres:17` | Runs once after the Registry's first start ([setup/setup.sh](setup/setup.sh)), then exits |

How the workshop configures them, and what you would change for production, is in
[How it maps to a real deployment](docs/design-notes.md).

## Logging in

Any username works with an empty password, and you become whoever that username belongs to: `admin` is the
platform administrator, and a name the Registry doesn't know yet is a new person, who can accept an invitation or
sign up through an enrollment flow. Use a private browser window per person.

## Everyday commands

Run them in the `comanage-pe-workshop` folder.

| | |
|---|---|
| `docker compose up --wait` | Start (or resume) and wait until ready |
| `docker compose stop` | Pause; your work is kept |
| `docker compose down -v`, then `docker compose up --wait` | Start over from a fresh install |
| `docker compose logs registry` | The Registry's log |

On macOS, Linux, WSL and Git Bash, `./workshop help` lists optional shortcuts (FileSource syncs, saving and
restoring the database); each prints the `docker compose` command it runs.

## Documentation

- [Participant guide](docs/participant-guide.md): before the workshop, starting, logging in, troubleshooting.
- [Notes for the lesson plan](docs/lesson-plan-notes.md): what participants start with, and how 5.2.0 behaves in the
  areas the lesson covers.
- [Instructor guide](docs/instructor-guide.md): preparing and presenting, procedures verified on 5.2.0, checking the
  lesson plan, known 5.2.0 traps.
- [How it maps to a real deployment](docs/design-notes.md): every setting, and what changes in production.
- [Running it yourself](docs/at-home.md): build the 5.2.0 images from the release and deploy them.

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). COmanage Registry is © University Corporation for
Advanced Internet Development, Inc. (Internet2) and contributors. This kit and its image are not official Internet2
products.
