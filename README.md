# Guitar Knowledge Base

A guitar theory and study knowledge base: intervals, scales, modes, harmony, the
fretboard, technique, and repertoire. Built with [Zensical](https://zensical.org/) and
deployed to GitHub Pages.

**Live site:** <https://guitar.jwall.engineering/>

## Local development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                 # install Zensical into .venv
uv run zensical serve   # preview at http://localhost:8000 with live reload
uv run zensical build   # write the static site to site/
```

Add `--strict` to `zensical build` to fail on warnings, which is what CI does.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the commit conventions, the branch-and-PR
workflow, and how releases work.

## License

[MIT](LICENSE)
