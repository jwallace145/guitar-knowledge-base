# Instructions for coding agents

This repository is a Zensical static site: Markdown in `docs/`, config in
`zensical.toml`, Python tooling via `uv`, served from S3 + CloudFront. The
infrastructure is one file, `jwall-engineering-sites.yaml`, managed by the
`jwall-engineering-sites` CLI from `jwallace145/jwall-engineering-infra`. Read
[CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow. The rules below are the ones you MUST follow.

## Never push to `main`

All changes go through a pull request from a branch. The branch ruleset rejects direct
pushes. Do not attempt to bypass it.

## Commits are one line

Every commit message is a single Conventional Commits header:

```
type(scope)?: subject
```

- Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `ci`, `build`, `perf`, `style`,
  `test`, `revert`. Breaking changes use `!` after the type or scope.
- Max 100 characters.
- **No body.** The only allowed content after the header is a blank line followed by
  `Co-authored-by: Name <email>` trailers. Anything else fails commitlint in CI.
- Put explanations in the PR description, never in the commit.

Example of the only acceptable multi-line form:

```
docs(theory): add modes page

Co-authored-by: Claude <noreply@anthropic.com>
```

## Open PRs with a typed template

Use `gh pr create` with the template matching the change type:

```sh
gh pr create --template feat.md      # new content or capability
gh pr create --template fix.md       # bug fix (has bug / cause / repro sections)
gh pr create --template docs.md      # documentation and site content
gh pr create --template chore.md     # maintenance, dependencies
gh pr create --template refactor.md  # restructuring with no visible change
gh pr create --template ci.md        # workflows and automation
```

- Fill in **every** section of the template. Do not leave placeholders or delete
  sections.
- The PR title must be a valid conventional commit header of the same type as the
  template. It becomes the squash commit message.
- Before opening the PR, run `uv run zensical build --strict` and report the result in
  "How it was verified".

## Content conventions

- One idea per page. Link to related pages instead of repeating them.
- New pages must be added to `nav` in `zensical.toml`.
- Images go in `docs/assets/images/`.
- Chord and scale diagrams are `chord` and `fretboard` fenced blocks, never ASCII art or
  images. See "Diagrams" in [CONTRIBUTING.md](CONTRIBUTING.md).
- Do not edit `CHANGELOG.md`, `version.txt`, or the version in `pyproject.toml`.
  Release Please owns them.

## Infrastructure rules

- **There is no Terraform in this repository.** `jwall-engineering-sites.yaml` is the
  whole description: project, repository, domain, the six required tags, the build
  output directory and preview settings. Change it there; the CLI validates it and
  fails fast on anything missing. Infrastructure behaviour lives upstream in
  `jwallace145/jwall-engineering-infra` (the CLI and reusable workflows) and
  `jwallace145/terraform-aws-jwall-engineering` (the modules); fix it there.
- **Never apply or publish from a machine.** Applies and publishes happen only in the
  reusable `deploy` workflow when a release PR is merged, as the apply role in the
  `prod` environment.
- **The reusable workflow refs are exact tags** (`@v0.8.0`) in the three workflow files.
  Dependabot bumps them; bump all three together. The workflow at a tag runs the CLI
  image of the same tag.
- **The plan and preview jobs declare no GitHub environment** and the deploy job runs in
  `prod`; the OIDC role trust depends on it.
- **Owner-only steps** (AWS credentials, GitHub environments, repository variables, DNS
  changes in other repos) are listed in the PR description, never attempted.

## Local commands

```sh
uv sync
uv run zensical serve
uv run zensical build --strict
npx commitlint --from main        # lint your branch's commits before pushing
```
