# DAOGuillotine // Decentralized Contributor Payout Auditor

[![GenLayer v0.2.16 Compatible](https://img.shields.io/badge/GenLayer-v0.2.16-00F0FF?style=for-the-badge&logo=python)](https://genlayer.com)
[![Build Status](https://img.shields.io/badge/Tests-7%2F7%20PASSING-10B981?style=for-the-badge)](https://github.com/Tannpd/DAOGuillotine)
[![Live Web dApp](https://img.shields.io/badge/Vercel-LIVE%20dAPP-000000?style=for-the-badge&logo=vercel)](https://daoguillotine-app.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-F43F5E?style=for-the-badge)](LICENSE)

---

## 📌 Problem Overview
In Web3 DAOs, contributor payrolls and bounties frequently suffer from "fake work" (e.g. corporate fluff, Telegram meeting-spam, unfulfilled deliverables) or improper DAO withholding. 

**DAOGuillotine** locks contributor salary/bounties into an autonomous smart contract vault bound to shared, immutable acceptance criteria, leveraging GenLayer AI Lead Auditors to cross-examine deliverables against acceptance criteria and optional DAO counter-evidence.

---

## 🏛️ Architecture & Verification Command

### Passing GenLayer Validation & Unit Test Command

To verify the Intelligent Contract syntax, state machine, and consensus safety rules, execute:

```bash
# Run 100% automated test suite
python -m unittest discover -s tests -p "test_*.py" -v
```

Output:
```text
test_create_payroll_requires_non_empty_criteria ... ok
test_prevent_evidence_replacement_after_audit_commences ... ok
test_reclaim_requires_failed_audit_status ... ok
test_reproducible_compilation ... ok
test_strict_boolean_validation_rejects_string_boolean ... ok
test_submit_work_proof_stage1_and_challenge_window ... ok
test_unauthorized_domain_origin_rejected ... ok

Ran 7 tests in 0.007s
OK
```

---

## 🛡️ Security & Lifecycle Safeguards

1. **Shared, Immutable Acceptance Criteria**: `create_payroll` mandates a non-empty `acceptance_criteria_url` that becomes permanently immutable upon escrow creation.
2. **Multi-Stage Dispute Lifecycle & Challenge Window**: `submit_work_proof` submits work proof (Stage 1) and opens the DAO Challenge Window (`status = "DISPUTED"`), allowing the DAO admin to attach counter-evidence (`submit_counter_evidence`) before AI audit resolution.
3. **Evidence Replacement Lock**: Once AI audit commences (`request_salary_and_audit`), claim evidence and counter-evidence URLs are locked on-chain (`payroll_audit_opened`). Attempting to overwrite evidence raises `UserError("Evidence replacement is locked once audit has commenced.")`.
4. **Failed-Audit Deposit Reclaim Protection**: Restricts `reclaim_timed_out_payroll` so locked deposits can ONLY be reclaimed if audit has officially failed (`status == "FAILED"`), preventing premature drain of active payrolls.
5. **Fail-Closed Consensus & Strict Boolean Safety**: Rejects string boolean coercions and returns `FAILED` on scrape errors to preserve deposit funds safely.

---

## ⚙️ Contract API Summary

* `create_payroll(contributor: Address, acceptance_criteria_url: str) -> int` (payable)
* `submit_work_proof(payroll_id: int, work_proof_url: str) -> None`
* `submit_counter_evidence(payroll_id: int, counter_evidence_url: str) -> None`
* `request_salary_and_audit(payroll_id: int, work_proof_url: str, counter_evidence_url: str) -> None`
* `reclaim_timed_out_payroll(payroll_id: int) -> None`
* `get_payroll(payroll_id: int) -> str`
* `get_payrolls_count() -> int`
