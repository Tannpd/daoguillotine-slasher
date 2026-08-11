import { useState, useCallback, useEffect } from 'react';
import { createClient, createAccount } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';

const CONTRACT_ADDRESS = '0xf44474179A2F07deDF14C6043608dF6d7a7D978A';

// Custom chain that proxies RPC through Vercel same-origin to bypass browser CORS policies
const getRpcEndpoint = () => {
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return `${window.location.origin}/api/rpc`;
  }
  return 'https://studio.genlayer.com/api';
};

const customStudionet = {
  ...studionet,
  rpcUrls: {
    default: { http: [getRpcEndpoint()] },
    public: { http: [getRpcEndpoint()] },
  }
};

let _readClient = null;

function getReadClient() {
  if (!_readClient) {
    _readClient = createClient({ chain: customStudionet });
  }
  return _readClient;
}

function getWriteClient(account) {
  return createClient({ chain: customStudionet, account });
}

// Convert Wei (u256) to human readable GEN string
export function formatGen(weiVal) {
  if (!weiVal) return '0';
  try {
    const big = BigInt(weiVal);
    const integerPart = big / 10n**18n;
    const fractionalPart = big % 10n**18n;
    let fractionStr = fractionalPart.toString().padStart(18, '0');
    fractionStr = fractionStr.replace(/0+$/, ''); // Trim trailing zeros
    if (fractionStr === '') {
      return integerPart.toString();
    }
    return `${integerPart}.${fractionStr.slice(0, 4)}`;
  } catch (e) {
    return '0';
  }
}

// Convert human readable GEN input to Wei (u256 BigInt)
export function parseGen(genVal) {
  if (!genVal || genVal.toString().trim() === '') return 0n;
  try {
    const parts = genVal.toString().split('.');
    let integerPart = parts[0] || '0';
    let fractionalPart = parts[1] || '';
    fractionalPart = fractionalPart.slice(0, 18).padEnd(18, '0');
    return BigInt(integerPart) * 10n**18n + BigInt(fractionalPart);
  } catch (e) {
    return 0n;
  }
}

export function useDAOGuillotine() {
  const [address, setAddress] = useState('');
  const [glAccount, setGlAccount] = useState(null);
  const [payrolls, setPayrolls] = useState([]);
  const [contractBalance, setContractBalance] = useState('0');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [txHash, setTxHash] = useState('');
  const [txStatus, setTxStatus] = useState('');

  // Connect Wallet (MetaMask/ethereum provider or fallback ephemeral account)
  const connectWallet = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      if (typeof window !== 'undefined' && window.ethereum) {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const addr = accounts[0].toLowerCase();
        setAddress(addr);
        setGlAccount(addr);
      } else {
        // Ephemeral account fallback
        let savedKey = localStorage.getItem('__daoguillotine_sk');
        let acct;
        if (savedKey) {
          acct = createAccount(savedKey);
        } else {
          acct = createAccount();
          localStorage.setItem('__daoguillotine_sk', acct.privateKey);
        }
        const addr = acct.address.toLowerCase();
        setAddress(addr);
        setGlAccount(acct);
      }
    } catch (err) {
      console.error('Wallet connection failed:', err);
      setError('Wallet connection failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch all payrolls and contract balance
  const fetchPayrollsState = useCallback(async () => {
    if (!CONTRACT_ADDRESS || CONTRACT_ADDRESS === '0x0000000000000000000000000000000000000000') return;
    setLoading(true);
    try {
      const client = getReadClient();
      
      // Get the number of payrolls
      const rawCount = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_payrolls_count',
        args: [],
      });
      const count = Number(rawCount);
      
      const fetchedPayrolls = [];
      for (let i = 0; i < count; i++) {
        const rawPayroll = await client.readContract({
          address: CONTRACT_ADDRESS,
          functionName: 'get_payroll',
          args: [i],
        });
        if (rawPayroll && rawPayroll !== '{}') {
          const payrollObj = JSON.parse(rawPayroll);
          fetchedPayrolls.push(payrollObj);
        }
      }
      
      // Get balance of contract
      const rawBalance = await client.getBalance({ address: CONTRACT_ADDRESS });
      setContractBalance(rawBalance.toString());
      
      setPayrolls(fetchedPayrolls.reverse()); // Show newest first
      setError('');
    } catch (err) {
      console.error('Error fetching payrolls:', err);
      setError('Failed to fetch payrolls: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Create Payroll (DAO locks funds with acceptance criteria)
  const createPayroll = async (contributorAddress, depositAmt, acceptanceCriteriaUrl) => {
    if (!glAccount || !CONTRACT_ADDRESS) {
      throw new Error('Wallet not connected');
    }
    setLoading(true);
    setError('');
    setTxHash('');
    setTxStatus(`Locking salary/bounty of ${depositAmt} GEN for contributor ${contributorAddress}...`);

    try {
      const client = getWriteClient(glAccount);
      const valueWei = parseGen(depositAmt);
      
      const hash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: 'create_payroll',
        args: [contributorAddress.trim(), acceptanceCriteriaUrl.trim()],
        value: valueWei,
      });
      
      setTxHash(hash);
      setTxStatus('Transmitting payroll payload. Locking funds in the Guillotine Vault...');

      const receipt = await client.waitForTransactionReceipt({ hash });
      
      const leaderReceipt = receipt.consensus_data?.leader_receipt?.[0];
      if (leaderReceipt && leaderReceipt.execution_result === 'ERROR') {
        const errorMsg = leaderReceipt.genvm_result?.stderr || 'Contract execution error';
        throw new Error(errorMsg);
      }

      setTxStatus('Success! Salary locked with immutable criteria.');
      await fetchPayrollsState();
      return receipt;
    } catch (err) {
      console.error('Payroll creation failed:', err);
      setError(err.message || 'Transaction failed');
      setTxStatus('Failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Stage 1: Submit Work Proof (Opens DAO Challenge Window)
  const submitWorkProof = async (payrollId, workProofUrl) => {
    if (!glAccount || !CONTRACT_ADDRESS) {
      throw new Error('Wallet not connected');
    }
    setLoading(true);
    setError('');
    setTxHash('');
    setTxStatus(`Submitting work proof for Payroll #${payrollId}...`);

    try {
      const client = getWriteClient(glAccount);
      const hash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: 'submit_work_proof',
        args: [Number(payrollId), workProofUrl.trim()],
      });
      
      setTxHash(hash);
      setTxStatus('Filing work proof & opening DAO Challenge Window...');

      const receipt = await client.waitForTransactionReceipt({ hash });
      
      const leaderReceipt = receipt.consensus_data?.leader_receipt?.[0];
      if (leaderReceipt && leaderReceipt.execution_result === 'ERROR') {
        const errorMsg = leaderReceipt.genvm_result?.stderr || 'Contract execution error';
        throw new Error(errorMsg);
      }

      setTxStatus('Success! Work proof submitted. Challenge Window open.');
      await fetchPayrollsState();
      return receipt;
    } catch (err) {
      console.error('Work proof submission failed:', err);
      setError(err.message || 'Transaction failed');
      setTxStatus('Failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Submit Counter Evidence (DAO challenges claim during Challenge Window)
  const submitCounterEvidence = async (payrollId, counterEvidenceUrl) => {
    if (!glAccount || !CONTRACT_ADDRESS) {
      throw new Error('Wallet not connected');
    }
    setLoading(true);
    setError('');
    setTxHash('');
    setTxStatus(`Attaching DAO counter-evidence for dispute on Payroll #${payrollId}...`);

    try {
      const client = getWriteClient(glAccount);
      const hash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: 'submit_counter_evidence',
        args: [Number(payrollId), counterEvidenceUrl.trim()],
      });
      
      setTxHash(hash);
      setTxStatus('Submitting counter-evidence challenge to contract state...');

      const receipt = await client.waitForTransactionReceipt({ hash });
      
      const leaderReceipt = receipt.consensus_data?.leader_receipt?.[0];
      if (leaderReceipt && leaderReceipt.execution_result === 'ERROR') {
        const errorMsg = leaderReceipt.genvm_result?.stderr || 'Transaction error';
        throw new Error(errorMsg);
      }

      setTxStatus('Success! Counter-evidence attached.');
      await fetchPayrollsState();
      return receipt;
    } catch (err) {
      console.error('Counter-evidence submission failed:', err);
      setError(err.message || 'Transaction failed');
      setTxStatus('Failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Reclaim Timed Out Payroll (DAO recovers abandoned deposit upon failed audit)
  const reclaimTimedOutPayroll = async (payrollId) => {
    if (!glAccount || !CONTRACT_ADDRESS) {
      throw new Error('Wallet not connected');
    }
    setLoading(true);
    setError('');
    setTxHash('');
    setTxStatus(`Reclaiming locked GEN deposit via timeout recovery path for Payroll #${payrollId}...`);

    try {
      const client = getWriteClient(glAccount);
      const hash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: 'reclaim_timed_out_payroll',
        args: [Number(payrollId)],
      });
      
      setTxHash(hash);
      setTxStatus('Executing timeout recovery path...');

      const receipt = await client.waitForTransactionReceipt({ hash });
      
      const leaderReceipt = receipt.consensus_data?.leader_receipt?.[0];
      if (leaderReceipt && leaderReceipt.execution_result === 'ERROR') {
        const errorMsg = leaderReceipt.genvm_result?.stderr || 'Transaction error';
        throw new Error(errorMsg);
      }

      setTxStatus('Success! Escrow funds reclaimed to DAO treasury.');
      await fetchPayrollsState();
      return receipt;
    } catch (err) {
      console.error('Timeout reclaim failed:', err);
      setError(err.message || 'Transaction failed');
      setTxStatus('Failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Request Salary & Trigger AI Audit (Locks evidence & triggers settlement)
  const requestSalary = async (payrollId, workProofUrl = '', counterEvidenceUrl = '') => {
    if (!glAccount || !CONTRACT_ADDRESS) {
      throw new Error('Wallet not connected');
    }
    setLoading(true);
    setError('');
    setTxHash('');
    setTxStatus(`Submitting work report for audit. Triggering Ruthless Tech Lead assessment...`);

    try {
      const client = getWriteClient(glAccount);
      const hash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: 'request_salary_and_audit',
        args: [Number(payrollId), workProofUrl.trim(), counterEvidenceUrl.trim()],
      });
      
      setTxHash(hash);
      setTxStatus('Auditors are scraping your report URL, scanning deliverables against criteria & counter-evidence. Executing AI prompt. Please wait 15-30s...');

      const receipt = await client.waitForTransactionReceipt({ hash });
      
      const leaderReceipt = receipt.consensus_data?.leader_receipt?.[0];
      if (leaderReceipt && leaderReceipt.execution_result === 'ERROR') {
        const errorMsg = leaderReceipt.genvm_result?.stderr || 'Audit execution error';
        throw new Error(errorMsg);
      }

      setTxStatus('Success! AI Audit processed. Funds disbursed/refunded.');
      await fetchPayrollsState();
      return receipt;
    } catch (err) {
      console.error('Salary request failed:', err);
      setError(err.message || 'Transaction failed');
      setTxStatus('Failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Auto-fetch on connect
  useEffect(() => {
    if (address && CONTRACT_ADDRESS) {
      fetchPayrollsState();
    }
  }, [address, fetchPayrollsState]);

  return {
    address,
    glAccount,
    payrolls,
    contractBalance,
    loading,
    error,
    txHash,
    txStatus,
    connectWallet,
    fetchPayrollsState,
    createPayroll,
    submitWorkProof,
    submitCounterEvidence,
    reclaimTimedOutPayroll,
    requestSalary,
    contractAddress: CONTRACT_ADDRESS,
  };
}
