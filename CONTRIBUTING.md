# Contributing

Thanks for helping with the Guitar Knowledge Base. This document covers the workflow
and the rules that CI enforces. Coding agents should also read [AGENTS.md](AGENTS.md).

## Local development

Requires [uv](https://docs.astral.sh/uv/) and, for the optional commit hook,
[pre-commit](https://pre-commit.com/).

```sh
uv sync                              # install Zensical into .venv
uv run zensical serve                # preview at http://localhost:8000
uv run zensical build --strict       # what CI runs; fails on any warning
pre-commit install --hook-type commit-msg   # optional: lint commit messages locally
```

Content lives in `docs/` as Markdown. Navigation is defined in `zensical.toml`
under `nav`. When you add a page, add it to the nav.

## Diagrams

Chord boxes and fretboard shapes are written inline as fenced blocks and rendered to
SVG at build time by `tools/diagrams`. Never paste ASCII diagrams or image files.

A shape (scale, mode, arpeggio) is a `fretboard` block. Strings are `E A D G B e`, low
to high. Each dot is `fret[:label][@color]`; dots have no label unless you give one.

```fretboard
title: C major, position 1
frets: 7-10
color: 1=red
E: 8:1 10:2
A: 7:3 8:4 10:5
D: 7:6 9:7 10:1
G: 7:2 9:3 10:4
B: 8:5 10:6
e: 7:7 8:1 10:2
```

A chord is a `chord` block. `frets` has six tokens low to high (`x` muted, `0` open);
`fingers` labels the dots; `barre: N` draws a barre across every string fretted at N.

```chord
name: C
frets: x 3@red 2 0 1@red 0
fingers: - 3 2 - 1 -
```

- Colors: `red orange yellow green blue purple grey`. `color: 1=red 3=blue` colors by
  label; `@color` on a dot always wins.
- `frets: lo-hi` fixes the window; omit it to fit the dots (minimum four frets).
- A diagram sits centred on its own line. For a row of diagrams (a set of chord
  voicings, say), put the fences inside `<div class="fb-row" markdown>` ... `</div>`
  with a blank line after the opening tag; the row centres and wraps on phones.
- A malformed block fails `zensical build --strict` with the line and the problem.
- Run `uv run pytest` after changing anything in `tools/diagrams`, and build with
  `uv run zensical build --strict --clean`: Zensical caches rendered pages and does not
  notice renderer changes on its own.

## Workflow: branches and pull requests only

Nobody pushes to `main`, ever. The branch ruleset blocks it.

1. Branch from `main`. Any name works; `type/short-description` is a good habit
   (for example `docs/intervals-page`, `fix/broken-nav-link`).
2. Commit following the rules below.
3. Open a pull request using one of the typed templates (see below).
4. CI must pass: commitlint, PR title lint, a strict Zensical build, and the Terraform
   checks.
5. Merge with **squash** or **rebase**. Merge commits are disabled.
   - Squash uses the PR title as the commit message, so the title must itself be a
     valid conventional commit.
   - Rebase keeps each commit, so each commit must pass commitlint on its own.
6. The head branch is deleted automatically on merge.

Dependabot PRs are the one exception to per-commit linting: Dependabot writes commit
bodies that cannot be changed, so CI skips the `commitlint` job for them. Always
**squash**-merge Dependabot PRs so the one-line PR title is what lands on `main`.

## Commit messages

Every commit message is **one line** in
[Conventional Commits](https://www.conventionalcommits.org/) form:

```
type(scope)?: subject
```

- Allowed types: `feat`, `fix`, `docs`, `chore`, `refactor`, `ci`, `build`, `perf`,
  `style`, `test`, `revert`.
- Breaking changes use `!`, for example `feat!: reorganize theory section`.
- The header is at most 100 characters.
- The scope is optional. Section names make good scopes: `theory`, `fretboard`,
  `techniques`, `repertoire`.
- **No body text.** Explanations go in the PR description.
- The only thing allowed after the header is a blank line followed by one or more
  `Co-authored-by: Name <email>` trailers. GitHub adds these itself on squash merges.

Good:

```
feat(theory): add intervals page
```

```
fix(nav): correct link to triads page

Co-authored-by: Jane Doe <jane@example.com>
```

Bad (body text is rejected):

```
feat(theory): add intervals page

Covers names, sizes, and inversions.
```

### How it is enforced

- `commitlint.config.mjs` extends `@commitlint/config-conventional` and adds a local
  rule, `only-coauthor-trailers`, that rejects anything after the header other than
  blank lines and `Co-authored-by` trailers.
- **CI is authoritative.** The `commitlint` job lints every commit in the PR range
  (`base..head`), and the `PR title lint` job runs the same rules on the PR title.
- The pre-commit hook is a local convenience that runs the same config. Install it
  with `pre-commit install --hook-type commit-msg`.

## Pull request templates

There is one template per change type in `.github/PULL_REQUEST_TEMPLATE/`:
`feat.md`, `fix.md`, `docs.md`, `chore.md`, `refactor.md`, `ci.md`.

From the CLI:

```sh
gh pr create --template feat.md
```

From the web, append `?template=feat.md` to the new-PR URL. The default template
links to each typed one. Fill in every section; delete nothing but the hints.

The PR title must be a valid conventional commit header, because it becomes the squash
commit message. Match the type to the template you picked.

## Pull request previews

Every pull request from a branch in this repository is built and published to
`https://pr-<n>.preview.guitar.jwall.engineering/`. The URL is posted as a comment that
is updated on every push; the preview is deleted when the PR closes. Fork PRs get no
preview (no OIDC token). The preview is the production build byte for byte, so canonical
links and the sitemap point at the production host.

## Infrastructure

The site is served from S3 + CloudFront, described in Terraform under
[`infra/`](infra/) using the shared
[`jwallace145/jwall-engineering/aws`](https://registry.terraform.io/modules/jwallace145/jwall-engineering/aws/latest)
registry module. CI runs `terraform fmt`, `terraform validate` and `tflint` on every PR,
and posts a `terraform plan` comment when `infra/` changed. Applies happen only in the
`deploy` job when a release PR is merged; nobody applies locally.

```sh
cd infra
terraform fmt -check -recursive
terraform init -backend=false && terraform validate
tflint --init && tflint
```

Module versions are pinned exactly in `infra/context.tf` and `infra/main.tf`; bump both
together, and never switch a module to a git or local source. Do not add
`ignore_changes`, `-lock=false`, or widen an IAM policy to make a plan pass; explain the
diff in the PR instead. See [infra/README.md](infra/README.md).

## Releases and deploys

Releases are automated with [Release Please](https://github.com/googleapis/release-please).

- On every push to `main`, Release Please reads the conventional commits since the last
  release and opens or updates a release PR authored by `jwallace145-release-bot[bot]`.
  That PR bumps `version.txt`, `pyproject.toml`, and the root project's version in
  `uv.lock`, and updates `CHANGELOG.md`. CI syncs with `--locked`, so a lockfile that
  disagrees with `pyproject.toml` fails the build instead of drifting silently.
- `feat` bumps the minor version, `fix` bumps the patch, and `!` marks a breaking
  change. While the project is below 1.0.0, breaking changes bump the minor version.
- Merging the release PR creates the git tag and GitHub release.
- `CHANGELOG.md` is owned by Release Please. Do not edit it by hand.

Merging the release PR is also the deploy. The `deploy` job in the same workflow checks
out the tag, runs `terraform apply` in `infra/`, builds the site, syncs it to the `prod/`
prefix of the site bucket and invalidates CloudFront, so
<https://guitar.jwall.engineering/> always serves a tagged release. The Release workflow
can also be run manually to redeploy the latest (or a chosen) tag.
