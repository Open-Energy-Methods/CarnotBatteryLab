# Publishing CarnotBatteryLab to the Open-Energy-Methods organization

**State at packaging:** local Git repository exists with `main` and two
commits; `origin` is not configured and no GitHub repository was created by
this archive. The GitHub connector available in this session cannot create
new repositories. Do not treat a proposed repository URL as an existing link.

## Windows PowerShell — preserve the supplied repository history

1. Download and extract `CarnotBatteryLab_repo_bootstrap.zip` to your local
   research directory. It includes a `.git` directory and branch `main`.
2. In GitHub, create an **empty** repository named `CarnotBatteryLab` under
   `Open-Energy-Methods`. Choose private while the licence and incomplete
   research claims are being reviewed, or public if the owner deliberately
   wants the preliminary work visible. **Do not initialize with a README,
   .gitignore or licence** (these files already exist locally).
3. Open PowerShell in the extracted root:

```powershell
cd "C:\Users\prasa\OEM_Research\CarnotBatteryLab"
git log --oneline -3
python -m pip install -e ".[test]"
python -m pytest tests/ -v
git remote add origin https://github.com/Open-Energy-Methods/CarnotBatteryLab.git
git push -u origin main
```

If `origin` is already present, inspect `git remote -v` instead of
blindly overwriting it. If your extract directory differs, adapt the `cd`
path. You need GitHub authentication and repository creation rights. The
commands do not create the remote GitHub repository themselves.

## After publishing

- Confirm 20 new foundation regression tests pass on GitHub Actions.
- Create issue tracking using `docs/IMPLEMENTATION_BACKLOG.md`; begin
  `feat/natural-fluid-hp-hx-baseline` as the first research feature branch.
- Choose source code and data licences (potentially different) and archive
  licences of any imported dependencies/datasets before a public release.
- Keep historical code in `legacy_audited_screen/` explicitly marked withdrawn.
- Do not mark scientific v1.0 complete until release gates and external
  validation evidence are satisfied.
