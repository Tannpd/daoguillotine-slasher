# ⚔️ DAOGuillotine - Decentralized Contributor Payout & Anti-Fluff Auditor

> **Category**: GenLayer Intelligent Contracts & Governance Escrow  
> **Target Framework**: GenLayer v0.2.16  
> **Status**: Production-Ready / 100% Automated Unit Test Coverage (9/9 Passed)

---

## 📌 Executive Summary & Purpose

DAOGuillotine holds contributor salaries and bounties in escrow, protecting DAO treasuries from corporate fluff, meeting spam, and unfulfilled commitments. 

Unlike traditional manual multisig payrolls or subjective admin approvals:
1. **Shared Acceptance Criteria Binding**: When a DAO creates a payroll escrow (`create_payroll`), both the DAO and contributor are bound to a shared acceptance criteria URL (`acceptance_criteria_url`) defining tangible deliverables.
2. **Authenticated Evidence & Domain Safeguards**: Contributor submits authenticated work proof URLs (`work_proof_url`) originating from authorized domains (`https://daoguillotine-app.vercel.app/`, `https://github.com/`, `https://gitlab.com/`).
3. **Counter-Evidence & Challenge Path**: The DAO can submit counter-evidence (`counter_evidence_url` / `submit_counter_evidence`) to challenge contributor claims or report critical bugs/unmet criteria.
4. **GenLayer AI Consensus Audit**: GenLayer AI validators scrape ALL 3 sources (Acceptance Criteria, Contributor Work Proof, and DAO Counter-Evidence), cross-examining deliverables and calculating an effort score (0-100).
5. **Atomic Settlement & Timeout Recovery**: If effort score < 50 or criteria breached (`is_slashed = true`), 100% of locked funds are slashed back to the DAO treasury. If deliverables are verified, funds release to the contributor. If a claim is abandoned or fails, the DAO can execute `reclaim_timed_out_payroll` to recover their deposit.

---

## 📐 Architecture & Flowchart

```
+---------------------------------------------------------------------------------------------------+
|                                            DAO TREASURY                                           |
+--------------------------------------------------+------------------------------------------------+
                                                   |
                         1. create_payroll(contributor, acceptance_criteria_url)
                         [Locks GEN salary deposit & binds agreed deliverables criteria]
                                                   |
                                                   v
+---------------------------------------------------------------------------------------------------+
|                                  DAOGuillotine Intelligent Vault                                  |
|                                    (contracts/daoguillotine.py)                                   |
+--------------------------------------------------+------------------------------------------------+
                                                   |
            +--------------------------------------+--------------------------------------+
            |                                                                             |
 2a. request_salary(work_proof_url)                                2b. submit_counter_evidence(counter_evidence_url)
 [Contributor submits work proof]                                   [DAO submits challenge counter-evidence]
            |                                                                             |
            +--------------------------------------+--------------------------------------+
                                                   |
                                                   v
+---------------------------------------------------------------------------------------------------+
|                                   GenLayer Non-Deterministic VM                                   |
|                             gl.vm.run_nondet_unsafe(leader_fn, validator_fn)                    |
+--------------------------------------------------+------------------------------------------------+
                                                   |
        +------------------------------------------+------------------------------------------+
        |                                          |                                          |
        v                                          v                                          v
gl.nondet.web.render(crit_url)             gl.nondet.web.render(work_url)            gl.nondet.web.render(ce_url)
[Agreed Acceptance Criteria]               [Contributor Work Proof]                  [DAO Counter-Evidence]
        |                                          |                                          |
        +------------------------------------------+------------------------------------------+
                                                   |
                                                   v
                                     gl.nondet.exec_prompt(...)
                        [Cross-examines deliverables vs criteria & counter-evidence]
                                                   |
                           +-----------------------+-----------------------+
                           |                                               |
                           v                                               v
            [Slashed (Effort Score < 50)]                      [Approved (Effort Score >= 50)]
                           |                                               |
                           v                                               v
        +-------------------------------------+         +-------------------------------------+
        | Refund 100% Deposit to DAO Treasury |         | Release 100% Salary to Contributor  |
        | Status: SLASHED                     |         | Status: PAID                        |
        +-------------------------------------+         +-------------------------------------+
```

---

## 🔒 Key Security & Safety Rules

1. **Shared Acceptance Criteria Binding**:
   - Every payroll is bound to an `acceptance_criteria_url` stored on-chain at escrow creation.
2. **Counter-Evidence Challenge Path**:
   - `submit_counter_evidence()` allows DAO admins to challenge claims and submit counter-evidence reports before audit execution.
3. **Timeout Recovery Path**:
   - `reclaim_timed_out_payroll()` enables the DAO to recover 100% locked deposit if a claim fails or is abandoned.
4. **Authorized Domain Origin Safeguards**:
   - Enforces URL domain validation (`https://daoguillotine-app.vercel.app/`, `https://github.com/`, `https://gitlab.com/`).
5. **Fail-Closed Consensus Security**:
   - If web scraping or LLM execution fails, `validator_fn` agreement sets status to `FAILED`, preserving escrow deposit safely.

---

## 🧪 Automated Unit Test Verification (9/9 Passed)

```powershell
cd D:\Gen\DAOGuillotine
python -m unittest discover -s tests -p "test_*.py" -v
```

### Test Suite Results:
* `test_create_payroll_payable_deposit`: **OK** (Locks deposit & binds shared acceptance criteria).
* `test_request_salary_contributor_payment_success`: **OK** (Solid work report approves salary payout to contributor).
* `test_request_salary_dao_refund_slashed`: **OK** (Fluff/meeting spam slashes salary back to DAO treasury).
* `test_submit_counter_evidence_and_challenge`: **OK** (DAO counter-evidence challenge path verified).
* `test_reclaim_timed_out_payroll`: **OK** (DAO timeout recovery path reclaims deposit).
* `test_unauthorized_domain_origin_rejected`: **OK** (Arbitrary un-whitelisted domain URLs are blocked).
* `test_request_salary_access_control_unauthorized`: **OK** (Rejects unauthorized third party callers).
* `test_strict_boolean_validation_rejects_string_boolean`: **OK** (Rejects string `"false"` injection attempts).
* `test_validator_rerun_scrape_failure_rejects_consensus`: **OK** (Fail-closed safety preserves escrow on scrape failure).
