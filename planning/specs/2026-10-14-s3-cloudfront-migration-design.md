# S3 + CloudFront migration: design

Date: 2026-10-14
Status: approved (2026-10-14); implemented in PR #13, site hand-over in jwallace145/site#52

## Goal

Serve <https://guitar.jwall.engineering/> from the jwall-engineering AWS account instead
of GitHub Pages, using the published Terraform module
[`jwallace145/jwall-engineering/aws`](https://registry.terraform.io/modules/jwallace145/jwall-engineering/aws/latest)
so this site is deployed the same way as every other jwall-engineering site. The repo
gains a Terraform root, a pull-request preview per PR, and a deploy that runs only when
a Release Please release PR is merged.

Success looks like:

- A merged release PR tags `vX.Y.Z` and, in the same workflow run, applies the Terraform
  and publishes that tag's build to `s3://jwall-engineering-guitar-knowledge-base/prod/`.
- Every pull request from a branch in this repo gets
  `https://pr-<n>.preview.guitar.jwall.engineering/`, updated on each push and removed
  when the PR closes.
- Pull requests that touch `infra/` get a Terraform plan posted as a comment.
- Nothing in CI holds long-lived AWS credentials; every job assumes one of the three
  per-project OIDC roles the infra repo already created.
- The `site` repo no longer manages the hosted zone or other projects' records.

## Non-goals

- A `dev` environment. The root module supports `dev_domain_name`; it stays `null`.
  The apply role is only allowed to change `guitar.jwall.engineering` and
  `*.preview.guitar.jwall.engineering`, so a dev record could not be created anyway.
- Changing the infra repo. It must be on module 0.3.0 and pass `owner_id` and
  `repository_id` for each project (see "Prerequisites"), and the owner is doing that in
  parallel.
- Moving `cs-survival-guide` off GitHub Pages. Its CNAME and the Pages verification TXT
  record stay live; see "Hand-over in the site repo" for who holds them.
- Changing the content build. `uv run zensical build --strict --clean` stays the build.

## Facts this design relies on

| Fact | Value | Source |
| --- | --- | --- |
| AWS account / region | `650503560686` / `us-east-1` | infra repo |
| Project key | `guitar-knowledge-base` | `projects.tf` in infra repo |
| Site bucket | `jwall-engineering-guitar-knowledge-base` | `site-bucket` naming |
| CI roles | `jwall-engineering-guitar-knowledge-base-ci-{plan,preview,apply}` | `site-ci-roles` naming |
| State bucket / key | `jwall-engineering-tfstate` / `project=guitar-knowledge-base/env=prod/guitar-knowledge-base-prod.tfstate` | infra README key convention |
| Hosted zone | `jwall.engineering`, ID `Z029546536VUFGDCPXZ21` | infra plan output |
| GitHub IDs | owner `35950238`, repository `1418340665` | `gh api repos/jwallace145/guitar-knowledge-base` |
| OIDC subject form | immutable (`repo:jwallace145@35950238/guitar-knowledge-base@1418340665:...`) | `actions/oidc/customization/sub` |
| Role trust | plan and preview trust `:pull_request`; apply trusts `:environment:prod` | `site-ci-roles` |
| Module version | `0.3.0`, pinned exactly | registry |

The hosted zone ID is hardcoded in `infra/terraform.tfvars`. A `data "aws_route53_zone"`
lookup by name would need `route53:ListHostedZones`, which the project roles do not
grant, and that is by design.

## Terraform root: `infra/`

One root module at `infra/`, applied by CI only. Layout follows the infra repo:

| File | Contents |
| --- | --- |
| `versions.tf` | Terraform `>= 1.11, < 2.0`, AWS provider `~> 6.0` |
| `providers.tf` | `provider "aws"` for `us-east-1` with `default_tags = module.context.tags` |
| `backend.tf` | empty `backend "s3" {}`; configured from `backend/prod.hcl` |
| `backend/prod.hcl` | bucket, key (above), region, `use_lockfile = true`, `encrypt = true` (same shape as the infra repo) |
| `context.tf` | `module "context"` (`project = "guitar-knowledge-base"`, `environment = "prod"`, `repository = "jwallace145/guitar-knowledge-base"`) |
| `main.tf` | `module "site"` (root registry module): `bucket_name` and `bucket_regional_domain_name` from `module.context.bucket_name`, `domain_name`, `zone_id`, `dev_domain_name = null`, `enable_preview = true` |
| `variables.tf` | `domain_name`, `zone_id` |
| `terraform.tfvars` | `domain_name = "guitar.jwall.engineering"`, `zone_id = "Z029546536VUFGDCPXZ21"` |
| `outputs.tf` | `prod_distribution_id`, `preview_distribution_id`, `prod_url`, `preview_url_pattern`, `bucket_name` |
| `.terraform.lock.hcl` | committed, provider hashes for `linux_amd64` and `darwin_arm64` |
| `.tflint.hcl` | same as the infra repo (terraform recommended preset, aws ruleset) |
| `README.md` | what the stack creates, how CI uses it, owner hand-off and cutover |

Both module blocks pin `version = "0.3.0"` exactly. Module versions are not recorded in
the lock file, so a range would not be reproducible. Dependabot's `terraform` ecosystem
is enabled for `/infra` with commit prefix `chore(deps)` so bumps arrive as PRs that
carry a plan comment.

What the registry root module creates for this input: an ACM certificate and a
CloudFront distribution for `guitar.jwall.engineering` served from `<bucket>/prod`, a
wildcard certificate and distribution for `*.preview.guitar.jwall.engineering` served
from `<bucket>/previews/pr-<n>`, the index-rewrite CloudFront Functions, and the Route 53
alias records. The bucket and the IAM roles are owned by the infra repo and are only
referenced here by name.

## Workflows

### `ci.yml` (pull requests)

Existing jobs stay as they are: `commitlint`, `PR title lint`, `build`. Two jobs are
added.

**`terraform`** always runs, so it can be added to the ruleset as a required check. It
runs `terraform fmt -check -recursive`, `terraform init -backend=false`,
`terraform validate`, and `tflint` in `infra/`. No AWS credentials.

**`terraform-plan`** runs only when the PR comes from a branch in this repository (forks
get no OIDC token) and only when `infra/` differs between base and head. It assumes the
plan role with `aws-actions/configure-aws-credentials`, runs
`terraform init -backend-config=backend/prod.hcl` and
`terraform plan -detailed-exitcode -lock-timeout=60s`, and posts the plan as a sticky
comment (`marocchino/sticky-pull-request-comment`, header `terraform-plan`) that is
replaced on each push. The job fails only when the plan errors; "changes pending" is a
normal outcome. The plan role may write the `.tflock` object, so locking stays on.

### `preview.yml` (pull requests)

Triggered on `opened`, `synchronize`, `reopened`, `closed`; restricted to PRs from
branches in this repository. Concurrency group `preview-<pr>` with cancel-in-progress.

**`deploy`** (not on `closed`): build with `uv run zensical build --strict --clean`,
assume the preview role, `aws s3 sync site/ s3://<bucket>/previews/pr-<n>/ --delete`
with `Cache-Control: public, max-age=0, must-revalidate` on HTML and
`public, max-age=300` on everything else, then post or update a sticky comment
(header `preview`) with `https://pr-<n>.preview.guitar.jwall.engineering/` and the
commit SHA. No CloudFront invalidation: the preview distribution's cache policy has a
60-second default TTL and the preview role has no invalidation permission.

The job has **no `environment:`**. The preview role trusts the `pull_request` subject;
putting the job in a GitHub environment would change the subject to `environment:<name>`
and the role assumption would fail.

**`cleanup`** (on `closed`): assume the preview role,
`aws s3 rm s3://<bucket>/previews/pr-<n>/ --recursive`, and update the sticky comment to
say the preview was removed. Objects under `previews/` also expire after 14 days by
bucket lifecycle, so a failed cleanup is not a leak.

The preview build is the same as the production build. Zensical has no CLI override for
`site_url`, so canonical links, the sitemap and `search.json` in a preview point at the
production host. That is acceptable: internal links are relative and work under the
preview host, and canonical links pointing at production is the right signal for
crawlers.

### `release-please.yml` (push to main, workflow_dispatch)

The existing `release-please` job stays and gains outputs `release_created` and
`tag_name`. A **`deploy`** job is added, modelled on the `site` repo:

- Runs when `release_created == 'true'`, or on `workflow_dispatch` with an optional `tag`
  input (default: the latest GitHub release) to redeploy.
- `environment: prod` with `url: https://guitar.jwall.engineering/`. This is what gives
  the OIDC token the `environment:prod` subject the apply role trusts.
- Checks out the release tag, not `main`.
- Terraform: `init -backend-config=backend/prod.hcl`, `plan -out=tfplan`, `apply tfplan`
  in `infra/`, with the apply role.
- Site: `uv sync --frozen`, `uv run zensical build --strict --clean`, then three
  `aws s3 sync` passes into `s3://<bucket>/prod/`:
  1. everything except HTML and the hashed bundles, `--delete`, `max-age=3600`;
  2. `assets/javascripts/bundle.*.min.js` and `assets/stylesheets/*.*.min.css`,
     `max-age=31536000, immutable`;
  3. HTML, `search.json`, `sitemap.xml`, `max-age=0, must-revalidate`,
     `--content-type "text/html; charset=utf-8"` for the HTML pass.
- `aws cloudfront create-invalidation --paths "/*"` on the prod distribution, whose ID
  is read from `terraform output -raw prod_distribution_id` in the same job, so no
  variable has to be kept in sync with the stack.
- A step summary with the tag and the URL.

Concurrency group `release`, never cancelled. The old `deploy.yml` (GitHub Pages) is
deleted. Pages keeps serving its last artifact until DNS moves, so deleting the
workflow before cutover causes no outage.

### Variables and secrets

All three role ARNs are **repository variables**, matching the infra repo:
`AWS_PLAN_ROLE_ARN`, `AWS_PREVIEW_ROLE_ARN`, `AWS_APPLY_ROLE_ARN`. The region is
hardcoded to `us-east-1` in each workflow's `env`. The existing
`RELEASE_BOT_*` secrets are unchanged. Nothing new is secret.

## Hand-over in the `site` repo

`jwallace145/site` currently creates the `jwall.engineering` zone and three plain
records through its `dns-zone` module. The infra repo has since imported the zone, so
the zone is in two states and the site's DNS management is retired:

- `infra/modules/dns-zone/` is deleted. The `dns` variable shrinks to
  `{ hosted_zone_id = string }`; `module "dns"` and the `zone_name` branches in
  `main.tf` and the `domain` validations go with it.
- `terraform.tfvars` sets `dns = { hosted_zone_id = "Z029546536VUFGDCPXZ21" }`.
- The site's own records (apex and `www` aliases, ACM validation, `preview` wildcard)
  are created by its `static-site` and `preview-site` modules and are unaffected.
- Before merging, the owner runs `terraform state rm 'module.dns[0]'` in
  `infra/environments/prod/` so the zone and the three records leave the site's state
  without being destroyed. The PR's plan then shows no changes.
- `infra/README.md` and `docs/repo-setup.md` in the site repo drop the zone bootstrap
  story and point at the infra repo.

After this, two records are live but unmanaged: the `survival-guide` CNAME and the
`_github-pages-challenge-jwallace145` TXT. They must stay while `cs-survival-guide` is on
GitHub Pages. Adopting them (TXT in the infra repo as a zone-level record, the CNAME in
`cs-survival-guide` when it migrates) is noted for the infra repo's `docs/migration.md`
and left to the owner's parallel work. The `guitar` CNAME is deleted at cutover (below).

## Cutover

Order of operations, with who does each step:

1. **Owner, infra repo.** Module 0.3.0 with `owner_id` and `repository_id` per
   project, applied. Until then, every role assumption from this repo fails with
   `Not authorized to perform sts:AssumeRoleWithWebIdentity`.
2. **Owner, this repo.** Create the `prod` environment with deployment branch policy
   `main` plus tags `v*`; set the three `AWS_*_ROLE_ARN` repository variables from
   `terraform output projects` in the infra repo. Exact `gh` commands are in
   `infra/README.md`.
3. **Merge this repo's PR.** CI must be green, including the plan comment (it needs
   steps 1 and 2). Nothing deploys yet; Release Please opens a release PR.
4. **Merge the `site` repo PR** after the `state rm` in that repo.
5. **Merge the release PR.** The deploy job applies the Terraform: certificate,
   distributions, preview alias and function all succeed; the `guitar.jwall.engineering`
   alias fails because the CNAME still exists (Route 53 rejects an A record beside a
   CNAME). The job fails at that step with state saved. This is expected.
6. **Owner.** Delete the CNAME:
   `aws route53 change-resource-record-sets --hosted-zone-id Z029546536VUFGDCPXZ21 --change-batch '{"Changes":[{"Action":"DELETE","ResourceRecordSet":{"Name":"guitar.jwall.engineering","Type":"CNAME","TTL":300,"ResourceRecords":[{"Value":"jwallace145.github.io."}]}}]}'`
7. **Re-run the deploy** with `workflow_dispatch` (no tag input: latest release). The
   apply creates the alias, the site syncs, CloudFront is invalidated. Downtime is
   roughly the CNAME's 300-second TTL, because the distribution already exists from
   step 5.
8. **Owner, afterwards.** Disable GitHub Pages on the repo and delete the
   `github-pages` environment; add `terraform` to the ruleset's required checks; remove
   `letsencrypt.org` from the CAA list in the infra repo only once `cs-survival-guide`
   has also left Pages.

Steps 5 to 7 could be collapsed by deleting the CNAME before merging the release PR, at
the cost of 10 to 15 minutes of downtime while the certificate validates and the
distribution deploys. The split order is recommended.

## Error handling

- A failed Terraform apply leaves state consistent (Terraform writes state after each
  resource) and the deploy job stops before touching the bucket. Re-run with
  `workflow_dispatch`.
- A failed sync leaves `prod/` partially updated but CloudFront still serves the old
  cached objects until the invalidation, which does not run. Re-run the deploy.
- A preview deploy for a fork PR is skipped, not failed, by the `if:` guard.
- The plan comment is posted even when the plan fails, with the tail of the log.
- Both plan and apply use `-lock-timeout` so a concurrent run waits rather than fails.

## Testing

- **Static, locally and in CI**: `terraform fmt -check`, `terraform validate` with
  `-backend=false` (fetches the registry module, no credentials), `tflint`,
  `actionlint` on the workflows, and `uv run zensical build --strict --clean`.
- **A real plan** needs the roles, so it is verified by the PR's plan comment once the
  owner has finished steps 1 and 2 of the cutover. The expected first plan is a full
  create of the registry module's resources and nothing else.
- **End to end**: the preview comment on this PR itself, once the roles work, proves the
  preview path. The first release proves the deploy path.

## Documentation

- `README.md`: hosting line and a short "Deploy" paragraph (release merge deploys;
  previews per PR).
- `CONTRIBUTING.md`: the "Releases" section gains the deploy step and the preview
  behaviour; a new "Infrastructure" section with the local Terraform commands and the
  rule that applies only happen in CI.
- `AGENTS.md`: four rules from the infra repo's AGENTS.md: never `terraform apply`
  locally; keep module pins exact and bump them together; never add `ignore_changes`,
  `-lock=false` or widen IAM to make a plan pass; list owner-only steps in the PR
  instead of attempting them.
- `infra/README.md`: as described above, including the owner hand-off commands and the
  cutover list.
- `.gitignore`: `.terraform/`, `*.tfstate*`, `*.tfplan`, `plan.log`,
  `backend_override.tf`.
