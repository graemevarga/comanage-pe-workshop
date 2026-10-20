# COmanage Registry PE 5.2.0 workshop

A hands-on environment for COmanage Registry PE (v5) that is the **delivered project, not a special workshop
build**: the Registry image is the one the upstream 5.2.0 release builds with its own `container/build.sh`
(basic-auth variant, unmodified), configured only through upstream's documented environment variables, next to
standard PostgreSQL and Mailpit containers. What you do here is what you'll do at home; see
[Running it yourself](docs/at-home.md).

> **Demo only.** The workshop's one customisation is anonymous login: anyone who can reach the Registry can log in
> as the platform administrator. The ports are published on 127.0.0.1 only; keep it that way and use only fictional
> data.

## Quick start

Requirements: Docker Desktop (macOS, Windows with WSL 2) or Docker Engine with Compose (Linux), about 3 GB of disk.

```bash
git clone https://github.com/graemevarga/comanage-pe-workshop.git
cd comanage-pe-workshop
docker compose up -d
```

When `docker compose ps` shows the `registry` service `(healthy)`:

- **Registry:** <https://localhost:8443/registry/>. Accept the self-signed certificate, click **Login**, type
  username **`admin`** and leave the password empty.
- **Mail:** <http://localhost:8025/> (Mailpit). Everything the Registry sends lands here.

The first start is the Registry's real first start: it creates the database schema and the platform administrator,
and nothing else.

## What is running

| Service | Image | Role |
|---|---|---|
| `registry` | `ghcr.io/graemevarga/comanage-registry:5.2.0-basic-auth-1`: upstream's 5.2.0 basic-auth image, built by [this repository's workflow](.github/workflows/publish.yml) with upstream's `build.sh` | COmanage Registry (Apache + PHP), at `/registry/` |
| `registry-database` | `postgres:17` | The Registry database (named volume `registry-database`) |
| `mailpit` | `axllent/mailpit` | Catches outgoing mail; stands in for your SMTP relay |

How the workshop configures them, and what you would change for production, is in
[How it maps to a real deployment](docs/design-notes.md).

## Logging in

Any username works with an empty password, and you become whoever that username belongs to: `admin` is the
platform administrator, the HR people log in with their uid (for example `ruth.spence`, from checkpoint 04 on), and a
new name is a new person who can sign up through an enrollment flow. Use a private browser window per person.

## Checkpoints

Jump to the start of any chapter with the `./workshop` helper (a thin wrapper around `docker compose`; it prints
the commands it runs):

```bash
./workshop list
./workshop restore 04-filesource-synced
```

| Checkpoint | State |
|---|---|
| (fresh start) | Upstream's first start: platform admin `admin` only. `./workshop reset` returns here. |
| `01-email` | Mailpit configured as the Outgoing SMTP Server; `admin` has a verified email (`admin@workshop.test`) |
| `02-configuration` | FileConnector and PipelineToolkit active; COs Discovery TNG (2), Redcurrant University (3), Guests (4), MESS (5); affiliation type Principal Investigator |
| `03-connections` | Redcurrant University: pipeline "Process HR API Inputs" (matches on UID); API user `co_3.hr_api_user` |
| `04-filesource-synced` | Redcurrant University: FileSource "HR File" (`hr.csv`) synced, 45 people who can log in with their uid |
| `05-org-structure` | COUs (Alumni, Faculty/Staff, Retirees, Students; arbovirus), group Access-wiki nested from Retirees, Lamar Martin, Ruth Spence's role, Claude Larkin |
| `06-enrollment` | Discovery TNG self-signup flow "Join Discovery TNG": email verification through Mailpit, login identifier from the username |

`docker compose stop`/`start` and `docker compose down`/`up -d` keep your work (the database is in a named volume);
`./workshop reset` throws it away.

## Documentation

- [Participant guide](docs/participant-guide.md): install, start, log in, catch up, troubleshoot.
- [Instructor guide](docs/instructor-guide.md): chapter-by-chapter demo with click paths, commands, the API push
  example, CSV rules, regenerating checkpoints, known 5.2.0 traps.
- [How it maps to a real deployment](docs/design-notes.md): every setting, and what changes in production.
- [Running it yourself](docs/at-home.md): build the 5.2.0 images from the release and deploy them.
- [Alignment with the v5.2 course material](docs/laura-alignment.md).

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). COmanage Registry is © University Corporation for
Advanced Internet Development, Inc. (Internet2) and contributors. This kit and its image are not official Internet2
products.
