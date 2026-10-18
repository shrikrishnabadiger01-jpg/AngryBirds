import React, { useEffect, useMemo, useState } from 'react';
import { Activity, ArrowLeft, ArrowRight, Check, LoaderCircle, LockKeyhole, Shield, Smartphone } from 'lucide-react';
import { api } from '../services/api';

const COUNTRIES = [
  ['IN', 'India', '+91'], ['US', 'United States', '+1'], ['GB', 'United Kingdom', '+44'],
  ['AU', 'Australia', '+61'], ['CA', 'Canada', '+1'], ['SG', 'Singapore', '+65'],
  ['AE', 'United Arab Emirates', '+971'], ['DE', 'Germany', '+49'], ['FR', 'France', '+33'],
];

export default function AuthPage({ method = 'password', error: authError = '', onAuthenticated }) {
  const [country, setCountry] = useState('IN');
  const [number, setNumber] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState('phone');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [cooldown, setCooldown] = useState(0);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const selectedCountry = useMemo(() => COUNTRIES.find(([id]) => id === country) || COUNTRIES[0], [country]);
  const phone = `${selectedCountry[2]}${number.replace(/\D/g, '')}`;
  const hasValidNumber = /^\+[1-9]\d{7,14}$/.test(phone);

  useEffect(() => {
    if (!cooldown) return undefined;
    const timer = window.setTimeout(() => setCooldown(value => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  const requestOtp = async (event) => {
    event.preventDefault();
    if (!hasValidNumber || busy || cooldown) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const response = await api.sendOtp(phone);
      setStep('code');
      setCooldown(response.resend_after || 60);
      setNotice(`Enter the six-digit code sent to ${selectedCountry[2]} ${number.replace(/\D/g, '')}.`);
    } catch (cause) {
      setError(cause.message || 'Could not send a code. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const verifyOtp = async (event) => {
    event.preventDefault();
    if (!/^\d{6}$/.test(code) || busy) return;
    setBusy(true);
    setError('');
    try {
      const user = await api.verifyOtp(phone, code);
      setCode('');
      await onAuthenticated(user);
    } catch (cause) {
      setError(cause.message || 'That code could not be verified. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const submitPassword = async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const user = await api.login(username, password);
      setPassword('');
      await onAuthenticated(user);
    } catch (cause) {
      setError(cause.message || 'Sign-in failed. Check your details and try again.');
    } finally {
      setBusy(false);
    }
  };

  const resetPhone = () => {
    setStep('phone');
    setCode('');
    setError('');
    setNotice('');
  };

  return <main className="auth-page">
    <div className="auth-ambient auth-ambient-one" aria-hidden="true" />
    <div className="auth-ambient auth-ambient-two" aria-hidden="true" />
    <section className="auth-card" aria-labelledby="auth-title">
      <header className="auth-brand">
        <span className="auth-logo"><Shield size={22} strokeWidth={1.8} /></span>
        <span><strong>IgnisGuard</strong><small>AI SECURITY PLATFORM</small></span>
        <span className="auth-secure"><LockKeyhole size={13} /> ENCRYPTED</span>
      </header>

      <div className="auth-content">
        <div className="auth-eyebrow"><span /> PRIVATE WORKSPACE</div>
        <h1 id="auth-title">Secure Access to<br />IgnisGuard</h1>
        <p className="auth-lede">Verify your identity to access the security operations workspace.</p>

        {method === 'otp' ? <>
          <div className="auth-step-indicator" aria-label={step === 'phone' ? 'Step 1 of 2: phone number' : 'Step 2 of 2: verification code'}>
            <span className={step === 'phone' ? 'current' : 'complete'}>{step === 'code' ? <Check size={13} /> : '01'}</span>
            <i className={step === 'code' ? 'complete' : ''} />
            <span className={step === 'code' ? 'current' : ''}>02</span>
            <small>{step === 'phone' ? 'PHONE NUMBER' : 'VERIFY CODE'}</small>
          </div>

          {step === 'phone' ? <form onSubmit={requestOtp} className="auth-form">
            <label className="auth-label" htmlFor="phone-number">PHONE NUMBER</label>
            <div className="auth-phone-row">
              <label className="sr-only" htmlFor="country-code">Country calling code</label>
              <select id="country-code" value={country} onChange={event => setCountry(event.target.value)} aria-label="Country calling code">
                {COUNTRIES.map(([id, name, dial]) => <option key={id} value={id}>{id} {dial}</option>)}
              </select>
              <span className="auth-phone-divider" />
              <input id="phone-number" autoComplete="tel-national" inputMode="tel" type="tel" placeholder="98765 43210" value={number} onChange={event => setNumber(event.target.value.replace(/[^\d\s()-]/g, '').slice(0, 18))} aria-describedby="phone-hint" required />
            </div>
            <small className="auth-hint" id="phone-hint">We’ll send a one-time verification code to your phone.</small>
            {error && <p className="auth-message error" role="alert">{error}</p>}
            <button className="auth-submit" type="submit" disabled={busy || !hasValidNumber}>
              {busy ? <><LoaderCircle className="auth-spin" size={17} /> Sending code</> : <>Send OTP <ArrowRight size={16} /></>}
            </button>
          </form> : <form onSubmit={verifyOtp} className="auth-form">
            <label className="auth-label" htmlFor="otp-code">SIX-DIGIT CODE</label>
            <div className="auth-code-wrap"><Smartphone size={17} /><input id="otp-code" autoComplete="one-time-code" inputMode="numeric" type="text" pattern="[0-9]{6}" maxLength={6} placeholder="000000" value={code} onChange={event => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} required /></div>
            <p className="auth-hint">{notice || `Code sent to ${phone}.`}</p>
            {error && <p className="auth-message error" role="alert">{error}</p>}
            <button className="auth-submit" type="submit" disabled={busy || code.length !== 6}>
              {busy ? <><LoaderCircle className="auth-spin" size={17} /> Verifying</> : <>Verify &amp; Continue <ArrowRight size={16} /></>}
            </button>
            <div className="auth-secondary-actions">
              <button type="button" className="auth-link" onClick={resetPhone}><ArrowLeft size={13} /> Change number</button>
              <button type="button" className="auth-link" onClick={requestOtp} disabled={busy || cooldown > 0}>{cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}</button>
            </div>
          </form>}
        </> : <form onSubmit={submitPassword} className="auth-form">
          <label className="auth-label" htmlFor="username">USERNAME</label>
          <input className="auth-text-input" id="username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required />
          <label className="auth-label auth-label-spaced" htmlFor="password">PASSWORD</label>
          <input className="auth-text-input" id="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required />
          {(error || authError) && <p className="auth-message error" role="alert">{error || authError}</p>}
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? <><LoaderCircle className="auth-spin" size={17} /> Signing in</> : <>Sign in <ArrowRight size={16} /></>}</button>
        </form>}

        <div className="auth-assurance"><Activity size={14} /><span>Protected by IgnisGuard identity verification</span></div>
      </div>
      <footer className="auth-footer"><span><i /> SYSTEM OPERATIONAL</span><span>IGNISGUARD · SECURE ACCESS</span></footer>
    </section>
    <p className="auth-outside-note">Your access is monitored and protected by security policy.</p>
  </main>;
}
