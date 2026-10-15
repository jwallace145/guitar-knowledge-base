# Guitar Knowledge Base

A guitar theory and study knowledge base: intervals, scales, modes, harmony, the
fretboard, technique, and repertoire. Built with [Zensical](https://zensical.org/) and
served from AWS S3 + CloudFront.

**Live site:** <https://guitar.jwall.engineering/>

## Local development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                 # install Zensical into .venv
uv run zensical serve   # preview at http://localhost:8000 with live reload
uv run zensical build   # write the static site to site/
```

Add `--strict` to `zensical build` to fail on warnings, which is what CI does.

## Deploying

Every pull request gets a live preview at `https://pr-<n>.preview.guitar.jwall.engineering/`.
Merging a Release Please release PR tags a version, applies the Terraform in
[`infra/`](infra/) and publishes that tag to production. See
[CONTRIBUTING.md](CONTRIBUTING.md#releases-and-deploys) and [infra/README.md](infra/README.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the commit conventions, the branch-and-PR
workflow, and how releases and deploys work.

## License

[MIT](LICENSE)
