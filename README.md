# COmanage Registry PE 5.2.0 workshop environment

One Docker image with everything a hands-on COmanage Registry PE (v5) workshop needs: **Registry 5.2.0** (the
upstream Internet2 release, unmodified), **PostgreSQL**, **Mailpit** to catch email, a job runner, the sample HR files
and catch-up **checkpoints** for every chapter. Login is Apache anonymous Basic auth: no Shibboleth, no LDAP, no
accounts to set up. It runs natively on Apple Silicon and Intel/AMD, on macOS, Windows (WSL 2) and Linux.

> **Demo only.** Anyone who can reach the Registry port can log in as the platform administrator. The compose file
> publishes the ports on 127.0.0.1 only; keep it that way and use only fictional data.

## Quick start

```bash
git clone https://github.com/graemevarga/comanage-pe-workshop.git
cd comanage-pe-workshop
docker compose up -d
```

When `docker compose ps` shows `(healthy)` (about ten seconds after the image is downloaded):

- **Registry:** <https://localhost:8443/registry-pe/>. Accept the self-signed certificate, click **Login**, type
  username **`admin`** and leave the password empty.
- **Mail:** <http://localhost:8025/> (Mailpit). Everything the Registry sends lands here.

Without cloning the repository:

```bash
docker run -d --name comanage -p 127.0.0.1:8443:443 -p 127.0.0.1:8025:8025 ghcr.io/graemevarga/comanage-pe-workshop:5.2.0-1
```

## Logging in

Any username works with an empty password, and you become whoever that username belongs to: `admin` is the
platform administrator, the HR people log in with their uid (for example `ruth.spence`, from checkpoint 04 on), and a
new name is a new person who can sign up through an enrollment flow. Use a private browser window per person.

## Checkpoints

Jump to the start of any chapter (your browser session ends; log in again):

```bash
docker compose exec registry workshop restore 04-filesource-synced
```

| Checkpoint | State |
|---|---|
| `01-fresh` | Platform admin `admin`; Mailpit configured as the outgoing mail server. **This is the state a new container starts in.** |
| `02-configuration` | FileConnector and PipelineToolkit active; COs Discovery TNG (2), Redcurrant University (3), Guests (4), MESS (5); affiliation type Principal Investigator |
| `03-connections` | Redcurrant University: pipeline "Process HR API Inputs" (matches on UID); API user `co_3.hr_api_user` |
| `04-filesource-synced` | Redcurrant University: FileSource "HR File" (`hr.csv`) synced, 45 people who can log in with their uid |
| `05-org-structure` | COUs (Alumni, Faculty/Staff, Retirees, Students; arbovirus), group Access-wiki nested from Retirees, Lamar Martin, Ruth Spence's role, Claude Larkin |
| `06-enrollment` | Discovery TNG self-signup flow "Join Discovery TNG": email verification through Mailpit, login identifier from the username |

`docker compose exec registry workshop help` lists the other helpers (`list`, `reset`, `status`, `sync`, `cake`,
`psql`, `logs`). `docker compose stop`/`start` keeps your work; `docker compose down` throws it away.

## Documentation

- [Participant guide](docs/participant-guide.md): install, start, log in, catch up, troubleshoot.
- [Instructor guide](docs/instructor-guide.md): chapter-by-chapter demo with click paths, the API push example,
  CSV rules, regenerating checkpoints, known 5.2.0 traps.
- [Design notes](docs/design-notes.md): how the image is built and why.
- [Alignment with the v5.2 course material](docs/laura-alignment.md).

## Building it yourself

```bash
make build      # docker compose -f compose.yaml -f compose.build.yaml build
```

The build downloads the upstream 5.2.0 source from github.internet2.edu and refuses it unless it is the tagged
commit (`c5e9be6f`). Checkpoints are produced by `tools/seed/seed-all.sh`, which drives the UI with Playwright.
Published images (amd64 + arm64) are built by `.github/workflows/publish.yml` on version tags.

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). COmanage Registry is © University Corporation for
Advanced Internet Development, Inc. (Internet2) and contributors. This kit is not an official Internet2 product.
