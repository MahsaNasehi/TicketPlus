# Team Roles and Decision Responsibilities

Team members rotate implementation responsibilities while preserving explicit
ownership for decisions and approvals.

## Role Perspectives

| Role | Primary concern | Required evidence | Questions asked during review |
|---|---|---|---|
| Product Owner | User value, priority, measurable outcome | Acceptance criteria, success metric, scope decision | Does this solve the highest-value problem? |
| System Analyst | Complete, consistent, traceable requirements | Models, contracts, story-to-artifact mapping | Are edge cases and domain terms unambiguous? |
| Backend Developer | Correct domain behavior and maintainable services | Tests, API/event schemas, migrations | Who owns this invariant and how does it fail? |
| Frontend Developer | Accessible, recoverable purchase workflows | UI states, client tests, accessibility evidence | Can the user understand pending/failure states? |
| QA Specialist | Defect prevention and credible verification | Test design, coverage, mutation, load evidence | Could the test pass while the business rule is broken? |
| DevOps/SRE Engineer | Deployability, observability, and recovery | CI, IaC, SLOs, runbooks, recovery exercises | Can this be rolled back and diagnosed safely? |
| Security Reviewer | Least privilege, privacy, abuse resistance | Threat analysis, scan evidence, audit controls | What data or authority can an attacker gain? |
| Incident Commander | Coordinated restoration and communication | Timeline, decisions, status updates, follow-ups | What protects customers now, and who owns each action? |

## Responsibility Matrix

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Product scope and backlog order | Product Owner | Product Owner | Analyst, Engineering Lead | Team |
| Domain boundary or public contract | System Analyst/Domain Lead | Architecture Lead | Security, QA, consumers | Team |
| Reservation invariant change | Reservation Developer | Reservation Lead | QA, Checkout, SRE | Product Owner |
| Payment workflow change | Checkout Developer | Checkout Lead | Security, Reservation, QA | Support/SRE |
| Test strategy and release evidence | QA Specialist | QA Lead | Domain teams, SRE | Product Owner |
| CI/CD and infrastructure | DevOps Engineer | SRE Lead | Security, domain teams | Team |
| Production incident | Operations Lead | Incident Commander | Domain experts, Communications | Stakeholders |
| Release approval | Engineering and QA Leads | Product Owner | Security/SRE for critical changes | Team |

## Rotation and Handoff

Development and QA responsibilities rotate between sprints so each team member
can defend more than one viewpoint. Production on-call rotates weekly as defined
in [`../architecture-and-operations/incident-management.md`](../architecture-and-operations/incident-management.md).
Every handoff records active work, known risks, temporary controls, failed tests,
recent deployments, and the next decision owner.

