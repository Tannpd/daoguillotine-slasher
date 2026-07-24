import React, { useState, useEffect } from 'react';
import { 
  useDAOGuillotine, 
  formatGen 
} from './useDAOGuillotine';
import { 
  ShieldCheck, 
  Wallet, 
  PlusCircle, 
  FolderOpen, 
  Lock, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  ExternalLink,
  Coins,
  TrendingUp,
  Scale,
  Sparkles,
  RefreshCw
} from 'lucide-react';

export default function App() {
  const {
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
    requestSalary,
    contractAddress
  } = useDAOGuillotine();

  const [activeTab, setActiveTab] = useState('CREATE_PAYROLL'); // CREATE_PAYROLL or CABINET
  const [selectedPayrollId, setSelectedPayrollId] = useState(null);
  
  // Form inputs
  const [contributorInput, setContributorInput] = useState('');
  const [amountInput, setAmountInput] = useState('5.0');
  const [workProofUrlInput, setWorkProofUrlInput] = useState('');

  const selectedPayroll = payrolls.find(p => Number(p.id) === Number(selectedPayrollId));

  // Auto select first payroll
  useEffect(() => {
    if (activeTab === 'CABINET' && payrolls.length > 0 && selectedPayrollId === null) {
      setSelectedPayrollId(payrolls[0].id);
    }
  }, [activeTab, payrolls, selectedPayrollId]);

  const handleCreatePayroll = async (e) => {
    e.preventDefault();
    if (!contributorInput || !amountInput) return;
    try {
      await createPayroll(contributorInput, amountInput);
      setContributorInput('');
      setAmountInput('5.0');
      setActiveTab('CABINET');
      setSelectedPayrollId(0);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRequestSalary = async (e) => {
    e.preventDefault();
    if (!workProofUrlInput || selectedPayrollId === null) return;
    try {
      await requestSalary(selectedPayrollId, workProofUrlInput);
      setWorkProofUrlInput('');
    } catch (err) {
      console.error(err);
    }
  };

  // Compute stat summary metrics
  const paidCount = payrolls.filter(p => p.status === 'PAID').length;
  const slashedCount = payrolls.filter(p => p.status === 'SLASHED').length;
  const activeCount = payrolls.filter(p => p.status === 'ACTIVE').length;

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="brand-logo">
          <div className="brand-icon-box">
            <Scale size={24} />
          </div>
          <div>
            <div className="brand-title">DAOGuillotine</div>
            <div className="brand-subtitle">AI Contributor Audit & Escrow Protocol (GenLayer v0.2.16)</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ background: '#111622', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '6px 14px', fontSize: '12px', color: 'var(--primary-cyan)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981', boxShadow: '0 0 8px #10B981' }} />
            StudioNet Connected
          </div>

          {address ? (
            <div style={{ background: 'var(--primary-cyan-dim)', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '10px', padding: '8px 16px', color: '#FFF', fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wallet size={16} color="var(--primary-cyan)" />
              {address.slice(0, 6)}...{address.slice(-4)}
            </div>
          ) : (
            <button onClick={connectWallet} className="btn-primary" style={{ width: 'auto', padding: '10px 20px', fontSize: '14px' }}>
              <Wallet size={16} />
              Connect Wallet
            </button>
          )}
        </div>
      </header>

      {/* Stats Overview Bar */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span>TOTAL PAYROLLS</span>
            <FolderOpen size={16} color="var(--primary-cyan)" />
          </div>
          <div className="stat-value">{payrolls.length}</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>ACTIVE ESCROW BALANCE</span>
            <Coins size={16} color="var(--primary-cyan)" />
          </div>
          <div className="stat-value" style={{ color: 'var(--primary-cyan)' }}>
            {formatGen(contractBalance)} GEN
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>DISBURSED (PAID)</span>
            <CheckCircle2 size={16} color="var(--emerald-success)" />
          </div>
          <div className="stat-value" style={{ color: 'var(--emerald-success)' }}>{paidCount}</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>SLASHED & REFUNDED</span>
            <AlertCircle size={16} color="var(--rose-slash)" />
          </div>
          <div className="stat-value" style={{ color: 'var(--rose-slash)' }}>{slashedCount}</div>
        </div>
      </div>

      {/* Main Content Area */}
      <main>
        {/* Navigation Tabs */}
        <div className="tabs-header">
          <button 
            onClick={() => setActiveTab('CREATE_PAYROLL')}
            className={`tab-btn ${activeTab === 'CREATE_PAYROLL' ? 'active' : ''}`}
          >
            <PlusCircle size={18} />
            Create Escrow Bounty
          </button>
          <button 
            onClick={() => {
              setActiveTab('CABINET');
              fetchPayrollsState();
            }}
            className={`tab-btn ${activeTab === 'CABINET' ? 'active' : ''}`}
          >
            <FolderOpen size={18} />
            Dossier Repository ({payrolls.length})
          </button>
        </div>

        {error && (
          <div style={{ background: 'var(--rose-dim)', border: '1px solid rgba(244, 63, 94, 0.4)', borderRadius: '12px', padding: '16px 20px', color: '#FDA4AF', fontSize: '13px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={18} color="var(--rose-slash)" />
            <span>{error}</span>
          </div>
        )}

        {/* Tab 1: CREATE_PAYROLL */}
        {activeTab === 'CREATE_PAYROLL' && (
          <div style={{ maxWidth: '680px', margin: '0 auto' }}>
            <div className="glass-panel">
              <div className="panel-title">
                <Lock size={22} color="var(--primary-cyan)" />
                Deposit & Lock Contributor Bounty
              </div>
              <p className="panel-desc">
                DAO locks native GEN tokens in escrow for a specified contributor. Funds remain securely locked until audited by GenLayer AI.
              </p>

              <form onSubmit={handleCreatePayroll}>
                <div className="form-group">
                  <label className="form-label">CONTRIBUTOR RECIPIENT ADDRESS</label>
                  <input 
                    type="text" 
                    placeholder="0x90F8bf651d130c507982e1cfd84d12A9c0fFd2Ef" 
                    value={contributorInput}
                    onChange={(e) => setContributorInput(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">SALARY AMOUNT TO LOCK (GEN)</label>
                  <input 
                    type="number" 
                    step="0.001" 
                    min="0.001"
                    placeholder="5.0" 
                    value={amountInput}
                    onChange={(e) => setAmountInput(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>

                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? (
                    <>
                      <RefreshCw size={18} className="animate-spin" />
                      Creating Payroll Escrow...
                    </>
                  ) : (
                    <>
                      <PlusCircle size={18} />
                      Lock Bounty & Create Dossier
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Tab 2: CABINET / REPOSITORY */}
        {activeTab === 'CABINET' && (
          <div>
            {payrolls.length === 0 ? (
              <div className="glass-panel" style={{ textAlign: 'center', padding: '60px 20px' }}>
                <FolderOpen size={48} color="var(--text-dim)" style={{ margin: '0 auto 16px auto' }} />
                <h3 style={{ fontSize: '18px', color: '#FFF', marginBottom: '8px' }}>No Payroll Dossiers Found</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '24px' }}>
                  Create your first payroll bounty in the "Create Escrow Bounty" tab.
                </p>
                <button onClick={() => setActiveTab('CREATE_PAYROLL')} className="btn-primary" style={{ width: 'auto' }}>
                  Create First Payroll
                </button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
                {/* Dossiers List Sidebar */}
                <div className="dossier-list">
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.5px', marginBottom: '4px', textTransform: 'uppercase' }}>
                    SELECT DOSSIER ({payrolls.length})
                  </div>

                  {payrolls.map((p) => (
                    <div 
                      key={p.id}
                      onClick={() => setSelectedPayrollId(p.id)}
                      className={`dossier-item ${Number(selectedPayrollId) === Number(p.id) ? 'selected' : ''}`}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontFamily: 'var(--font-heading)', fontSize: '16px', fontWeight: 700, color: '#FFF' }}>
                          Case #{p.id}
                        </span>
                        <span className={`badge ${p.status === 'PAID' ? 'badge-paid' : p.status === 'SLASHED' ? 'badge-slashed' : 'badge-active'}`}>
                          {p.status}
                        </span>
                      </div>

                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        Contributor: {p.contributor.slice(0, 6)}...{p.contributor.slice(-4)}
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--primary-cyan)', marginTop: '4px' }}>
                        {formatGen(p.amount)} GEN
                      </div>
                    </div>
                  ))}
                </div>

                {/* Selected Dossier Details */}
                <div>
                  {selectedPayroll && (
                    <div className="glass-panel">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
                        <div>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>DOSSIER REFERENCE</div>
                          <div style={{ fontFamily: 'var(--font-heading)', fontSize: '24px', fontWeight: 800, color: '#FFF' }}>
                            Case #{selectedPayroll.id}
                          </div>
                        </div>

                        <span className={`badge ${selectedPayroll.status === 'PAID' ? 'badge-paid' : selectedPayroll.status === 'SLASHED' ? 'badge-slashed' : 'badge-active'}`} style={{ fontSize: '14px', padding: '8px 18px' }}>
                          {selectedPayroll.status === 'PAID' && <CheckCircle2 size={16} />}
                          {selectedPayroll.status === 'SLASHED' && <AlertCircle size={16} />}
                          {selectedPayroll.status === 'ACTIVE' && <Sparkles size={16} />}
                          {selectedPayroll.status}
                        </span>
                      </div>

                      {/* Detail Info Grid */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                        <div style={{ background: '#0D1017', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '14px 18px' }}>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>DAO SOURCE (ESCROW OWNER)</div>
                          <div style={{ fontSize: '12px', color: '#FFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>{selectedPayroll.dao}</div>
                        </div>

                        <div style={{ background: '#0D1017', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '14px 18px' }}>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>CONTRIBUTOR RECIPIENT</div>
                          <div style={{ fontSize: '12px', color: '#FFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>{selectedPayroll.contributor}</div>
                        </div>
                      </div>

                      <div style={{ background: 'var(--primary-cyan-dim)', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '12px', padding: '16px 20px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>LOCKED ESCROW AMOUNT</span>
                        <span style={{ fontFamily: 'var(--font-heading)', fontSize: '24px', fontWeight: 800, color: 'var(--primary-cyan)' }}>
                          {formatGen(selectedPayroll.amount)} GEN
                        </span>
                      </div>

                      {/* Progress Gauge */}
                      {selectedPayroll.effort_score > 0 && (
                        <div style={{ marginBottom: '24px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px' }}>
                            <span>AI PRODUCTIVITY GAUGED VALUE</span>
                            <span style={{ color: selectedPayroll.is_slashed ? 'var(--rose-slash)' : 'var(--emerald-success)' }}>
                              {selectedPayroll.effort_score}% EFFORT SCORE
                            </span>
                          </div>
                          <div className="progress-bar-track">
                            <div 
                              className={`progress-bar-fill ${selectedPayroll.effort_score >= 50 ? 'high' : 'low'}`}
                              style={{ width: `${selectedPayroll.effort_score}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Audit Decree Box */}
                      {selectedPayroll.audit_report && (
                        <div className={`decree-box ${selectedPayroll.status === 'PAID' ? 'paid' : selectedPayroll.status === 'SLASHED' ? 'slashed' : ''}`}>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: selectedPayroll.status === 'PAID' ? 'var(--emerald-success)' : selectedPayroll.status === 'SLASHED' ? 'var(--rose-slash)' : 'var(--primary-cyan)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                            <ShieldCheck size={16} />
                            GENLAYER AI AUDITOR DECREE LOG
                          </div>
                          <div style={{ fontStyle: 'italic', fontSize: '14px', color: '#E2E8F0', lineHeight: '22px' }}>
                            "{selectedPayroll.audit_report}"
                          </div>

                          {selectedPayroll.work_proof_url && (
                            <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px dashed var(--border-color)', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ color: 'var(--text-muted)' }}>VERIFIED REPORT URL:</span>
                              <a 
                                href={selectedPayroll.work_proof_url} 
                                target="_blank" 
                                rel="noreferrer" 
                                style={{ color: 'var(--primary-cyan)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                              >
                                {selectedPayroll.work_proof_url}
                                <ExternalLink size={12} />
                              </a>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Action Form */}
                      <div style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid var(--border-color)' }}>
                        {selectedPayroll.status === 'ACTIVE' ? (
                          <div>
                            {(address.toLowerCase() === selectedPayroll.contributor.toLowerCase() || address.toLowerCase() === selectedPayroll.dao.toLowerCase()) ? (
                              <div>
                                <div style={{ background: 'var(--primary-cyan-dim)', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '12px', padding: '14px 18px', fontSize: '13px', color: '#A5F3FC', marginBottom: '20px' }}>
                                  Authenticated Role Recognized // {address.toLowerCase() === selectedPayroll.contributor.toLowerCase() ? "Contributor" : "DAO Admin"}. Submit your work proof URL below to trigger AI auditing.
                                </div>

                                {/* Preset Fill Buttons */}
                                <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                                  <button
                                    type="button"
                                    className="preset-btn preset-btn-cyan"
                                    onClick={() => setWorkProofUrlInput('https://daoguillotine-slasher.vercel.app/mock_report_solid_work.txt')}
                                  >
                                    <Sparkles size={14} />
                                    + Fill Solid Work Report (Payout)
                                  </button>

                                  <button
                                    type="button"
                                    className="preset-btn preset-btn-rose"
                                    onClick={() => setWorkProofUrlInput('https://daoguillotine-slasher.vercel.app/mock_report_fluff_meetings.txt')}
                                  >
                                    <AlertCircle size={14} />
                                    + Fill Fluff Meetings Report (Slash & Refund DAO)
                                  </button>
                                </div>

                                <form onSubmit={handleRequestSalary}>
                                  <div className="form-group">
                                    <label className="form-label">WORK PROOF URL (GitHub Gist, Notion Doc, Blog Link)</label>
                                    <input 
                                      type="text" 
                                      placeholder="https://daoguillotine-slasher.vercel.app/mock_report_solid_work.txt" 
                                      value={workProofUrlInput || 'https://daoguillotine-slasher.vercel.app/mock_report_solid_work.txt'}
                                      onChange={(e) => setWorkProofUrlInput(e.target.value)}
                                      className="form-input"
                                      required
                                    />
                                  </div>

                                  <button type="submit" className="btn-primary" disabled={loading}>
                                    {loading ? (
                                      <>
                                        <RefreshCw size={18} className="animate-spin" />
                                        Auditing Work Report via AI Nodes...
                                      </>
                                    ) : (
                                      <>
                                        <ShieldCheck size={18} />
                                        Trigger AI Audit & Settle Payout
                                      </>
                                    )}
                                  </button>
                                </form>
                              </div>
                            ) : (
                              <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px', background: '#0D1017', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                                Awaiting contributor claim. Connected wallet is not a recognized party for this payroll.
                              </div>
                            )}
                          </div>
                        ) : (
                          <div style={{ background: '#0D1017', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'center', fontSize: '13px' }}>
                            Dossier Finalized. Payout settled or refunded to DAO. State locked on-chain.
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
