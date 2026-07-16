# Submission Checklist

## Required Package

| Deliverable | Repository location | Status |
|---|---|---|
| Product Vision | Supplied by project team | Required before submission |
| Risk Analysis | Supplied by project team | Required before submission |
| Jira board export | Supplied from Jira | Required before submission |
| Jira burndown charts | Supplied from Jira | Required before submission |
| Use-case diagram source/export | `diagrams/01-use-case.puml`, `rendered/01-use-case.svg` | Present |
| Class diagram source/export | `diagrams/02-class-diagram.puml`, `rendered/02-class-diagram.svg` | Present |
| Booking sequence source/export | `diagrams/03-sequence-booking-flow.puml`, `rendered/03-sequence-booking-flow.svg` | Present |
| Notification sequence source/export | `diagrams/04-sequence-notification-flow.puml`, `rendered/04-sequence-notification-flow.svg` | Present |
| Buyer activity source/export | `diagrams/05-activity-user-purchase.puml`, `rendered/05-activity-user-purchase.svg` | Present |
| Admin activity source/export | `diagrams/06-activity-admin-event-creation.puml`, `rendered/06-activity-admin-event-creation.svg` | Present |
| Component source/export | `diagrams/07-component-diagram.puml`, `rendered/07-component-diagram.svg` | Present |
| Deployment source/export | `diagrams/08-deployment-diagram.puml`, `rendered/08-deployment-diagram.svg` | Present |
| Terraform infrastructure | `infra/terraform/` | Present |
| Executable reference application | `src/ticketplus/`, `Dockerfile`, `compose.yaml` | Present |
| PostgreSQL migrations and seed data | `db/migrations/` | Present |
| API and event contracts | `contracts/` | Present |
| Unit and concurrency tests | `tests/` | Present; 9 pass locally, 1 HTTP class skipped by sandbox socket policy |
| Coverage evidence | `reports/coverage/summary.json` | Present; 93.1% critical-module statement coverage |
| Mutation evidence | `reports/mutation/summary.json` | Present; 6/6 targeted mutations killed |
| QA and verification strategy | `docs/quality/` | Present |
| Executable contention test | `quality/load/hot-seat-contention.js` | Present; requires a test environment |
| GitLab pipeline | `.gitlab-ci.yml` | Present |
| Merge-request process | `CONTRIBUTING.md`, `.gitlab/merge_request_templates/Default.md` | Present |
| Production architecture | `docs/architecture-and-operations/` | Present |
| Team roles and standards | `docs/project-governance/` | Present |

## Final Verification

- [ ] Insert the final Product Vision and Risk Analysis files.
- [ ] Export Jira backlog, hierarchy, sprint reports, and burndown charts.
- [x] Render all PlantUML sources as SVG.
- [ ] Export diagrams as vector PDF if required by the instructor; SVG sources
      are currently included.
- [ ] Run the GitLab pipeline on the final commit and retain its reports.
- [x] Confirm Terraform formatting without applying billable resources.
- [ ] Retain a successful provider-backed `terraform validate` result from GitLab
      CI; the local registry endpoint did not expose the provider protocol.
- [ ] Remove credentials, local state, caches, personal data, and temporary files.
- [ ] Verify every document link and submission filename on a clean checkout.
- [ ] Record the commit SHA used for the presentation and archive.
- [ ] Create one ZIP containing the complete repository and external exports.
- [ ] Extract the ZIP into a clean directory and repeat the manifest check.

## Packaging Rule

The tag pipeline creates `ticketplus-<tag>.zip` while excluding Git metadata and
Terraform state. Add the team-supplied baseline documents and Jira exports before
creating the final tag so the generated archive is complete.
