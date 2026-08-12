# DermClin-MT annotation tool

This is the generic, image-optional review interface used for the five-task
DermClin-MT workflow. The repository includes the tool code only. It does not
include annotations, images, taxonomies, source indices, review records, or an
annotation database.

The server uses only the Python 3 standard library and binds to `127.0.0.1` by
default. Review decisions are stored locally in a newly created SQLite file.

## Expected input layout

Point `--data-root` to a private directory with this layout:

```text
private_data/
  descriptors/{train,test}.json
  diagnosis/{train,test}.json
  differential/{train,test}.json
  management/{train,test}.json
  consultation/{train,test}.json
```

Each JSON file is an array of records following `docs/SCHEMA.md`. Image values
may be absolute paths or paths relative to `--image-root`. Keep all dataset and
image directories outside this Git repository.

## Run

```bash
python3 annotation_tool/app.py \
  --data-root /private/path/by_task \
  --image-root /private/path/images \
  --database /private/path/reviews.sqlite3 \
  --port 8000
```

Then open `http://127.0.0.1:8000`.

The interface supports approve, revise, reject, and skip decisions; an optional
revised answer; comments; annotator name; and JSON export. It never modifies the
source annotation files.

## Security boundary

- Do not expose the server to the public Internet.
- Image access is confined to `--image-root` using resolved-path checks.
- The request body is capped at 1 MiB.
- SQLite files, exports, logs, PIDs, datasets, and images are ignored by Git.
- The tool contains no authentication layer; use it only on a trusted machine or
  behind an authenticated reverse proxy.

