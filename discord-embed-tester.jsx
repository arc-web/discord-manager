import { useState, useCallback } from "react";

const COLORS = {
  "Blue": 3447003, "Red": 15158332, "Green": 3066993, "Gold": 15844367,
  "Orange": 15105570, "Purple": 10181046, "Blurple": 5793266, "Dark": 2303786,
  "White": 16777215, "Teal": 1752220
};

const decToHex = (dec) => `#${dec.toString(16).padStart(6, '0')}`;

const TEMPLATES = {
  "Status Update": {
    embeds: [{ title: "Online", description: "All systems operational.", color: 3066993 }]
  },
  "Error Alert": {
    embeds: [{ title: "Error", description: "Connection to API failed.\nRetrying in 30 seconds.", color: 15158332, timestamp: new Date().toISOString() }]
  },
  "Data Report": {
    embeds: [{
      title: "Memory Storage", color: 3447003,
      fields: [
        { name: "Local DB", value: "SQLite - 204 memories", inline: true },
        { name: "Shared Service", value: "172.19.0.1:3860", inline: true },
        { name: "Status", value: "Healthy", inline: true }
      ],
      footer: { text: "ZeroClaw" }
    }]
  },
  "Task List": {
    embeds: [{
      title: "Daily Tasks", color: 15844367,
      fields: [
        { name: "1. Wright's Impact Looker", value: "Fix Facebook spend display" },
        { name: "2. SFBayArea Proposal", value: "Draft awaiting Mike approval" },
        { name: "3. NKPSYCH Review", value: "Google Ads STR pending" }
      ]
    }]
  },
  "Full Example": {
    embeds: [{
      title: "Deployment Complete", url: "https://example.com",
      description: "Version **2.4.1** deployed to production.\n\nAll health checks passing.",
      color: 3066993, timestamp: new Date().toISOString(),
      author: { name: "CI/CD Pipeline", icon_url: "https://cdn.discordapp.com/embed/avatars/0.png" },
      thumbnail: { url: "https://cdn.discordapp.com/embed/avatars/1.png" },
      fields: [
        { name: "Service", value: "`api-gateway`", inline: true },
        { name: "Region", value: "`us-east-1`", inline: true },
        { name: "Duration", value: "`2m 34s`", inline: true },
        { name: "Changes", value: "- Fixed auth timeout\n- Updated rate limiter\n- Added health endpoint" }
      ],
      footer: { text: "Deployed by GitHub Actions" }
    }]
  },
  "Components V2": {
    flags: 32768,
    components: [
      { type: 17, accent_color: 3447003, components: [
        { type: 10, content: "# Server Status\nAll systems are **operational**." },
        { type: 14, spacing: 1, divider: true },
        { type: 9, components: [{ type: 10, content: "**Uptime:** 99.97%\n**Last incident:** 3 days ago" }],
          accessory: { type: 11, media: { url: "https://cdn.discordapp.com/embed/avatars/2.png" }}
        }
      ]},
      { type: 1, components: [
        { type: 2, style: 1, label: "Details", custom_id: "details" },
        { type: 2, style: 5, label: "Dashboard", url: "https://example.com" },
        { type: 2, style: 4, label: "Restart", custom_id: "restart" }
      ]}
    ]
  }
};

function parseMarkdown(text) {
  if (!text) return text;
  let result = text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/~~(.+?)~~/g, '<del>$1</del>')
    .replace(/__(.+?)__/g, '<u>$1</u>')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.06);padding:1px 4px;border-radius:3px;font-size:0.85em;font-family:Consolas,monospace">$1</code>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:#00AFF4;text-decoration:none" target="_blank">$1</a>')
    .replace(/^> (.+)$/gm, '<div style="border-left:3px solid rgba(255,255,255,0.15);padding-left:8px;margin:2px 0">$1</div>')
    .replace(/^- (.+)$/gm, '• $1')
    .replace(/^# (.+)$/gm, '<div style="font-size:1.4em;font-weight:700;margin:4px 0">$1</div>')
    .replace(/\n/g, '<br/>');
  return result;
}

function EmbedPreview({ embed }) {
  const borderColor = embed.color ? decToHex(embed.color) : '#202225';
  return (
    <div style={{
      display: 'flex', maxWidth: 520, marginBottom: 4,
      background: '#2f3136', borderRadius: 4, overflow: 'hidden',
      borderLeft: `4px solid ${borderColor}`
    }}>
      <div style={{ padding: '8px 16px 16px 12px', flex: 1, minWidth: 0 }}>
        {embed.author && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            {embed.author.icon_url && <img src={embed.author.icon_url} alt="" style={{ width: 24, height: 24, borderRadius: '50%' }} onError={e => e.target.style.display='none'} />}
            <span style={{ fontSize: 12, fontWeight: 600, color: '#fff' }}>{embed.author.name}</span>
          </div>
        )}
        {embed.title && (
          <div style={{ fontWeight: 700, color: embed.url ? '#00AFF4' : '#fff', fontSize: 16, marginBottom: 4 }}>
            {embed.url ? <a href={embed.url} style={{ color: '#00AFF4', textDecoration: 'none' }} target="_blank" rel="noreferrer">{embed.title}</a> : embed.title}
          </div>
        )}
        {embed.description && (
          <div style={{ fontSize: 14, color: '#dcddde', lineHeight: 1.45, marginBottom: 8 }}
            dangerouslySetInnerHTML={{ __html: parseMarkdown(embed.description) }} />
        )}
        {embed.fields && embed.fields.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: embed.fields.some(f => f.inline) ? 'repeat(3, 1fr)' : '1fr', gap: '8px 12px', marginBottom: 8 }}>
            {embed.fields.map((field, i) => (
              <div key={i} style={{ gridColumn: field.inline ? 'auto' : '1 / -1' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#fff', marginBottom: 2 }}
                  dangerouslySetInnerHTML={{ __html: parseMarkdown(field.name) }} />
                <div style={{ fontSize: 14, color: '#dcddde', lineHeight: 1.4 }}
                  dangerouslySetInnerHTML={{ __html: parseMarkdown(field.value) }} />
              </div>
            ))}
          </div>
        )}
        {embed.image && (
          <img src={embed.image.url} alt="" style={{ maxWidth: '100%', borderRadius: 4, marginBottom: 8 }} onError={e => e.target.style.display='none'} />
        )}
        {(embed.footer || embed.timestamp) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#72767d' }}>
            {embed.footer?.icon_url && <img src={embed.footer.icon_url} alt="" style={{ width: 20, height: 20, borderRadius: '50%' }} onError={e => e.target.style.display='none'} />}
            {embed.footer?.text && <span>{embed.footer.text}</span>}
            {embed.footer?.text && embed.timestamp && <span>•</span>}
            {embed.timestamp && <span>{new Date(embed.timestamp).toLocaleString()}</span>}
          </div>
        )}
      </div>
      {embed.thumbnail && (
        <div style={{ padding: '8px 16px 8px 0', flexShrink: 0 }}>
          <img src={embed.thumbnail.url} alt="" style={{ width: 80, height: 80, borderRadius: 4, objectFit: 'cover' }} onError={e => e.target.style.display='none'} />
        </div>
      )}
    </div>
  );
}

function ButtonPreview({ btn }) {
  const styles = {
    1: { bg: '#5865F2', color: '#fff' },
    2: { bg: '#4f545c', color: '#fff' },
    3: { bg: '#3ba55c', color: '#fff' },
    4: { bg: '#ed4245', color: '#fff' },
    5: { bg: '#4f545c', color: '#fff' },
  };
  const s = styles[btn.style] || styles[2];
  return (
    <button style={{
      background: s.bg, color: s.color, border: 'none', borderRadius: 3,
      padding: '2px 16px', height: 32, fontSize: 14, fontWeight: 500,
      cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6,
      opacity: btn.disabled ? 0.5 : 1, fontFamily: 'inherit'
    }}>
      {btn.emoji && <span>{btn.emoji.name}</span>}
      {btn.label}
      {btn.style === 5 && <span style={{ fontSize: 10 }}>↗</span>}
    </button>
  );
}

function ComponentPreview({ component }) {
  if (!component) return null;
  switch (component.type) {
    case 1: // Action Row
      return (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
          {component.components?.map((c, i) => <ComponentPreview key={i} component={c} />)}
        </div>
      );
    case 2: // Button
      return <ButtonPreview btn={component} />;
    case 3: // String Select
      return (
        <div style={{ background: '#1e1f22', border: '1px solid #3f4147', borderRadius: 4, padding: '8px 12px', color: '#8b8d93', fontSize: 14, marginBottom: 4, maxWidth: 400 }}>
          {component.placeholder || 'Make a selection'}
          <span style={{ float: 'right' }}>▾</span>
        </div>
      );
    case 9: // Section
      return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 4 }}>
          <div style={{ flex: 1 }}>
            {component.components?.map((c, i) => <ComponentPreview key={i} component={c} />)}
          </div>
          {component.accessory && component.accessory.type === 11 && (
            <img src={component.accessory.media?.url} alt="" style={{ width: 48, height: 48, borderRadius: 4 }} onError={e => e.target.style.display='none'} />
          )}
        </div>
      );
    case 10: // Text Display
      return (
        <div style={{ fontSize: 14, color: '#dcddde', lineHeight: 1.5, marginBottom: 4 }}
          dangerouslySetInnerHTML={{ __html: parseMarkdown(component.content) }} />
      );
    case 14: // Separator
      return (
        <div style={{ margin: component.spacing === 2 ? '16px 0' : '8px 0' }}>
          {component.divider && <hr style={{ border: 'none', borderTop: '1px solid #3f4147', margin: 0 }} />}
        </div>
      );
    case 17: // Container
      return (
        <div style={{
          background: '#2b2d31', borderRadius: 8, padding: 12, marginBottom: 8,
          borderLeft: component.accent_color ? `3px solid ${decToHex(component.accent_color)}` : 'none'
        }}>
          {component.components?.map((c, i) => <ComponentPreview key={i} component={c} />)}
        </div>
      );
    default:
      return <div style={{ color: '#72767d', fontSize: 12 }}>Component type {component.type} (preview not available)</div>;
  }
}

function MessagePreview({ payload }) {
  return (
    <div style={{ padding: '16px 48px 16px 72px', position: 'relative' }}>
      <div style={{
        position: 'absolute', left: 16, top: 16, width: 40, height: 40,
        borderRadius: '50%', background: '#5865F2', display: 'flex',
        alignItems: 'center', justifyContent: 'center', color: '#fff',
        fontSize: 14, fontWeight: 700
      }}>ZC</div>
      <div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
          <span style={{ fontWeight: 600, color: '#fff', fontSize: 15 }}>ZeroClaw</span>
          <span style={{
            background: '#5865F2', color: '#fff', fontSize: 10, fontWeight: 600,
            padding: '1px 5px', borderRadius: 3, verticalAlign: 'middle'
          }}>APP</span>
          <span style={{ color: '#72767d', fontSize: 12 }}>Today at {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
        {payload.content && (
          <div style={{ color: '#dcddde', fontSize: 15, marginBottom: 4 }}
            dangerouslySetInnerHTML={{ __html: parseMarkdown(payload.content) }} />
        )}
        {payload.embeds?.map((embed, i) => <EmbedPreview key={i} embed={embed} />)}
        {payload.components?.map((comp, i) => <ComponentPreview key={i} component={comp} />)}
      </div>
    </div>
  );
}

function Validator({ payload }) {
  const errors = [];
  const warnings = [];

  if (!payload.content && !payload.embeds?.length && !payload.components?.length) {
    errors.push("Payload must have content, embeds, or components");
  }
  if (payload.content && payload.content.length > 2000) {
    errors.push(`content: ${payload.content.length}/2000 chars`);
  }
  if (payload.embeds) {
    if (payload.embeds.length > 10) errors.push(`Max 10 embeds, got ${payload.embeds.length}`);
    payload.embeds.forEach((e, i) => {
      let total = 0;
      const count = (s) => { if (s) total += s.length; };
      count(e.title); count(e.description); count(e.footer?.text); count(e.author?.name);
      e.fields?.forEach(f => { count(f.name); count(f.value); });

      if (e.title && e.title.length > 256) errors.push(`embeds[${i}].title: ${e.title.length}/256`);
      if (e.description && e.description.length > 4096) errors.push(`embeds[${i}].description: ${e.description.length}/4096`);
      if (total > 6000) errors.push(`embeds[${i}] total chars: ${total}/6000`);
      if (e.fields?.length > 25) errors.push(`embeds[${i}].fields: ${e.fields.length}/25`);
      e.fields?.forEach((f, j) => {
        if (!f.name || f.name.trim() === '') errors.push(`embeds[${i}].fields[${j}].name is empty`);
        if (!f.value || f.value.trim() === '') errors.push(`embeds[${i}].fields[${j}].value is empty`);
        if (f.name && f.name.length > 256) errors.push(`embeds[${i}].fields[${j}].name: ${f.name.length}/256`);
        if (f.value && f.value.length > 1024) errors.push(`embeds[${i}].fields[${j}].value: ${f.value.length}/1024`);
      });
      if (e.color && typeof e.color === 'string') errors.push(`embeds[${i}].color must be integer, got string`);
      if (e.thumbnail?.url && !e.thumbnail.url.startsWith('https')) warnings.push(`embeds[${i}].thumbnail: HTTP URLs blocked`);
      if (e.image?.url && !e.image.url.startsWith('https')) warnings.push(`embeds[${i}].image: HTTP URLs blocked`);
      if (e.description && e.description.includes('```')) warnings.push(`embeds[${i}].description: triple backticks render inconsistently`);
      if (e.description && e.description.includes('\u2014')) warnings.push(`embeds[${i}].description: contains em dash`);
      if (total > 0) {
        // char count display
      }
    });
  }
  return { errors, warnings };
}

export default function DiscordEmbedTester() {
  const [json, setJson] = useState(JSON.stringify(TEMPLATES["Status Update"], null, 2));
  const [parseError, setParseError] = useState(null);
  const [payload, setPayload] = useState(TEMPLATES["Status Update"]);
  const [tab, setTab] = useState('editor');
  const [copied, setCopied] = useState(false);

  const updatePayload = useCallback((newJson) => {
    setJson(newJson);
    try {
      const parsed = JSON.parse(newJson);
      setPayload(parsed);
      setParseError(null);
    } catch (e) {
      setParseError(e.message);
    }
  }, []);

  const loadTemplate = (name) => {
    const t = TEMPLATES[name];
    const s = JSON.stringify(t, null, 2);
    setJson(s);
    setPayload(t);
    setParseError(null);
  };

  const copyJson = () => {
    navigator.clipboard?.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const validation = payload ? Validator({ payload }) : { errors: [], warnings: [] };

  return (
    <div style={{
      fontFamily: "'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif",
      background: '#313338', color: '#dcddde', minHeight: '100vh', display: 'flex', flexDirection: 'column'
    }}>
      {/* Header */}
      <div style={{
        background: '#1e1f22', padding: '12px 20px', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #3f4147'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: '#5865F2',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 14, fontWeight: 700
          }}>E</div>
          <div>
            <div style={{ color: '#fff', fontWeight: 600, fontSize: 15 }}>Discord Embed Tester</div>
            <div style={{ color: '#72767d', fontSize: 11 }}>Build, validate, preview Discord embeds and components</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['editor', 'preview', 'reference'].map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              background: tab === t ? '#5865F2' : 'transparent', color: tab === t ? '#fff' : '#b5bac1',
              border: 'none', borderRadius: 4, padding: '6px 14px', fontSize: 13,
              cursor: 'pointer', fontWeight: 500, fontFamily: 'inherit'
            }}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>
          ))}
        </div>
      </div>

      {/* Templates */}
      <div style={{ background: '#2b2d31', padding: '8px 20px', display: 'flex', gap: 6, flexWrap: 'wrap', borderBottom: '1px solid #3f4147' }}>
        <span style={{ color: '#72767d', fontSize: 12, lineHeight: '28px', marginRight: 4 }}>Templates:</span>
        {Object.keys(TEMPLATES).map(name => (
          <button key={name} onClick={() => loadTemplate(name)} style={{
            background: '#1e1f22', color: '#b5bac1', border: '1px solid #3f4147',
            borderRadius: 4, padding: '4px 10px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit'
          }}>{name}</button>
        ))}
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Editor */}
        {(tab === 'editor' || tab === 'preview') && (
          <div style={{
            flex: tab === 'editor' ? 1 : 0,
            display: tab === 'editor' ? 'flex' : 'none',
            flexDirection: 'column', borderRight: '1px solid #3f4147'
          }}>
            <div style={{ padding: '8px 12px', background: '#2b2d31', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#b5bac1' }}>JSON PAYLOAD</span>
              <button onClick={copyJson} style={{
                background: copied ? '#3ba55c' : '#4f545c', color: '#fff', border: 'none',
                borderRadius: 3, padding: '3px 10px', fontSize: 11, cursor: 'pointer', fontFamily: 'inherit'
              }}>{copied ? 'Copied!' : 'Copy'}</button>
            </div>
            <textarea value={json} onChange={e => updatePayload(e.target.value)} spellCheck={false} style={{
              flex: 1, background: '#1e1f22', color: '#e1e4e8', border: 'none',
              padding: 16, fontFamily: 'Consolas, Monaco, monospace', fontSize: 13,
              lineHeight: 1.6, resize: 'none', outline: 'none', tabSize: 2
            }} />
            {/* Validation */}
            <div style={{ background: '#2b2d31', padding: '8px 12px', borderTop: '1px solid #3f4147' }}>
              {parseError && <div style={{ color: '#ed4245', fontSize: 12, marginBottom: 4 }}>Parse Error: {parseError}</div>}
              {validation.errors.map((e, i) => <div key={i} style={{ color: '#ed4245', fontSize: 12 }}>✕ {e}</div>)}
              {validation.warnings.map((w, i) => <div key={i} style={{ color: '#faa61a', fontSize: 12 }}>⚠ {w}</div>)}
              {!parseError && validation.errors.length === 0 && (
                <div style={{ color: '#3ba55c', fontSize: 12 }}>✓ Valid payload</div>
              )}
            </div>
          </div>
        )}

        {/* Preview */}
        {(tab === 'editor' || tab === 'preview') && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '8px 12px', background: '#2b2d31' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#b5bac1' }}>DISCORD PREVIEW</span>
            </div>
            <div style={{ flex: 1, background: '#313338', overflowY: 'auto' }}>
              {!parseError && payload && <MessagePreview payload={payload} />}
              {parseError && (
                <div style={{ padding: 40, textAlign: 'center', color: '#72767d' }}>
                  Fix JSON errors to see preview
                </div>
              )}
            </div>

            {/* Raw output comparison */}
            <div style={{ background: '#2b2d31', padding: '8px 12px', borderTop: '1px solid #3f4147' }}>
              <div style={{ fontSize: 11, color: '#72767d', marginBottom: 4 }}>What ZeroClaw should send vs what it's doing:</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#3ba55c', fontWeight: 600, marginBottom: 2 }}>CORRECT: channel.send(payload)</div>
                  <div style={{ background: '#1e1f22', padding: 4, borderRadius: 3, fontSize: 10, color: '#8b8d93', fontFamily: 'monospace', border: '1px solid #3ba55c33' }}>
                    Renders as rich embed ↑
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#ed4245', fontWeight: 600, marginBottom: 2 }}>WRONG: channel.send({"{"} content: JSON.stringify(payload) {"}"})</div>
                  <div style={{ background: '#1e1f22', padding: 4, borderRadius: 3, fontSize: 10, color: '#8b8d93', fontFamily: 'monospace', border: '1px solid #ed424533', wordBreak: 'break-all', maxHeight: 40, overflow: 'hidden' }}>
                    {json?.substring(0, 120)}...
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Reference Tab */}
        {tab === 'reference' && (
          <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
            <h2 style={{ color: '#fff', fontSize: 20, margin: '0 0 16px', fontWeight: 700 }}>Quick Reference</h2>

            <div style={{ background: '#2b2d31', borderRadius: 8, padding: 16, marginBottom: 16 }}>
              <h3 style={{ color: '#fff', fontSize: 15, margin: '0 0 8px' }}>Character Limits</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 24px', fontSize: 13 }}>
                {[
                  ['title', '256'], ['description', '4096'], ['field name', '256'], ['field value', '1024'],
                  ['footer text', '2048'], ['author name', '256'], ['fields per embed', '25'],
                  ['total chars/embed', '6000'], ['embeds per message', '10'], ['content', '2000']
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                    <span style={{ color: '#b5bac1' }}>{k}</span>
                    <span style={{ color: '#5865F2', fontFamily: 'monospace' }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: '#2b2d31', borderRadius: 8, padding: 16, marginBottom: 16 }}>
              <h3 style={{ color: '#fff', fontSize: 15, margin: '0 0 8px' }}>Color Presets (Decimal)</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 4, fontSize: 13 }}>
                {Object.entries(COLORS).map(([name, val]) => (
                  <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
                    <div style={{ width: 16, height: 16, borderRadius: 3, background: decToHex(val), flexShrink: 0 }} />
                    <span style={{ color: '#b5bac1' }}>{name}</span>
                    <span style={{ color: '#72767d', fontFamily: 'monospace', marginLeft: 'auto' }}>{val}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: '#2b2d31', borderRadius: 8, padding: 16, marginBottom: 16 }}>
              <h3 style={{ color: '#fff', fontSize: 15, margin: '0 0 8px' }}>Component Types</h3>
              <div style={{ fontSize: 13, lineHeight: 1.8 }}>
                {[
                  [1, 'Action Row', 'Layout - holds buttons or 1 select'],
                  [2, 'Button', '5 styles: Primary/Secondary/Success/Danger/Link'],
                  [3, 'String Select', 'Dropdown, max 25 options'],
                  [5, 'User Select', 'Auto-populated user picker'],
                  [6, 'Role Select', 'Auto-populated role picker'],
                  [8, 'Channel Select', 'Auto-populated channel picker'],
                  [9, 'Section', 'V2 - text + accessory (thumbnail/button)'],
                  [10, 'Text Display', 'V2 - markdown text block'],
                  [12, 'Media Gallery', 'V2 - image grid'],
                  [14, 'Separator', 'V2 - spacing/divider'],
                  [17, 'Container', 'V2 - grouped components with accent color'],
                ].map(([type, name, desc]) => (
                  <div key={type} style={{ display: 'flex', gap: 12, padding: '2px 0' }}>
                    <span style={{ color: '#5865F2', fontFamily: 'monospace', minWidth: 24 }}>{type}</span>
                    <span style={{ color: '#fff', fontWeight: 600, minWidth: 120 }}>{name}</span>
                    <span style={{ color: '#8b8d93' }}>{desc}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: '#2b2d31', borderRadius: 8, padding: 16 }}>
              <h3 style={{ color: '#fff', fontSize: 15, margin: '0 0 8px' }}>Button Styles</h3>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {[
                  [1, 'Primary', '#5865F2'], [2, 'Secondary', '#4f545c'],
                  [3, 'Success', '#3ba55c'], [4, 'Danger', '#ed4245'], [5, 'Link', '#4f545c']
                ].map(([style, name, color]) => (
                  <div key={style} style={{
                    background: color, color: '#fff', borderRadius: 3,
                    padding: '4px 14px', fontSize: 13, fontWeight: 500
                  }}>{name} ({style})</div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
