# Stack Builder golden files (T4)

Snapshots of every artefact `ComposeGenerator.generate()` produces for the
curated, realistic stacks defined in `../golden_stacks.py`
(`GOLDEN_STACKS`). Compared byte-exactly by `../test_goldens.py`. See
`docs/plans/stackbuilder-test-strategy.md` (T4) for why these stacks were
chosen.

## Layout

Each stack gets one directory named after its `GoldenStack.id`:

```text
goldens/<stack_id>/
  docker-compose.yml         <- result["docker_compose"]
  .env                       <- result["env"]
  README.md                  <- result["readme"]
  config_files/<rel_path>    <- one file per result["config_files"] entry,
                                 preserving its generator-assigned relative path
                                 (e.g. config_files/configs/traefik/traefik.yml)
  startup_scripts/<name>     <- one file per result["startup_scripts"] entry
                                 (start.sh, start.bat)
```

Only files the generator actually produced for that stack exist - e.g.
`ignition_emqx_nodered/` has no `config_files/` because neither EMQX nor
Node-RED currently gets a generated config file.

## Updating the snapshots

After an **intentional** change to the generator (a template, README wording,
a new integration wiring, etc.), regenerate the snapshots and review the diff
like any other code change:

```bash
cd backend
.venv/bin/python -m pytest tests/test_stackbuilder/test_goldens.py --update-goldens -q
git diff tests/test_stackbuilder/goldens/
```

`--update-goldens` is defined in `../conftest.py`. If a snapshot changes for
a reason you *didn't* expect, that's the point of this test tier - it's a
regression, not a golden update.

## Secret normalisation (why goldens are stable despite random secrets)

`ComposeGenerator` generates a fresh, cryptographically random OAuth client
secret on every call (`keycloak_generator.generate_client_secret`,
`secrets.token_urlsafe(32)`) whenever Keycloak is paired with an OAuth-client
service (Grafana or n8n). The same value is correctly threaded through to
both places it appears, so a single generation is internally consistent, but
two generations of the *same* input are never byte-identical. Left alone,
this would make golden snapshots permanently flaky.

Before snapshotting or comparing, `golden_stacks.normalize_artifacts()`
replaces every known non-deterministic value with the fixed placeholder
`NORMALIZED_SECRET`:

| Location | What gets normalised |
| --- | --- |
| `docker-compose.yml` | The `GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET` and `N8N_OAUTH_CLIENT_SECRET` environment values (regex, line-based, key-scoped - see `_SECRET_ENV_RE`) |
| `config_files/configs/keycloak/import/realm-*.json` | Every `clients[*].secret` field (JSON-parsed, not regex) |

Only `oauth_email_stack` and `full_mixed_stack` are actually affected (they're
the only two golden stacks pairing Keycloak with Grafana); the other five
stacks have no OAuth-client integration and were already fully deterministic.

**Other nondeterminism sources checked and found *not* to apply** to the
current golden stacks (documented so a future stack addition knows what to
watch for):

- **Admin/DB passwords** (`POSTGRES_PASSWORD`, `GATEWAY_ADMIN_PASSWORD`,
  `KEYCLOAK_ADMIN_PASSWORD`, etc.) are static catalog defaults
  (`data/catalog.json`), not randomly generated - no normalisation needed.
- **Mosquitto's password file** (`config_generators.generate_mosquitto_password_file`)
  salts its PBKDF2 hash with `os.urandom(12)`, which *is* nondeterministic -
  but the file is only generated when MQTT username/password are explicitly
  configured in `IntegrationSettings.mqtt`. None of the golden stacks do
  this (Mosquitto's `mosquitto.conf` is still generated deterministically for
  `full_mixed_stack`, just not the password file), so this path is
  deliberately not exercised by T4. If a future golden stack configures MQTT
  auth, its password file will need the same normalisation treatment.
- **Timestamps**: none of the generator's templates embed a generation
  timestamp or date - checked `compose_generator.py`, `keycloak_generator.py`,
  `config_generators.py`, `ignition_db_registration.py`.

## Generator bug fixed while building this test tier

`ComposeGenerator._get_service_dependencies` used to end with
`return list(set(dependencies))`. Python randomises string hashing per
process, so `set` iteration order (and therefore the `depends_on` key order
in the generated compose YAML) varied on every run of the same input -
harmless to Compose semantics, but it broke reproducibility of generated
output and made this golden-file tier flaky by design. Fixed to
`list(dict.fromkeys(dependencies))`, which dedupes while preserving
insertion order. See `ignition_toolkit/stackbuilder/compose_generator.py`.
