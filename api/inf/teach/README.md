# Teach Winter AI something new

Drop `.txt` or `.md` files in this folder and Winter AI will automatically
load them into its searchable knowledge base the next time it starts, or
immediately if you call:

```
POST /api/v1/teach/reload
```

## Format

Plain text works fine. If you want a fact to answer consistently in all
three supported languages, use this convention (one block per fact):

```
EN: The capital of Kenya is Nairobi.
FR: La capitale du Kenya est Nairobi.
RW: Umurwa mukuru wa Kenya ni Nairobi.
```

Untagged lines are treated as English by default -- that's fine too, just
less precise for language-matched retrieval.

## Uploading over the API instead of git

If your deploy doesn't give you filesystem access (e.g. Render's ephemeral
containers reset the filesystem on redeploy), use:

```
POST /api/v1/teach/upload   (multipart form field: file)
```

Note: on most container hosts, anything uploaded this way disappears on the
next deploy unless you also commit it to `api/inf/teach/` in git. For
knowledge you want to keep permanently, add the file to this folder in your
repository instead of only uploading it at runtime.
