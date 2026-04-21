# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Plan Templates** marketplace category. Bundled starter templates (product-launch, sprint-planning, bug-triage, research-project) plus full CRUD for user-managed custom templates. New `/api/plan-templates` endpoints and an optional `template_id` on `POST /api/plans` that seeds the new plan with the template's columns and tasks. When creating a plan in the UI, choose **Blank Plan** or **From Template**.
- Plan templates can **preassign agents** at the plan level (`agent_ids`) and at the task level (`agent_id`). Missing agent ids are silently skipped at plan-creation time. The Add Plan Template modal lets you pick agents as chips (plan-level) and dropdowns (per task), and the detail modal shows preassigned agents with a stale/missing indicator.

