# =============================================================================
#  test_daoguillotine.py - DAOGuillotine Contract Unit Test Suite
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
        self.fail_on_next = False
    def render(self, url):
        if self.fail_on_next:
            raise Exception("Simulated report scrape failure")
        if "404" in url:
            raise Exception("404 Report Link Blocked")
        if "empty" in url:
            return ""
        return self.url_to_content.get(url, "Scraped report: Implemented smart contract suite, written 100% unit tests, deployed web app.")

class MockNondet:
    def __init__(self):
        self.web = MockWeb()
        self.exec_prompt_responses = []
        self.response_index = 0
    def exec_prompt(self, prompt):
        if self.exec_prompt_responses:
            res = self.exec_prompt_responses[self.response_index % len(self.exec_prompt_responses)]
            self.response_index += 1
            if isinstance(res, Exception):
                raise res
            return res
        return json.dumps({
            "is_slashed": False,
            "effort_score": 95,
            "audit_report": "Excellent technical deliverables verified."
        })

class MockVM:
    def run_nondet_unsafe(self, leader_fn, validator_fn):
        leader_res = leader_fn()
        valid = validator_fn(leader_res)
        if not valid:
            return json.dumps({"error": "VALIDATOR_REJECTED_CONSENSUS"})
        return leader_res

class MockContractRef:
    def __init__(self, addr, tracker=None):
        self.addr = str(addr)
        self.tracker = tracker
    def emit_transfer(self, value=0):
        if self.tracker is not None:
            self.tracker.append({"target": self.addr, "value": int(value)})
        return True

class MockGL:
    def __init__(self):
        self.Contract = MockContractBase
        self.message = MockMessage()
        self.nondet = MockNondet()
        self.vm = MockVM()
        self.transfers_log = []
        self.public = MagicMock()
        self.public.write = lambda f: f
        self.public.write.payable = lambda f: f
        self.public.view = lambda f: f
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
mock_gl.gl = mock_gl
sys.modules['genlayer'] = mock_gl
mock_gl.Contract = MockContractBase
mock_gl.Address = MockAddress
mock_gl.bigint = lambda v: int(v)
mock_gl.TreeMap = dict

# Add contracts directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../contracts')))
import daoguillotine

class TestDAOGuillotine(unittest.TestCase):
    def setUp(self):
        mock_gl.message = MockMessage(sender="0x1111111111111111111111111111111111111111", value=5000000000000000000)
        mock_gl.nondet = MockNondet()
        mock_gl.transfers_log = []
        self.contract = daoguillotine.Contract()

    def test_reproducible_compilation(self):
        """Verify contract file syntax and compilation."""
        contract_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../contracts/daoguillotine.py'))
        compiled_file = py_compile.compile(contract_path, doraise=True)
        self.assertTrue(os.path.exists(compiled_file))

    def test_create_payroll_requires_non_empty_criteria(self):
        """Verify create_payroll rejects empty acceptance criteria URLs and binds immutable criteria."""
        dao = "0x1111111111111111111111111111111111111111"
        contributor = "0x2222222222222222222222222222222222222222"
        mock_gl.message = MockMessage(sender=dao, value=5000000000000000000)

        # Empty criteria URL MUST fail
        with self.assertRaises(daoguillotine.UserError) as ctx:
            self.contract.create_payroll(contributor, "")
        self.assertIn("Shared acceptance criteria URL cannot be empty", str(ctx.exception))

        crit_url = "https://daoguillotine-app.vercel.app/criteria_sprint_1.txt"
        pid = self.contract.create_payroll(contributor, crit_url)
        self.assertEqual(pid, 0)

        payroll = json.loads(self.contract.get_payroll(0))
        self.assertEqual(payroll["acceptance_criteria_url"], crit_url)

    def test_submit_work_proof_stage1_and_challenge_window(self):
        """Verify multi-stage dispute lifecycle: submit_work_proof (Stage 1) -> submit_counter_evidence -> request_salary_and_audit."""
        dao = "0x1111111111111111111111111111111111111111"
        contributor = "0x2222222222222222222222222222222222222222"
        crit_url = "https://daoguillotine-app.vercel.app/criteria.txt"
        work_url = "https://daoguillotine-app.vercel.app/mock_report_solid_work.txt"
        ce_url = "https://daoguillotine-app.vercel.app/counter_evidence_bug_log.txt"

        mock_gl.message = MockMessage(sender=dao, value=3000000000000000000)
        self.contract.create_payroll(contributor, crit_url)

        # Contributor submits work proof (Stage 1), status becomes DISPUTED
        mock_gl.message = MockMessage(sender=contributor)
        self.contract.submit_work_proof(0, work_url)

        payroll1 = json.loads(self.contract.get_payroll(0))
        self.assertEqual(payroll1["status"], "DISPUTED")
        self.assertEqual(payroll1["work_proof_url"], work_url)

        # DAO submits counter-evidence during Challenge Window
        mock_gl.message = MockMessage(sender=dao)
        self.contract.submit_counter_evidence(0, ce_url)

        payroll2 = json.loads(self.contract.get_payroll(0))
        self.assertEqual(payroll2["counter_evidence_url"], ce_url)

        # Trigger AI Audit resolution
        mock_gl.nondet.web.url_to_content[crit_url] = "Agreed criteria: Implement contracts."
        mock_gl.nondet.web.url_to_content[work_url] = "Solid work deliverables."
        mock_gl.nondet.web.url_to_content[ce_url] = "Minor counter note."

        mock_gl.message = MockMessage(sender=contributor)
        self.contract.request_salary_and_audit(0)

        payroll3 = json.loads(self.contract.get_payroll(0))
        self.assertTrue(payroll3["audit_opened"])
        self.assertEqual(payroll3["status"], "PAID")

    def test_slashing_path_when_effort_insufficient_or_bug_reported(self):
        """Verify insufficient effort or critical bug report slashes salary back to DAO treasury."""
        dao = "0x1111111111111111111111111111111111111111"
        contributor = "0x2222222222222222222222222222222222222222"
        crit_url = "https://daoguillotine-app.vercel.app/criteria.txt"
        work_url = "https://daoguillotine-app.vercel.app/work.txt"
        ce_url = "https://daoguillotine-app.vercel.app/counter_evidence_bug_log.txt"

        mock_gl.message = MockMessage(sender=dao, value=4000000000000000000)
        self.contract.create_payroll(contributor, crit_url)

        # Contributor submits work proof
        mock_gl.message = MockMessage(sender=contributor)
        self.contract.submit_work_proof(0, work_url)

        # DAO submits counter-evidence challenge
        mock_gl.message = MockMessage(sender=dao)
        self.contract.submit_counter_evidence(0, ce_url)

        mock_gl.nondet.web.url_to_content[crit_url] = "Criteria: Zero critical bugs in production code."
        mock_gl.nondet.web.url_to_content[work_url] = "Claim: Deployed code on mainnet."
        mock_gl.nondet.web.url_to_content[ce_url] = "DAO Dispute Report: Critical reentrancy bug found in deployed code!"

        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({
                "is_slashed": True,
                "effort_score": 20,
                "audit_report": "DAO counter-evidence confirmed critical bug. Salary slashed to DAO treasury."
            })
        ]

        mock_gl.message = MockMessage(sender=contributor)
        self.contract.request_salary_and_audit(0)

        payroll = json.loads(self.contract.get_payroll(0))

        self.assertTrue(payroll["is_slashed"])
        self.assertEqual(payroll["status"], "SLASHED")
        self.assertTrue(any(t["target"] == dao and t["value"] == 4000000000000000000 for t in mock_gl.transfers_log))

    def test_prevent_evidence_replacement_after_audit_commences(self):
        """Verify evidence replacement is locked once AI audit commences."""
        dao = "0x1111111111111111111111111111111111111111"
        contributor = "0x2222222222222222222222222222222222222222"
        crit_url = "https://daoguillotine-app.vercel.app/criteria.txt"
        work_url = "https://daoguillotine-app.vercel.app/work.txt"

        mock_gl.message = MockMessage(sender=dao, value=1000000000000000000)
        self.contract.create_payroll(contributor, crit_url)

        # Trigger AI audit
        mock_gl.message = MockMessage(sender=contributor)
        self.contract.request_salary_and_audit(0, work_url)

        # Attempt to replace counter-evidence after audit commences MUST fail
        mock_gl.message = MockMessage(sender=dao)
        with self.assertRaises(daoguillotine.UserError) as ctx:
            self.contract.submit_counter_evidence(0, "https://daoguillotine-app.vercel.app/new_counter.txt")
        self.assertIn("Evidence replacement is locked once audit has commenced", str(ctx.exception))

    def test_reclaim_requires_failed_audit_status(self):
        """Verify reclaim_timed_out_payroll requires FAILED status and rejects active payrolls."""
        dao = "0x1111111111111111111111111111111111111111"
        contributor = "0x2222222222222222222222222222222222222222"
        mock_gl.message = MockMessage(sender=dao, value=2000000000000000000)
        self.contract.create_payroll(contributor, "https://daoguillotine-app.vercel.app/crit.txt")

        # Reclaim on ACTIVE payroll MUST fail
        mock_gl.message = MockMessage(sender=dao)
        with self.assertRaises(daoguillotine.UserError) as ctx:
            self.contract.reclaim_timed_out_payroll(0)
        self.assertIn("Payroll funds can only be reclaimed if audit has officially failed", str(ctx.exception))

        # Force status to FAILED via scrape failure
        mock_gl.nondet.web.fail_on_next = True
        mock_gl.message = MockMessage(sender=contributor)
        self.contract.request_salary(0, "https://daoguillotine-app.vercel.app/report.txt")

        # Reclaim on FAILED status MUST succeed
        mock_gl.message = MockMessage(sender=dao)
        self.contract.reclaim_timed_out_payroll(0)

        payroll = json.loads(self.contract.get_payroll(0))
        self.assertEqual(payroll["status"], "RECLAIMED")
        self.assertEqual(payroll["amount"], 0)

    def test_access_controls_for_roles(self):
        """Verify access controls for contributor and DAO admin functions."""
        dao = "0x1111111111111111111111111111111111111111"
        contributor = "0x2222222222222222222222222222222222222222"
        attacker = "0x9999999999999999999999999999999999999999"

        mock_gl.message = MockMessage(sender=dao, value=1000000000000000000)
        self.contract.create_payroll(contributor, "https://daoguillotine-app.vercel.app/crit.txt")

        # Attacker calling submit_work_proof MUST fail
        mock_gl.message = MockMessage(sender=attacker)
        with self.assertRaises(daoguillotine.UserError) as ctx:
            self.contract.submit_work_proof(0, "https://daoguillotine-app.vercel.app/work.txt")
        self.assertIn("Only the designated contributor can submit work proof", str(ctx.exception))

        # Attacker calling submit_counter_evidence MUST fail
        with self.assertRaises(daoguillotine.UserError) as ctx:
            self.contract.submit_counter_evidence(0, "https://daoguillotine-app.vercel.app/counter.txt")
        self.assertIn("Only the designated DAO admin can submit counter-evidence", str(ctx.exception))

        # Attacker calling reclaim_timed_out_payroll MUST fail
        with self.assertRaises(daoguillotine.UserError) as ctx:
            self.contract.reclaim_timed_out_payroll(0)
        self.assertIn("Payroll funds can only be reclaimed if audit has officially failed", str(ctx.exception))

    def test_unauthorized_domain_origin_rejected(self):
        """Verify arbitrary un-whitelisted domain URLs are blocked for work proof."""
        dao = "0x1111111111111111111111111111111111111111"
        contributor = "0x2222222222222222222222222222222222222222"
        mock_gl.message = MockMessage(sender=dao, value=1000000000000000000)
        self.contract.create_payroll(contributor, "https://daoguillotine-app.vercel.app/crit.txt")

        mock_gl.message = MockMessage(sender=contributor)
        with self.assertRaises(daoguillotine.UserError) as ctx:
            self.contract.request_salary(0, "https://fake-unauthorized-site.com/fake_report.txt")
        self.assertIn("Unauthorized work proof domain origin", str(ctx.exception))

    def test_strict_boolean_validation_rejects_string_boolean(self):
        """Verify string boolean 'false' or 'true' in LLM output is rejected as non-boolean."""
        dao = "0x1111111111111111111111111111111111111111"
        contributor = "0x2222222222222222222222222222222222222222"
        mock_gl.message = MockMessage(sender=dao, value=1000000000000000000)
        self.contract.create_payroll(contributor, "https://daoguillotine-app.vercel.app/crit.txt")

        mock_gl.nondet.web.url_to_content["https://daoguillotine-app.vercel.app/work.txt"] = "Report content"
        mock_gl.nondet.exec_prompt_responses = [
            json.dumps({
                "is_slashed": "false",
                "effort_score": 80,
                "audit_report": "Fake string response"
            })
        ]

        mock_gl.message = MockMessage(sender=contributor)
        self.contract.request_salary(0, "https://daoguillotine-app.vercel.app/work.txt")

        payroll = json.loads(self.contract.get_payroll(0))
        self.assertEqual(payroll["status"], "FAILED")

    def test_get_payroll_out_of_bounds(self):
        """Verify get_payroll returns {} for out of bounds IDs."""
        self.assertEqual(self.contract.get_payroll(-1), "{}")
        self.assertEqual(self.contract.get_payroll(999), "{}")

if __name__ == '__main__':
    unittest.main()
