# ToolboxAudit test project

A minimal Perspective project used to prove the `perspective` playbook
library (`session_smoke.yaml`, `page_crawl.yaml`) against a real gateway.
Built for the Perspective Project Audit Phase 4 work
(`docs/plans/perspective-project-audit.md`).

## What it is

- 2 views: `Home` (label + label + button that navigates to `/page2`) and
  `Page2` (label + label + button that navigates back to `/`).
- `page-config` with 2 routes: `/` -> `Home`, `/page2` -> `Page2`.
- No `session-permissions` / auth resources, no security zones -> the
  project inherits the gateway's default (anonymous) access, so
  `session_smoke.yaml` can prove a session starts with **no login**.
- Deliberately tiny: no session-props, style-classes, or scripts beyond the
  two navigation button click handlers.

File layout under `ToolboxAudit/` mirrors what the gateway actually needs on
disk (verified 2026-07-06 against Ignition 8.3.6 in the `ignition-module-testing`
docker container):

```
ToolboxAudit/
├── project.json
└── com.inductiveautomation.perspective/
    ├── page-config/
    │   ├── resource.json
    │   └── config.json
    └── views/
        ├── Home/
        │   ├── resource.json
        │   └── view.json
        └── Page2/
            ├── resource.json
            └── view.json
```

Each `resource.json`'s `attributes.lastModificationSignature` is a sha-256 of
the concatenated bytes of its sibling `files` entries, matching the format
real gateway-written resources use (not verified/checked by the gateway on
load as far as we could tell, but kept correct for consistency with real
projects).

## Deploying it to a gateway (reproduction steps)

These are the exact steps used to deploy this project to the
`ignition-module-testing` docker container (host networking, gateway at
`http://localhost:8088`). Adjust the container name / gateway data path for
your environment.

```bash
# 1. Copy the project directory into the gateway's projects folder
docker cp ToolboxAudit ignition-module-testing:/usr/local/bin/ignition/data/projects/ToolboxAudit

# 2. Fix ownership/permissions to match the gateway's other projects.
#    `docker cp` preserves the copying user's uid/gid, which is usually
#    wrong inside the container, and `docker exec` (no -u) runs as the
#    unprivileged `ignition` user, which can't chown files it doesn't own -
#    use -u root for this one step only.
docker exec -u root ignition-module-testing chown -R ignition:ignition \
    /usr/local/bin/ignition/data/projects/ToolboxAudit
docker exec -u root ignition-module-testing find \
    /usr/local/bin/ignition/data/projects/ToolboxAudit -type f -exec chmod 644 {} \;
docker exec -u root ignition-module-testing find \
    /usr/local/bin/ignition/data/projects/ToolboxAudit -type d -exec chmod 755 {} \;
```

### The project scan gotcha (read this before assuming a restart is needed)

Ignition 8.3 has **no restart requirement** for picking up a brand-new
project directory, but it is also **not automatic on a useful timescale**:
in testing, the gateway did not detect a new top-level project folder within
2 minutes of it appearing on disk (confirmed via the `Perspective.Routes`
gateway log repeatedly logging `Could not find project 'ToolboxAudit'`).

The fix is the **"Scan File System" button** on the Gateway web UI's
Projects page (`Config -> Platform -> System -> Projects`, or directly at
`/app/platform/system/projects` once logged in). Click it, confirm the
"Scan File System?" dialog, and the new project is registered within a few
seconds - no restart of the gateway or the container required. This is a
two-click flow (the page button opens a confirmation dialog with its own
"Scan File System" button) if driving it with Playwright/browser automation.

Once a project is *registered* this way, subsequent edits to its files on
disk (e.g. updating `view.json`) are picked up automatically without
needing another manual scan - the one-time gap is specifically for
brand-new project directories the gateway doesn't know about yet.

### Verifying the deploy

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8088/data/perspective/client/ToolboxAudit
# -> 200 once registered (404 before the scan picks it up)
```

## Safe to delete / redeploy

Nothing here depends on gateway state beyond the project directory itself.
To remove it: delete `/usr/local/bin/ignition/data/projects/ToolboxAudit`
inside the container and click "Scan File System" again (the gateway
detects the removal the same way).
