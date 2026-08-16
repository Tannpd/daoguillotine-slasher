# =============================================================================
#  test_daoguillotine.py - DAOGuillotine v0.2.17 Unit Test Suite
#
#  Steward Fixes Verified:
#  Fix 1 — Per-party evidence locking (work proof + counter-evidence)
#  Fix 2 — Measurable challenge window deadline (audit blocked until closed)
#  Fix 3 — Enforced recovery deadline (reclaim blocked until timeout)
# =============================================================================

import sys
import os
import json
import unittest
import py_compile
from unittest.mock import MagicMock

# --- Mocking structure to simulate the GenLayer SDK runtime ------------------
class MockContractBase:
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        for name, type_hint in getattr(cls, '__annotations__', {}).items():
            if 'dict' in str(type_hint) or 'TreeMap' in str(type_hint):
                setattr(instance, name, dict())
        return instance

class MockMessage:
    def __init__(self, sender="0x1111111111111111111111111111111111111111", value=0):
        self.sender_address = sender
        self.value = value

class MockWeb:
    def __init__(self):
        self.url_to_content = {}
        self.fail_on_next   = False
    def render(self, url):
        if self.fail_on_next:
            raise Exception("Simulated report scrape failure")
        if "404" in url:
            raise Exception("404 Report Link Blocked")
        if "empty" in url:
            return ""
        return self.url_to_content.get(
            url,
            "Scraped report: Implemented smart contract suite, written 100% unit tests, deployed web app."
        )

class MockNondet:
    def __init__(self):
        self.web                  = MockWeb()
        self.exec_prompt_responses = []
        self.response_index       = 0

    def exec_prompt(self, prompt):
        if self.exec_prompt_responses:
            res = self.exec_prompt_responses[self.response_index % len(self.exec_prompt_responses)]
            self.response_index += 1
            if isinstance(res, Exception):
                raise res
            return res
        # Default: window closed + good audit result
        if "window_closed" in prompt or "deadline_passed" in prompt:
            return json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True,
                               "deadline_passed": True, "reasoning": "Deadline passed."})
        return json.dumps({
            "is_slashed":   False,
            "effort_score": 95,
            "audit_report": "Excellent technical deliverables verified."
        })

class MockVM:
    def run_nondet_unsafe(self, leader_fn, validator_fn):
        leader_res = leader_fn()
        valid      = validator_fn(leader_res)
        if not valid:
            return json.dumps({"error": "VALIDATOR_REJECTED_CONSENSUS"})
        return leader_res

class MockContractRef:
    def __init__(self, addr, tracker=None):
        self.addr    = str(addr)
        self.tracker = tracker
    def emit_transfer(self, value=0):
        if self.tracker is not None:
            self.tracker.append({"target": self.addr, "value": int(value)})
        return True

class MockGL:
    def __init__(self):
        self.Contract      = MockContractBase
        self.message       = MockMessage()
        self.nondet        = MockNondet()
        self.vm            = MockVM()
        self.transfers_log = []
        self.public        = MagicMock()
        self.public.write  = lambda f: f
        self.public.write.payable = lambda f: f
        self.public.view   = lambda f: f
    def get_contract_at(self, addr):
        return MockContractRef(addr, self.transfers_log)

class MockAddress:
    def __init__(self, val):
        self.val = str(val)
    def __str__(self):
        return self.val
    def __repr__(self):
        return f"Address('{self.val}')"

mock_gl = MockGL()
mock_gl.gl      = mock_gl
sys.modules['genlayer'] = mock_gl
mock_gl.Contract = MockContractBase
mock_gl.Address  = MockAddress
mock_gl.bigint   = lambda v: int(v)
mock_gl.TreeMap  = dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../contracts')))
import daoguillotine

UserError = daoguillotine.UserError

# ---------------------------------------------------------------------------
# Shared Test Constants
# ---------------------------------------------------------------------------
DAO         = "0x1111111111111111111111111111111111111111"
CONTRIBUTOR = "0x2222222222222222222222222222222222222222"
ATTACKER    = "0x9999999999999999999999999999999999999999"
STAKE       = 5_000_000_000_000_000_000   # 5 GEN

CRIT_URL    = "https://github.com/dao/project/blob/main/criteria_sprint_1.txt"
WORK_URL    = "https://github.com/contributor/project/blob/main/report.md"
CE_URL      = "https://github.com/dao/project/blob/main/counter_evidence.txt"
TIME_URL    = "https://worldtimeapi.org/api/timezone/UTC"

# Deadline: far-future (already passed for window_closed=True in mock)
CHALLENGE_DEADLINE  = 1800000000   # far future Unix ts (mocked as passed)
RECOVERY_DEADLINE   = 1800086400   # challenge + 1 day


def _make_payroll(challenge_deadline=CHALLENGE_DEADLINE, recovery_deadline=RECOVERY_DEADLINE,
                  stake=STAKE, crit_url=CRIT_URL):
    """Helper: DAO creates a payroll, returns (contract, pid)."""
    mock_gl.message = MockMessage(sender=DAO, value=stake)
    c = daoguillotine.Contract()
    pid = c.create_payroll(CONTRIBUTOR, crit_url, challenge_deadline, recovery_deadline)
    return c, pid


class TestDAOGuillotine(unittest.TestCase):

    def setUp(self):
        mock_gl.message       = MockMessage(sender=DAO, value=STAKE)
        mock_gl.nondet        = MockNondet()
        mock_gl.transfers_log = []
        self.contract         = daoguillotine.Contract()

    # ===================================================================
    # 1. Contract compiles
    # ===================================================================
    def test_reproducible_compilation(self):
        """Contract file must compile without syntax errors."""
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../contracts/daoguillotine.py'))
        compiled = py_compile.compile(path, doraise=True)
        self.assertTrue(os.path.exists(compiled))

    # ===================================================================
    # 2. create_payroll validation
    # ===================================================================
    def test_create_payroll_requires_non_empty_criteria(self):
        """Empty acceptance criteria URL must be rejected."""
        mock_gl.message = MockMessage(sender=DAO, value=STAKE)
        with self.assertRaises(UserError) as ctx:
            self.contract.create_payroll(CONTRIBUTOR, "", CHALLENGE_DEADLINE, RECOVERY_DEADLINE)
        self.assertIn("Shared acceptance criteria URL cannot be empty", str(ctx.exception))

    def test_create_payroll_stores_deadlines(self):
        """Both deadlines must be stored and readable via get_payroll."""
        c, pid = _make_payroll()
        payroll = json.loads(c.get_payroll(pid))
        self.assertEqual(payroll["challenge_deadline_ts"], CHALLENGE_DEADLINE)
        self.assertEqual(payroll["recovery_deadline_ts"],  RECOVERY_DEADLINE)
        self.assertFalse(payroll["work_proof_locked"])
        self.assertFalse(payroll["counter_evidence_locked"])

    def test_create_payroll_rejects_past_challenge_deadline(self):
        """challenge_deadline_ts before 2025-01-01 must be rejected."""
        mock_gl.message = MockMessage(sender=DAO, value=STAKE)
        with self.assertRaises(UserError) as ctx:
            self.contract.create_payroll(CONTRIBUTOR, CRIT_URL, 1000000000, RECOVERY_DEADLINE)
        self.assertIn("valid future Unix timestamp", str(ctx.exception))

    def test_create_payroll_rejects_recovery_before_challenge(self):
        """recovery_deadline_ts < challenge_deadline_ts must be rejected."""
        mock_gl.message = MockMessage(sender=DAO, value=STAKE)
        with self.assertRaises(UserError) as ctx:
            self.contract.create_payroll(CONTRIBUTOR, CRIT_URL, CHALLENGE_DEADLINE, CHALLENGE_DEADLINE - 1)
        self.assertIn("recovery_deadline_ts must be >=", str(ctx.exception))

    # ===================================================================
    # FIX 1: Per-party evidence locking
    # ===================================================================
    def test_fix1_work_proof_locks_on_first_submission(self):
        """FIX 1: Work proof URL locks immediately after first submit — replacement raises UserError."""
        c, pid = _make_payroll()

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        payroll = json.loads(c.get_payroll(pid))
        self.assertTrue(payroll["work_proof_locked"])
        self.assertEqual(payroll["work_proof_url"], WORK_URL)
        self.assertEqual(payroll["status"], "DISPUTED")

        # Attempt to replace work proof MUST fail
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        with self.assertRaises(UserError) as ctx:
            c.submit_work_proof(pid, "https://github.com/contributor/project/blob/main/new_report.md")
        self.assertIn("permanently locked", str(ctx.exception))

    def test_fix1_counter_evidence_locks_on_first_submission(self):
        """FIX 1: Counter-evidence URL locks immediately after first submit — replacement raises UserError."""
        c, pid = _make_payroll()

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        mock_gl.message = MockMessage(sender=DAO)
        c.submit_counter_evidence(pid, CE_URL)

        payroll = json.loads(c.get_payroll(pid))
        self.assertTrue(payroll["counter_evidence_locked"])
        self.assertEqual(payroll["counter_evidence_url"], CE_URL)

        # Attempt to replace counter-evidence MUST fail
        mock_gl.message = MockMessage(sender=DAO)
        with self.assertRaises(UserError) as ctx:
            c.submit_counter_evidence(pid, "https://github.com/dao/project/blob/main/new_counter.txt")
        self.assertIn("permanently locked", str(ctx.exception))

    def test_fix1_work_proof_and_counter_evidence_independent_locks(self):
        """FIX 1: Each party's lock is independent — one party locking doesn't affect the other."""
        c, pid = _make_payroll()

        # Contributor submits and locks
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        # DAO has NOT submitted yet — counter-evidence is still open
        payroll = json.loads(c.get_payroll(pid))
        self.assertTrue(payroll["work_proof_locked"])
        self.assertFalse(payroll["counter_evidence_locked"])

        # DAO can still submit counter-evidence for the first time
        mock_gl.message = MockMessage(sender=DAO)
        c.submit_counter_evidence(pid, CE_URL)

        payroll2 = json.loads(c.get_payroll(pid))
        self.assertTrue(payroll2["counter_evidence_locked"])

    # ===================================================================
    # FIX 2: Challenge window — audit blocked until deadline passes
    # ===================================================================
    def test_fix2_audit_blocked_when_challenge_window_open(self):
        """FIX 2: Audit must be blocked if challenge window has not closed (window_closed=False)."""
        c, pid = _make_payroll()

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        # Mock time oracle: window_closed = False (challenge window still open)
        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({"current_unix_timestamp": 1000000000, "window_closed": False,
                        "reasoning": "Current time is before challenge deadline."}),
            json.dumps({"current_unix_timestamp": 1000000000, "window_closed": False,
                        "reasoning": "Validator: window still open."}),
        ]

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.request_salary_and_audit(pid, TIME_URL)

        payroll = json.loads(c.get_payroll(pid))
        # Must be FAILED — either CHALLENGE_WINDOW_OPEN or VALIDATOR_REJECTED_CONSENSUS
        # Both outcomes correctly block payout when the challenge window is still open
        self.assertEqual(payroll["status"], "FAILED")
        self.assertTrue(
            "CHALLENGE_WINDOW_OPEN" in payroll["audit_report"] or
            "VALIDATOR_REJECTED_CONSENSUS" in payroll["audit_report"],
            f"Unexpected audit_report: {payroll['audit_report']}"
        )
        self.assertEqual(payroll["amount"], STAKE)   # Funds preserved


    def test_fix2_audit_proceeds_after_challenge_window_closes(self):
        """FIX 2: Audit executes normally after challenge window has closed (window_closed=True)."""
        c, pid = _make_payroll()

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        mock_gl.message = MockMessage(sender=DAO)
        c.submit_counter_evidence(pid, CE_URL)

        # Mock responses: 1st call = window check (closed), 2nd call = audit result
        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True,
                        "reasoning": "Challenge window closed."}),
            json.dumps({"is_slashed": False, "effort_score": 90,
                        "audit_report": "Excellent deliverables verified post challenge window."}),
            # Validator repeats both
            json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True,
                        "reasoning": "Validator: window closed."}),
            json.dumps({"is_slashed": False, "effort_score": 90,
                        "audit_report": "Validator confirms."}),
        ]

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.request_salary_and_audit(pid, TIME_URL)

        payroll = json.loads(c.get_payroll(pid))
        self.assertEqual(payroll["status"], "PAID")
        self.assertTrue(any(t["target"] == CONTRIBUTOR and t["value"] == STAKE
                            for t in mock_gl.transfers_log))

    def test_fix2_unauthorized_time_domain_rejected_for_audit(self):
        """FIX 2: Time source URL for audit must be from AUTHORIZED_TIME_DOMAINS."""
        c, pid = _make_payroll()
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        with self.assertRaises(UserError) as ctx:
            c.request_salary_and_audit(pid, "https://attacker-clock.evil.io/now")
        self.assertIn("authoritative time service", str(ctx.exception))

    # ===================================================================
    # FIX 3: Enforced recovery deadline
    # ===================================================================
    def test_fix3_reclaim_blocked_before_recovery_deadline(self):
        """FIX 3: Reclaim is blocked if recovery_deadline_ts has not yet passed."""
        c, pid = _make_payroll()

        # Force FAILED status via scrape failure
        mock_gl.nondet.web.fail_on_next = True
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)
        mock_gl.nondet.web.fail_on_next = False

        # Manually set status to FAILED for test isolation
        c.payroll_status[str(pid)] = "FAILED"
        c.payroll_amount[str(pid)] = STAKE

        # Mock time oracle: deadline NOT passed
        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({"current_unix_timestamp": 1800000001, "deadline_passed": False,
                        "reasoning": "Current time before recovery deadline."}),
            json.dumps({"current_unix_timestamp": 1800000001, "deadline_passed": False,
                        "reasoning": "Validator confirms not passed."}),
        ]

        mock_gl.message = MockMessage(sender=DAO)
        with self.assertRaises(UserError) as ctx:
            c.reclaim_timed_out_payroll(pid, TIME_URL)
        self.assertIn("Recovery deadline has not yet passed", str(ctx.exception))

    def test_fix3_reclaim_succeeds_after_recovery_deadline(self):
        """FIX 3: Reclaim succeeds after recovery_deadline_ts has passed via time oracle."""
        c, pid = _make_payroll()

        # Set FAILED state directly for test isolation
        c.payroll_status[str(pid)] = "FAILED"
        c.payroll_amount[str(pid)] = STAKE

        # Mock time oracle: deadline HAS passed
        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({"current_unix_timestamp": 9999999999, "deadline_passed": True,
                        "reasoning": "Current time exceeds recovery deadline."}),
            json.dumps({"current_unix_timestamp": 9999999999, "deadline_passed": True,
                        "reasoning": "Validator confirms deadline passed."}),
        ]

        mock_gl.message = MockMessage(sender=DAO)
        c.reclaim_timed_out_payroll(pid, TIME_URL)

        payroll = json.loads(c.get_payroll(pid))
        self.assertEqual(payroll["status"], "RECLAIMED")
        self.assertEqual(payroll["amount"], 0)
        self.assertTrue(any(t["target"] == DAO and t["value"] == STAKE
                            for t in mock_gl.transfers_log))

    def test_fix3_reclaim_requires_failed_status(self):
        """FIX 3: Reclaim on ACTIVE or DISPUTED payroll must fail regardless of deadline."""
        c, pid = _make_payroll()

        mock_gl.message = MockMessage(sender=DAO)
        with self.assertRaises(UserError) as ctx:
            c.reclaim_timed_out_payroll(pid, TIME_URL)
        self.assertIn("Payroll funds can only be reclaimed if audit has officially failed", str(ctx.exception))

    def test_fix3_unauthorized_time_domain_rejected_for_reclaim(self):
        """FIX 3: Time source URL for reclaim must be from AUTHORIZED_TIME_DOMAINS."""
        c, pid = _make_payroll()
        c.payroll_status[str(pid)] = "FAILED"
        c.payroll_amount[str(pid)] = STAKE

        mock_gl.message = MockMessage(sender=DAO)
        with self.assertRaises(UserError) as ctx:
            c.reclaim_timed_out_payroll(pid, "http://localhost:5173/fake_time.json")
        self.assertIn("authoritative time service", str(ctx.exception))

    # ===================================================================
    # Happy Path — Full Lifecycle
    # ===================================================================
    def test_full_lifecycle_paid_path(self):
        """Full lifecycle: create → submit proof → submit counter → audit → PAID."""
        c, pid = _make_payroll(stake=STAKE)

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        mock_gl.message = MockMessage(sender=DAO)
        c.submit_counter_evidence(pid, CE_URL)

        # Window closed, good audit
        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True, "reasoning": "Closed."}),
            json.dumps({"is_slashed": False, "effort_score": 85, "audit_report": "Solid work."}),
            json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True, "reasoning": "Closed."}),
            json.dumps({"is_slashed": False, "effort_score": 85, "audit_report": "Validator agrees."}),
        ]
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.request_salary_and_audit(pid, TIME_URL)

        payroll = json.loads(c.get_payroll(pid))
        self.assertEqual(payroll["status"], "PAID")
        self.assertFalse(payroll["is_slashed"])
        self.assertTrue(any(t["target"] == CONTRIBUTOR and t["value"] == STAKE
                            for t in mock_gl.transfers_log))

    def test_full_lifecycle_slashed_path(self):
        """Full lifecycle: create → submit proof → counter-evidence → audit → SLASHED."""
        c, pid = _make_payroll(stake=STAKE)

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        mock_gl.message = MockMessage(sender=DAO)
        c.submit_counter_evidence(pid, CE_URL)

        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True, "reasoning": "Closed."}),
            json.dumps({"is_slashed": True, "effort_score": 20, "audit_report": "Critical bug confirmed."}),
            json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True, "reasoning": "Closed."}),
            json.dumps({"is_slashed": True, "effort_score": 20, "audit_report": "Validator confirms slash."}),
        ]
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.request_salary_and_audit(pid, TIME_URL)

        payroll = json.loads(c.get_payroll(pid))
        self.assertEqual(payroll["status"], "SLASHED")
        self.assertTrue(payroll["is_slashed"])
        self.assertTrue(any(t["target"] == DAO and t["value"] == STAKE
                            for t in mock_gl.transfers_log))

    # ===================================================================
    # Access Control
    # ===================================================================
    def test_access_control_submit_work_proof_only_contributor(self):
        """Only the designated contributor can submit work proof."""
        c, pid = _make_payroll()

        mock_gl.message = MockMessage(sender=ATTACKER)
        with self.assertRaises(UserError) as ctx:
            c.submit_work_proof(pid, WORK_URL)
        self.assertIn("Only the designated contributor", str(ctx.exception))

    def test_access_control_submit_counter_evidence_only_dao(self):
        """Only the designated DAO admin can submit counter-evidence."""
        c, pid = _make_payroll()
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        mock_gl.message = MockMessage(sender=ATTACKER)
        with self.assertRaises(UserError) as ctx:
            c.submit_counter_evidence(pid, CE_URL)
        self.assertIn("Only the designated DAO admin", str(ctx.exception))

    def test_access_control_reclaim_only_dao(self):
        """Only the DAO admin can reclaim failed payroll funds."""
        c, pid = _make_payroll()
        c.payroll_status[str(pid)] = "FAILED"
        c.payroll_amount[str(pid)] = STAKE

        mock_gl.message = MockMessage(sender=ATTACKER)
        with self.assertRaises(UserError) as ctx:
            c.reclaim_timed_out_payroll(pid, TIME_URL)
        self.assertIn("Only the designated DAO admin can reclaim", str(ctx.exception))

    # ===================================================================
    # Domain / URL validation
    # ===================================================================
    def test_unauthorized_work_proof_domain_rejected(self):
        """Work proof from non-whitelisted domain is rejected."""
        c, pid = _make_payroll()
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        with self.assertRaises(UserError) as ctx:
            c.submit_work_proof(pid, "https://fake-unauthorized-site.com/report.txt")
        self.assertIn("Unauthorized work proof domain origin", str(ctx.exception))

    def test_unauthorized_counter_evidence_domain_rejected(self):
        """Counter-evidence from non-whitelisted domain is rejected."""
        c, pid = _make_payroll()
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        mock_gl.message = MockMessage(sender=DAO)
        with self.assertRaises(UserError) as ctx:
            c.submit_counter_evidence(pid, "https://attacker.io/fake_counter.txt")
        self.assertIn("Unauthorized counter-evidence domain origin", str(ctx.exception))

    # ===================================================================
    # Strict boolean validation
    # ===================================================================
    def test_strict_boolean_rejects_string_is_slashed(self):
        """AI returning string 'false' for is_slashed is rejected (fail-closed → FAILED)."""
        c, pid = _make_payroll()
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True, "reasoning": "Closed."}),
            json.dumps({"is_slashed": "false", "effort_score": 80, "audit_report": "String exploit."}),
        ]

        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.request_salary_and_audit(pid, TIME_URL)

        payroll = json.loads(c.get_payroll(pid))
        self.assertEqual(payroll["status"], "FAILED")

    # ===================================================================
    # Scrape / network failure → FAILED, funds preserved
    # ===================================================================
    def test_failed_scrape_preserves_funds(self):
        """If work proof URL cannot be scraped, status=FAILED and funds are preserved."""
        c, pid = _make_payroll(stake=STAKE)
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.submit_work_proof(pid, WORK_URL)

        # Window closed, then scrape fails
        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({"current_unix_timestamp": 9999999999, "window_closed": True, "reasoning": "Closed."}),
        ]
        mock_gl.nondet.web.fail_on_next = True
        mock_gl.message = MockMessage(sender=CONTRIBUTOR)
        c.request_salary_and_audit(pid, TIME_URL)

        payroll = json.loads(c.get_payroll(pid))
        self.assertEqual(payroll["status"], "FAILED")
        self.assertEqual(payroll["amount"], STAKE)

    # ===================================================================
    # Read-only edge cases
    # ===================================================================
    def test_get_payroll_out_of_bounds(self):
        """get_payroll returns {} for out-of-bounds IDs."""
        self.assertEqual(self.contract.get_payroll(-1),  "{}")
        self.assertEqual(self.contract.get_payroll(999), "{}")

    def test_zero_stake_rejected(self):
        """create_payroll with 0 GEN must be rejected."""
        mock_gl.message = MockMessage(sender=DAO, value=0)
        with self.assertRaises(UserError) as ctx:
            self.contract.create_payroll(CONTRIBUTOR, CRIT_URL, CHALLENGE_DEADLINE, RECOVERY_DEADLINE)
        self.assertIn("positive GEN salary amount", str(ctx.exception))

    def test_zero_address_contributor_rejected(self):
        """create_payroll with zero-address contributor must be rejected."""
        mock_gl.message = MockMessage(sender=DAO, value=STAKE)
        with self.assertRaises(UserError) as ctx:
            self.contract.create_payroll(
                "0x0000000000000000000000000000000000000000",
                CRIT_URL, CHALLENGE_DEADLINE, RECOVERY_DEADLINE
            )
        self.assertIn("Invalid contributor address", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
