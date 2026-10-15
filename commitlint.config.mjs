// Commit message rules for this repo. CI runs this against every commit in a PR
// and against the PR title; the pre-commit hook runs it locally as a convenience.
//
// Every commit message is one Conventional Commits header line. The only thing
// allowed after the header is a blank line followed by Co-authored-by trailers.
// Details belong in the PR description, not the commit body.

const TRAILER = /^Co-authored-by: .+ <.+>$/;

/** @type {import('@commitlint/types').Rule} */
function onlyCoauthorTrailers(parsed) {
  const lines = parsed.raw.replace(/\s+$/, "").split(/\r?\n/);
  const rest = lines.slice(1);

  if (rest.length === 0) {
    return [true];
  }
  if (rest[0].trim() !== "") {
    return [
      false,
      "the header must be followed by a blank line before any Co-authored-by trailers",
    ];
  }
  for (const line of rest.slice(1)) {
    if (line.trim() === "") continue;
    if (!TRAILER.test(line)) {
      return [
        false,
        `only "Co-authored-by: Name <email>" trailers may follow the header; found: "${line}"`,
      ];
    }
  }
  return [true];
}

export default {
  extends: ["@commitlint/config-conventional"],
  plugins: [{ rules: { "only-coauthor-trailers": onlyCoauthorTrailers } }],
  rules: {
    "header-max-length": [2, "always", 100],
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "docs", "chore", "refactor", "ci", "build", "perf", "style", "test", "revert"],
    ],
    "only-coauthor-trailers": [2, "always"],
    // The custom rule above covers the body and footer, so loosen the built-in
    // ones that would otherwise interfere with Co-authored-by trailers.
    "body-max-line-length": [0],
    "footer-max-line-length": [0],
  },
};
