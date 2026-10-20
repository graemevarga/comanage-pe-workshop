# Checkpoints

Saved Registry databases (`pg_dump -Fc` files), for the presenter and for checking the lesson plan. Participants don't
need any: the workshop starts from a fresh install.

- `./workshop checkpoint NAME "description"` saves the current database here as `NAME.dump`.
- `./workshop restore NAME` puts it back (and restarts the Registry so it drops its caches).
- `tools/seed/seed-all.sh` walks through the lesson's procedures on a fresh install and saves one here after each
  chapter (see the instructor guide).

The dump files are not committed (`.gitignore`).
