import { useState } from 'react';

const s = {
  badge: {
    display: 'inline-flex', alignItems: 'center', padding: '2px 8px',
    borderRadius: 999, fontSize: 11, fontWeight: 600, letterSpacing: .4,
  },
  btn: {
    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px',
    borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600,
    fontSize: 13, transition: 'opacity .15s',
  },
  card: {
    background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 'var(--radius)', padding: 20,
  },
  input: {
    width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontSize: 13,
    outline: 'none', transition: 'border-color .15s',
  },
  label: { display: 'block', fontSize: 12, color: 'var(--text-dim)', marginBottom: 5, fontWeight: 600 },
  th: {
    padding: '10px 14px', textAlign: 'left', fontSize: 11,
    color: 'var(--text-dim)', fontWeight: 700, letterSpacing: .6,
    textTransform: 'uppercase', borderBottom: '1px solid var(--border)',
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '10px 14px', borderBottom: '1px solid var(--border)',
    fontSize: 13, verticalAlign: 'middle',
  },
};

export function Badge({ color = 'blue', children }) {
  const colors = {
    blue: { background: 'var(--accent-dim)', color: 'var(--accent)' },
    green: { background: '#14532d', color: 'var(--green)' },
    red: { background: '#450a0a', color: 'var(--red)' },
    yellow: { background: '#451a03', color: 'var(--yellow)' },
    gray: { background: 'var(--border)', color: 'var(--text-dim)' },
  };
  return <span style={{ ...s.badge, ...colors[color] }}>{children}</span>;
}

export function Btn({ variant = 'primary', children, icon: Icon, ...props }) {
  const vars = {
    primary: { background: 'var(--accent)', color: '#fff' },
    ghost: { background: 'var(--surface2)', color: 'var(--text)' },
    danger: { background: '#450a0a', color: 'var(--red)' },
  };
  return (
    <button style={{ ...s.btn, ...vars[variant] }} {...props}>
      {Icon && <Icon size={14} />}
      {children}
    </button>
  );
}

export function Card({ children, style }) {
  return <div style={{ ...s.card, ...style }}>{children}</div>;
}

export function Input({ label, ...props }) {
  const [focus, setFocus] = useState(false);
  return (
    <div>
      {label && <label style={s.label}>{label}</label>}
      <input
        style={{ ...s.input, borderColor: focus ? 'var(--accent)' : 'var(--border)' }}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        {...props}
      />
    </div>
  );
}

export function Select({ label, children, ...props }) {
  return (
    <div>
      {label && <label style={s.label}>{label}</label>}
      <select style={{ ...s.input, appearance: 'none', cursor: 'pointer' }} {...props}>
        {children}
      </select>
    </div>
  );
}

export function Textarea({ label, ...props }) {
  return (
    <div>
      {label && <label style={s.label}>{label}</label>}
      <textarea
        style={{ ...s.input, resize: 'vertical', minHeight: 80, fontFamily: 'inherit' }}
        {...props}
      />
    </div>
  );
}

export function Table({ headers, children, empty = 'Kayıt yok' }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {headers.map(h => <th key={h} style={s.th}>{h}</th>)}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
      {!children || (Array.isArray(children) && children.length === 0) ? (
        <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-dim)' }}>{empty}</div>
      ) : null}
    </div>
  );
}

export function TD({ children, style }) {
  return <td style={{ ...s.td, ...style }}>{children}</td>;
}

export function Spinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
      <div style={{
        width: 28, height: 28, border: '3px solid var(--border)',
        borderTopColor: 'var(--accent)', borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>{title}</h1>
        {subtitle && <p style={{ color: 'var(--text-dim)', marginTop: 2, fontSize: 13 }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Modal({ open, onClose, title, children, width = 480 }) {
  if (!open) return null;
  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 14, padding: 28, width, maxWidth: '95vw',
          maxHeight: '90vh', overflowY: 'auto',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700 }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: 20, lineHeight: 1 }}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function FormRow({ children, cols = 2 }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols},1fr)`, gap: 14 }}>
      {children}
    </div>
  );
}

export function Alert({ type = 'error', children }) {
  const styles = {
    error: { background: '#450a0a', color: 'var(--red)', border: '1px solid #7f1d1d' },
    success: { background: '#14532d', color: 'var(--green)', border: '1px solid #166534' },
    info: { background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--accent-dim)' },
  };
  return (
    <div style={{ ...styles[type], borderRadius: 8, padding: '10px 14px', fontSize: 13, marginBottom: 14 }}>
      {children}
    </div>
  );
}
