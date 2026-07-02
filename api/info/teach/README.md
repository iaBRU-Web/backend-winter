# api/info/teach/

Drop any `.txt` or `.md` file in this folder and Winter AI will index it as
knowledge automatically at startup (and immediately if uploaded live via
`POST /api/v1/knowledge/upload`).

Format:
- Trilingual fact: `EN: fact in English | FR: fait en français | RW: ukuri mu Kinyarwanda`
- English-only fact: just write the sentence, one per line.
- Blank lines are ignored.

Anything you put here becomes searchable through the BM25 retrieval engine
and can be returned as an answer. This is the easiest way to extend what
Winter AI knows without touching any code — just commit new files here and
redeploy (Render will pick them up on the next build), or upload them live
through the API.

Example (delete this file or replace it with your own facts):

EN: The Winter AI teach folder lets anyone extend the knowledge base without editing code.
FR: Le dossier teach de Winter AI permet à quiconque d'étendre la base de connaissances sans modifier le code.
RW: Ubwoko bwa teach bwa Winter AI bwemerera umuntu wese kongera ubumenyi nta guhindura kode.
