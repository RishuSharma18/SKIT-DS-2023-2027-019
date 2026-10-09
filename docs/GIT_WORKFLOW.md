# Git Workflow

## Branches
```
main      ← stable, demo-ready only (merge at the end of each sprint)
feature branches (branch from main; PRs target main):
  feat/backend-vaibhav
  feat/detection-rishu
  feat/ocr-nandani
  feat/dashboard-bhumi
```
Make new small branches for each task, e.g. `feat/ocr-plate-normalisation`, and delete them after merge.

## One-time: Vaibhav pushes the scaffold
```bash
cd smart-cctv-parking
git init -b main
git add .
git commit -m "chore: initial project scaffold (backend, frontend, ai-service)"
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```
Then GitHub → Settings → Collaborators (add the 3 teammates) → Branches → protect `main` (require pull requests).

## Everyone else, once
```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>
git checkout main
git pull
git checkout -b feat/<your-area>-<name>
```

## Daily loop
```bash
git checkout main && git pull                  # get latest
git checkout feat/<your-branch>
git merge main                                  # keep up to date (resolve conflicts here)
# ... work ...
git add <files>
git commit -m "feat(ocr): normalise Indian plate format"
git push -u origin feat/<your-branch>
# open a Pull Request → base: main, ask 1 teammate to review, then merge
```

## Commit message style
`type(scope): message`, with type one of `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.
Examples: `feat(detection): add ByteTrack tracking`, `fix(backend): free slot on exit`.

## Rules to avoid conflicts
1. Stay in your own folder/files as per the ownership table. If you must change someone else's file, tell them first.
2. Never commit `.env`, `node_modules`, `.venv`, `*.pt` model weights or large videos (already in `.gitignore`). Share videos via Google Drive.
3. Pull `main` at least daily and merge it into your feature branch. Commit small and often.
4. Never push directly to `main`; use pull requests.
5. When the event contract in README changes, update the README in the same PR.
