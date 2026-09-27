# Cut-over runbook: Dynamics AX 2012 → Dynamics 365 Business Central

A generic, reusable runbook. Times are indicative for a mid-size single legal entity.
Every step has an owner, an exit criterion and a rollback point.

## Roles

| Role | Responsibility |
|---|---|
| Migration lead (data analyst) | Runs extracts, transformation, reconciliation; owns this runbook |
| Finance controller | Signs off trial balance, AR/AP ageing and open-item totals |
| Functional consultant (BC) | Configuration packages, posting groups, number series |
| Business owners (Sales, Purchasing, Inventory) | Sign off master data samples |
| IT / infra | AX freeze, backups, BC environment, user access |

## Phase 0: Preparation (T-6 to T-2 weeks)

1. **Scope and mapping.** Agree the entity list and field mapping (`mappings/entities.yaml`). Every target field has a source or a documented default.
2. **Profiling.** Run `make profile` on a full extract. Log each issue with an owner: fix in AX, fix with a rule, or accept.
3. **Cleansing in source.** Fix what the business must own (duplicates, orphans, blocked records that should be closed).
4. **Mock migrations.** At least two full dress rehearsals into a BC sandbox. `make reconcile` must pass all checks; timings recorded.
5. **Sign-off criteria agreed in writing** (see Phase 3).

## Phase 1: Freeze and extract (T-1 day)

| # | Step | Exit criterion |
|---|---|---|
| 1.1 | Post all pending journals in AX; close the period | No unposted journals |
| 1.2 | Freeze AX (read-only roles) | Change log shows no writes after freeze time |
| 1.3 | Full database backup of AX | Backup verified with a restore test. **Rollback point A** |
| 1.4 | Extract CUSTTABLE, VENDTABLE, INVENTTABLE, CUSTTRANSOPEN, VENDTRANSOPEN, ledger balances | Row counts logged per table |
| 1.5 | Run AX standard reports: trial balance, AR ageing, AP ageing, inventory valuation | PDFs archived as the reconciliation baseline |

## Phase 2: Transform and load (T-0)

| # | Step | Exit criterion |
|---|---|---|
| 2.1 | `make migrate`: transform to BC-ready files | Rejects file reviewed; only known/accepted rejects remain |
| 2.2 | Import master data packages: G/L accounts, dimensions, posting groups, customers, vendors, items | Package import shows 0 errors |
| 2.3 | Post opening balances through general journals (G/L, customer, vendor, inventory) using a suspense account | Journals post without errors |
| 2.4 | Suspense account balance = 0 | **Rollback point B** (restore BC sandbox snapshot) |

## Phase 3: Reconcile and sign off

`make reconcile` produces `reports/reconciliation.md`. Go-live needs **all** of:

- [ ] Row accounting: source = loaded + rejected, for every entity
- [ ] Key checksums match (no altered keys)
- [ ] Open AR / AP totals per currency match to the paisa (loaded + rejected = source)
- [ ] Trial balance per account matches the AX baseline; net = 0
- [ ] Rejects are either fixed and reloaded, or signed off by the data owner with their value
- [ ] 25-record random sample per master entity checked field-by-field by the business owner
- [ ] Finance controller signs the reconciliation report

## Phase 4: Go-live and hypercare

1. Open BC to users; AX stays read-only for look-ups (archive).
2. Daily reconciliation of AR/AP ageing for the first period close.
3. Hypercare log: issue, entity, root cause, fix, owner.

## Rollback

| Trigger | Action |
|---|---|
| Any Phase 3 check fails and cannot be fixed within the cut-over window | Restore BC to rollback point B (or delete the company), unfreeze AX, reschedule |
| Critical process blocked after go-live (first 48 h) | Business decision: fix-forward in BC or revert to AX with manual re-keying of new transactions |
