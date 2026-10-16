import React from 'react';
import { Shield, Key, ExternalLink, X, Copy, Check, AlertCircle } from 'lucide-react';

export default function GmailSetupModal({ isOpen, onClose }) {
  const [copied, setCopied] = React.useState(false);

  if (!isOpen) return null;

  const redirectUri = 'http://localhost:8000/api/gmail/callback';

  const handleCopy = () => {
    navigator.clipboard.writeText(redirectUri);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 9999,
      background: 'rgba(2, 6, 5, 0.85)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
    }}>
      <div className="glass-panel" style={{
        maxWidth: '580px',
        width: '100%',
        background: 'rgba(10, 28, 23, 0.95)',
        border: '1.5px solid rgba(16, 185, 129, 0.35)',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8), 0 0 30px rgba(16, 185, 129, 0.15)',
        padding: '28px',
        position: 'relative',
      }}>
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
          }}
        >
          <X size={18} />
        </button>

        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '18px' }}>
          <div className="brand-logo" style={{ width: '38px', height: '38px' }}>
            <Key size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#ffffff' }}>
              Google OAuth Setup Required
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Enable read-only Gmail access with Google Cloud OAuth 2.0
            </p>
          </div>
        </div>

        {/* Security Notice */}
        <div style={{
          padding: '12px 14px',
          borderRadius: '10px',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          fontSize: '12px',
          color: '#a7f3d0',
          marginBottom: '20px',
          lineHeight: 1.5,
        }}>
          <strong>Security Guarantee: </strong>
          IgnisGuard requests only the minimum read-only scope (<code>gmail.readonly</code>). It cannot send, forward, delete, or modify emails. Tokens are encrypted server-side in SQLite and never reach the browser.
        </div>

        {/* Setup Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '12.5px', marginBottom: '24px' }}>
          <div>
            <strong style={{ color: '#ffffff' }}>Step 1: </strong>
            <span style={{ color: 'var(--text-secondary)' }}>
              Visit <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noreferrer" style={{ color: '#34d399', textDecoration: 'underline' }}>Google Cloud Console Credentials</a> and create an <strong>OAuth 2.0 Client ID</strong> (Web Application).
            </span>
          </div>

          <div>
            <strong style={{ color: '#ffffff' }}>Step 2: </strong>
            <span style={{ color: 'var(--text-secondary)' }}>Set the Authorized Redirect URI to:</span>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#020605',
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)',
              marginTop: '6px',
              fontFamily: 'var(--font-mono)',
              fontSize: '11.5px',
              color: '#34d399',
            }}>
              <span>{redirectUri}</span>
              <button
                type="button"
                onClick={handleCopy}
                style={{
                  background: 'none',
                  border: 'none',
                  color: copied ? '#10b981' : 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                }}
              >
                {copied ? <Check size={13} /> : <Copy size={13} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          <div>
            <strong style={{ color: '#ffffff' }}>Step 3: </strong>
            <span style={{ color: 'var(--text-secondary)' }}>
              Open <code style={{ color: '#5eead4' }}>backend/.env</code> and paste your Client ID & Secret:
            </span>
            <pre style={{
              background: '#020605',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '10px 12px',
              marginTop: '6px',
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              color: '#94a3b8',
              lineHeight: 1.5,
            }}>
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com{'\n'}
GOOGLE_CLIENT_SECRET=your_client_secret
            </pre>
          </div>

          <div>
            <strong style={{ color: '#ffffff' }}>Step 4: </strong>
            <span style={{ color: 'var(--text-secondary)' }}>
              Restart your backend server, then click <strong>Gmail Integration</strong> to log in.
            </span>
          </div>
        </div>

        {/* Footer Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button
            type="button"
            onClick={onClose}
            className="btn-approve"
            style={{ padding: '9px 18px', fontSize: '13px' }}
          >
            Got It
          </button>
        </div>
      </div>
    </div>
  );
}
