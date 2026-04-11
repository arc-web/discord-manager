import { useState, useRef, useCallback, useEffect } from "react";

const COLORS = {
  Blue: 3447003, Red: 15158332, Green: 3066993, Gold: 15844367,
  Orange: 15105570, Purple: 10181046, Blurple: 5793266, Dark: 2303786, Teal: 1752220
};
const decToHex = (d) => `#${d.toString(16).padStart(6, '0')}`;

function parseMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/~~(.+?)~~/g, '<del>$1</del>')
    .replace(/__(.+?)__/g, '<u>$1</u>')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.06);padding:1px 4px;border-radius:3px;font-size:0.85em;font-family:Consolas,monospace">$1</code>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:#00AFF4;text-decoration:none">$1</a>')
    .replace(/^- (.+)$/gm, '• $1')
    .replace(/\n/g, '<br/>');
}

function EmbedPreview({ embed, small = false }) {
  const bc = embed.color ? decToHex(embed.color) : '#202225';
  const s = small ? 0.85 : 1;
  return (
    <div style={{ display:'flex', maxWidth: small ? 360 : 520, background:'#2f3136', borderRadius:4, overflow:'hidden', borderLeft:`4px solid ${bc}`, fontSize: 14 * s }}>
      <div style={{ padding: small ? '6px 10px 10px 8px' : '8px 16px 16px 12px', flex:1, minWidth:0 }}>
        {embed.author && (
          <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:3 }}>
            {embed.author.icon_url && <img src={embed.author.icon_url} alt="" style={{ width:20*s, height:20*s, borderRadius:'50%' }} onError={e=>e.target.style.display='none'} />}
            <span style={{ fontSize:11*s, fontWeight:600, color:'#fff' }}>{embed.author.name}</span>
          </div>
        )}
        {embed.title && <div style={{ fontWeight:700, color: embed.url ? '#00AFF4':'#fff', fontSize:15*s, marginBottom:3 }}>{embed.title}</div>}
        {embed.description && <div style={{ fontSize:13*s, color:'#dcddde', lineHeight:1.4, marginBottom:6 }} dangerouslySetInnerHTML={{ __html: parseMarkdown(embed.description) }} />}
        {embed.fields?.length > 0 && (
          <div style={{ display:'grid', gridTemplateColumns: embed.fields.some(f=>f.inline) ? 'repeat(3,1fr)' : '1fr', gap:'6px 10px', marginBottom:6 }}>
            {embed.fields.map((f,i) => (
              <div key={i} style={{ gridColumn: f.inline ? 'auto' : '1/-1' }}>
                <div style={{ fontSize:11*s, fontWeight:700, color:'#fff', marginBottom:1 }} dangerouslySetInnerHTML={{ __html: parseMarkdown(f.name) }} />
                <div style={{ fontSize:13*s, color:'#dcddde', lineHeight:1.35 }} dangerouslySetInnerHTML={{ __html: parseMarkdown(f.value) }} />
              </div>
            ))}
          </div>
        )}
        {embed.image && <img src={embed.image.url} alt="" style={{ maxWidth:'100%', borderRadius:4, marginBottom:6 }} onError={e=>e.target.style.display='none'} />}
        {(embed.footer || embed.timestamp) && (
          <div style={{ display:'flex', alignItems:'center', gap:5, fontSize:11*s, color:'#72767d' }}>
            {embed.footer?.text && <span>{embed.footer.text}</span>}
            {embed.footer?.text && embed.timestamp && <span>•</span>}
            {embed.timestamp && <span>{new Date(embed.timestamp).toLocaleString()}</span>}
          </div>
        )}
      </div>
      {embed.thumbnail && (
        <div style={{ padding:'8px 12px 8px 0', flexShrink:0 }}>
          <img src={embed.thumbnail.url} alt="" style={{ width:60*s, height:60*s, borderRadius:4, objectFit:'cover' }} onError={e=>e.target.style.display='none'} />
        </div>
      )}
    </div>
  );
}

function ButtonPreview({ btn }) {
  const colors = { 1:'#5865F2', 2:'#4f545c', 3:'#3ba55c', 4:'#ed4245', 5:'#4f545c' };
  return (
    <button style={{ background: colors[btn.style]||'#4f545c', color:'#fff', border:'none', borderRadius:3, padding:'2px 14px', height:28, fontSize:13, fontWeight:500, cursor:'pointer', fontFamily:'inherit', display:'inline-flex', alignItems:'center', gap:5 }}>
      {btn.emoji?.name && <span>{btn.emoji.name}</span>}
      {btn.label}
      {btn.style === 5 && <span style={{ fontSize:9 }}>↗</span>}
    </button>
  );
}

function ComponentPreview({ comp }) {
  if (!comp) return null;
  if (comp.type === 1) return <div style={{ display:'flex', gap:6, flexWrap:'wrap', marginBottom:4 }}>{comp.components?.map((c,i) => <ComponentPreview key={i} comp={c} />)}</div>;
  if (comp.type === 2) return <ButtonPreview btn={comp} />;
  if (comp.type === 3) return <div style={{ background:'#1e1f22', border:'1px solid #3f4147', borderRadius:4, padding:'6px 10px', color:'#8b8d93', fontSize:13, marginBottom:4, maxWidth:360 }}>{comp.placeholder||'Select...'}<span style={{ float:'right' }}>▾</span></div>;
  if (comp.type === 10) return <div style={{ fontSize:13, color:'#dcddde', lineHeight:1.45, marginBottom:4 }} dangerouslySetInnerHTML={{ __html: parseMarkdown(comp.content) }} />;
  if (comp.type === 14) return <div style={{ margin: comp.spacing===2?'14px 0':'6px 0' }}>{comp.divider && <hr style={{ border:'none', borderTop:'1px solid #3f4147', margin:0 }} />}</div>;
  if (comp.type === 17) return <div style={{ background:'#2b2d31', borderRadius:8, padding:10, marginBottom:6, borderLeft: comp.accent_color?`3px solid ${decToHex(comp.accent_color)}`:'none' }}>{comp.components?.map((c,i) => <ComponentPreview key={i} comp={c} />)}</div>;
  if (comp.type === 9) return (
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:10, marginBottom:4 }}>
      <div style={{ flex:1 }}>{comp.components?.map((c,i) => <ComponentPreview key={i} comp={c} />)}</div>
      {comp.accessory?.type===11 && <img src={comp.accessory.media?.url} alt="" style={{ width:44, height:44, borderRadius:4 }} onError={e=>e.target.style.display='none'} />}
    </div>
  );
  return null;
}

function FullPreview({ payload }) {
  if (!payload) return null;
  return (
    <div>
      {payload.content && <div style={{ color:'#dcddde', fontSize:14, marginBottom:4 }} dangerouslySetInnerHTML={{ __html: parseMarkdown(payload.content) }} />}
      {payload.embeds?.map((e,i) => <EmbedPreview key={i} embed={e} />)}
      {payload.components?.map((c,i) => <ComponentPreview key={i} comp={c} />)}
    </div>
  );
}

const SYSTEM_PROMPT = `You are a Discord embed architect. The user describes what they want to communicate in Discord. Your job:

1. REASON through the request step by step:
   - What is the content type? (status, alert, report, task list, announcement, question, summary)
   - What embed structure fits best? (simple title+desc, fields grid, multi-embed, components v2)
   - What color conveys the right tone?
   - Should it use fields (inline or stacked), buttons, select menus?

2. Generate EXACTLY 3 different embed approaches as JSON. Each should be meaningfully different, not just color swaps:
   - Option A: Minimal/clean approach
   - Option B: Detailed/structured approach  
   - Option C: Creative/component-rich approach (can use Components V2 if appropriate)

RESPOND ONLY IN THIS EXACT JSON FORMAT, no other text:
{
  "reasoning": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "options": [
    {
      "label": "Short 2-4 word label",
      "description": "One sentence explaining the approach",
      "payload": { ...valid discord webhook/bot payload... }
    },
    { ... },
    { ... }
  ]
}

RULES:
- color must be decimal integer (Blue:3447003, Red:15158332, Green:3066993, Gold:15844367, Orange:15105570, Purple:10181046, Blurple:5793266)
- field name and value must never be empty strings
- total chars across all embed text fields must be under 6000
- no triple backticks in embed fields
- no em dashes anywhere; use hyphens or semicolons
- embeds array at root for standard embeds
- Components V2 uses "flags":32768 and "components" array instead of embeds
- timestamps in ISO 8601
- HTTPS only for image URLs`;

export default function App() {
  const [input, setInput] = useState('');
  const [phase, setPhase] = useState('input'); // input | thinking | options | editing | refining
  const [reasoning, setReasoning] = useState([]);
  const [options, setOptions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [editJson, setEditJson] = useState('');
  const [editPayload, setEditPayload] = useState(null);
  const [editError, setEditError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [thinkingStep, setThinkingStep] = useState(0);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [refineInput, setRefineInput] = useState('');
  const [copied, setCopied] = useState(false);
  const inputRef = useRef(null);

  const callClaude = useCallback(async (prompt) => {
    setLoading(true);
    setError(null);
    setPhase('thinking');
    setReasoning([]);
    setOptions([]);
    setThinkingStep(0);

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 4000,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: prompt }]
        })
      });

      const data = await response.json();
      const text = data.content?.map(b => b.type === 'text' ? b.text : '').join('') || '';

      // Clean potential markdown fences
      const clean = text.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();

      let parsed;
      try {
        parsed = JSON.parse(clean);
      } catch (e) {
        // Try to extract JSON from the response
        const jsonMatch = clean.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          parsed = JSON.parse(jsonMatch[0]);
        } else {
          throw new Error('Could not parse AI response as JSON');
        }
      }

      // Animate reasoning steps
      if (parsed.reasoning) {
        for (let i = 0; i < parsed.reasoning.length; i++) {
          await new Promise(r => setTimeout(r, 400));
          setReasoning(prev => [...prev, parsed.reasoning[i]]);
          setThinkingStep(i + 1);
        }
      }

      await new Promise(r => setTimeout(r, 600));

      if (parsed.options) {
        setOptions(parsed.options);
        setPhase('options');
        setHistory(prev => [...prev, { prompt, options: parsed.options, reasoning: parsed.reasoning }]);
      }
    } catch (e) {
      setError(e.message);
      setPhase('input');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSubmit = () => {
    if (!input.trim()) return;
    callClaude(input.trim());
  };

  const handleSelect = (idx) => {
    setSelected(idx);
    const payload = options[idx].payload;
    setEditJson(JSON.stringify(payload, null, 2));
    setEditPayload(payload);
    setEditError(null);
    setPhase('editing');
  };

  const handleJsonEdit = (val) => {
    setEditJson(val);
    try {
      const p = JSON.parse(val);
      setEditPayload(p);
      setEditError(null);
    } catch (e) {
      setEditError(e.message);
    }
  };

  const handleRefine = () => {
    if (!refineInput.trim()) return;
    const context = `Original request: "${input}"\nSelected option: ${options[selected]?.label}\nCurrent JSON: ${editJson}\n\nRefinement request: ${refineInput}`;
    setInput(refineInput);
    setRefineInput('');
    callClaude(context);
  };

  const handleCopy = () => {
    navigator.clipboard?.writeText(editJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const startOver = () => {
    setPhase('input');
    setInput('');
    setReasoning([]);
    setOptions([]);
    setSelected(null);
    setEditJson('');
    setEditPayload(null);
    setError(null);
  };

  const quickPrompts = [
    "Server deployment complete - API v2.4.1 live in us-east-1",
    "Daily task list with 4 items for the team",
    "Error alert - database connection timeout, retrying",
    "Welcome message for new Discord members with rules summary",
    "Weekly metrics report - 1.2k users, 340 signups, 98% uptime"
  ];

  return (
    <div style={{ fontFamily: "'gg sans','Noto Sans','Helvetica Neue',Helvetica,Arial,sans-serif", background:'#1e1f22', color:'#dcddde', minHeight:'100vh', display:'flex', flexDirection:'column' }}>

      {/* Header */}
      <div style={{ background:'#111214', padding:'14px 24px', display:'flex', alignItems:'center', justifyContent:'space-between', borderBottom:'1px solid #2b2d31' }}>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <div style={{ width:36, height:36, borderRadius:10, background:'linear-gradient(135deg,#5865F2,#3ba55c)', display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', fontSize:16, fontWeight:800 }}>⚡</div>
          <div>
            <div style={{ color:'#fff', fontWeight:700, fontSize:16, letterSpacing:'-0.3px' }}>Discord Embed Architect</div>
            <div style={{ color:'#72767d', fontSize:11 }}>AI-powered reasoning + build + preview + export</div>
          </div>
        </div>
        <div style={{ display:'flex', gap:8, alignItems:'center' }}>
          {phase !== 'input' && (
            <button onClick={startOver} style={{ background:'#4f545c', color:'#fff', border:'none', borderRadius:4, padding:'6px 14px', fontSize:12, cursor:'pointer', fontFamily:'inherit', fontWeight:500 }}>New Build</button>
          )}
          <div style={{ width:8, height:8, borderRadius:'50%', background: loading ? '#faa61a' : '#3ba55c' }} />
        </div>
      </div>

      <div style={{ flex:1, display:'flex', flexDirection:'column', maxWidth:900, width:'100%', margin:'0 auto', padding:'0 20px' }}>

        {/* PHASE: INPUT */}
        {phase === 'input' && (
          <div style={{ flex:1, display:'flex', flexDirection:'column', justifyContent:'center', paddingBottom:80 }}>
            <div style={{ textAlign:'center', marginBottom:32 }}>
              <div style={{ fontSize:28, fontWeight:800, color:'#fff', marginBottom:8, letterSpacing:'-0.5px' }}>What do you want to say in Discord?</div>
              <div style={{ color:'#8b8d93', fontSize:14 }}>Describe your message. I'll reason through the best embed structure and give you options.</div>
            </div>

            <div style={{ position:'relative', marginBottom:20 }}>
              <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
                placeholder="e.g. Server deployment complete, version 2.4.1 is live in us-east-1, all health checks passing..."
                style={{ width:'100%', background:'#2b2d31', color:'#dcddde', border:'1px solid #3f4147', borderRadius:12, padding:'16px 18px', fontSize:15, lineHeight:1.5, resize:'none', outline:'none', minHeight:100, fontFamily:'inherit', boxSizing:'border-box' }}
              />
              <button onClick={handleSubmit} disabled={!input.trim()} style={{
                position:'absolute', bottom:12, right:12, background: input.trim() ? '#5865F2' : '#4f545c',
                color:'#fff', border:'none', borderRadius:8, padding:'8px 20px', fontSize:13, fontWeight:600,
                cursor: input.trim() ? 'pointer' : 'default', fontFamily:'inherit', opacity: input.trim() ? 1 : 0.5,
                transition:'all 0.15s'
              }}>Build Embeds →</button>
            </div>

            <div style={{ display:'flex', gap:6, flexWrap:'wrap', justifyContent:'center' }}>
              {quickPrompts.map((p, i) => (
                <button key={i} onClick={() => { setInput(p); setTimeout(() => inputRef.current?.focus(), 50); }}
                  style={{ background:'#2b2d31', color:'#8b8d93', border:'1px solid #3f4147', borderRadius:20, padding:'6px 14px', fontSize:12, cursor:'pointer', fontFamily:'inherit', transition:'all 0.15s' }}
                  onMouseEnter={e => { e.target.style.borderColor='#5865F2'; e.target.style.color='#dcddde'; }}
                  onMouseLeave={e => { e.target.style.borderColor='#3f4147'; e.target.style.color='#8b8d93'; }}
                >{p.length > 50 ? p.slice(0,50) + '...' : p}</button>
              ))}
            </div>

            {error && <div style={{ marginTop:16, padding:12, background:'#2b2d31', border:'1px solid #ed4245', borderRadius:8, color:'#ed4245', fontSize:13 }}>{error}</div>}
          </div>
        )}

        {/* PHASE: THINKING */}
        {phase === 'thinking' && (
          <div style={{ flex:1, display:'flex', flexDirection:'column', justifyContent:'center', paddingBottom:80 }}>
            <div style={{ background:'#2b2d31', borderRadius:12, padding:24, maxWidth:600, margin:'0 auto', width:'100%' }}>
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
                <div style={{ width:24, height:24, borderRadius:6, background:'#5865F2', display:'flex', alignItems:'center', justifyContent:'center' }}>
                  <div style={{ width:10, height:10, border:'2px solid #fff', borderTop:'2px solid transparent', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
                </div>
                <div style={{ color:'#fff', fontWeight:600, fontSize:14 }}>Reasoning through your request...</div>
              </div>

              <div style={{ borderLeft:'2px solid #3f4147', paddingLeft:16, marginLeft:11 }}>
                {reasoning.map((step, i) => (
                  <div key={i} style={{
                    color:'#b5bac1', fontSize:13, lineHeight:1.5, marginBottom:10, opacity:1,
                    animation:'fadeIn 0.3s ease-out'
                  }}>
                    <span style={{ color:'#5865F2', fontWeight:700, marginRight:8 }}>Step {i+1}</span>
                    {step}
                  </div>
                ))}
                {loading && (
                  <div style={{ color:'#72767d', fontSize:13 }}>
                    <span style={{ display:'inline-block', animation:'pulse 1.2s infinite' }}>●</span>
                    <span style={{ display:'inline-block', animation:'pulse 1.2s infinite 0.2s' }}>●</span>
                    <span style={{ display:'inline-block', animation:'pulse 1.2s infinite 0.4s' }}>●</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* PHASE: OPTIONS */}
        {phase === 'options' && (
          <div style={{ flex:1, paddingTop:24, paddingBottom:80, overflowY:'auto' }}>
            {/* Show reasoning collapsed */}
            <details style={{ marginBottom:20 }}>
              <summary style={{ color:'#72767d', fontSize:12, cursor:'pointer', userSelect:'none' }}>
                View reasoning ({reasoning.length} steps)
              </summary>
              <div style={{ background:'#2b2d31', borderRadius:8, padding:12, marginTop:8, borderLeft:'2px solid #5865F2' }}>
                {reasoning.map((s,i) => <div key={i} style={{ color:'#8b8d93', fontSize:12, marginBottom:6 }}><span style={{ color:'#5865F2', fontWeight:700 }}>Step {i+1}:</span> {s}</div>)}
              </div>
            </details>

            <div style={{ color:'#fff', fontWeight:700, fontSize:18, marginBottom:4 }}>Choose an approach</div>
            <div style={{ color:'#8b8d93', fontSize:13, marginBottom:20 }}>Each option is structurally different. Pick one to preview, edit, and export.</div>

            <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(260px, 1fr))', gap:16 }}>
              {options.map((opt, i) => (
                <button key={i} onClick={() => handleSelect(i)} style={{
                  background:'#2b2d31', border:'1px solid #3f4147', borderRadius:12, padding:16,
                  textAlign:'left', cursor:'pointer', transition:'all 0.2s', fontFamily:'inherit'
                }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor='#5865F2'; e.currentTarget.style.transform='translateY(-2px)'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor='#3f4147'; e.currentTarget.style.transform='none'; }}
                >
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:8 }}>
                    <div style={{ width:28, height:28, borderRadius:8, background: ['#5865F2','#3ba55c','#faa61a'][i], display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', fontSize:13, fontWeight:800 }}>{String.fromCharCode(65+i)}</div>
                    <div style={{ color:'#fff', fontWeight:700, fontSize:14 }}>{opt.label}</div>
                  </div>
                  <div style={{ color:'#8b8d93', fontSize:12, marginBottom:12, lineHeight:1.4 }}>{opt.description}</div>
                  <div style={{ background:'#1e1f22', borderRadius:8, padding:10 }}>
                    <FullPreview payload={opt.payload} />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* PHASE: EDITING */}
        {phase === 'editing' && (
          <div style={{ flex:1, display:'flex', gap:16, paddingTop:20, paddingBottom:80, overflow:'hidden' }}>
            {/* JSON Editor */}
            <div style={{ flex:1, display:'flex', flexDirection:'column', minWidth:0 }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
                <div style={{ fontSize:12, fontWeight:600, color:'#b5bac1' }}>JSON PAYLOAD</div>
                <div style={{ display:'flex', gap:6 }}>
                  <button onClick={handleCopy} style={{ background: copied?'#3ba55c':'#4f545c', color:'#fff', border:'none', borderRadius:3, padding:'3px 10px', fontSize:11, cursor:'pointer', fontFamily:'inherit' }}>{copied?'Copied!':'Copy JSON'}</button>
                  <button onClick={() => setPhase('options')} style={{ background:'#4f545c', color:'#fff', border:'none', borderRadius:3, padding:'3px 10px', fontSize:11, cursor:'pointer', fontFamily:'inherit' }}>← Back</button>
                </div>
              </div>
              <textarea value={editJson} onChange={e => handleJsonEdit(e.target.value)} spellCheck={false}
                style={{ flex:1, background:'#111214', color:'#e1e4e8', border:'1px solid #3f4147', borderRadius:8, padding:14, fontFamily:'Consolas,Monaco,monospace', fontSize:12, lineHeight:1.6, resize:'none', outline:'none', tabSize:2 }}
              />
              {editError && <div style={{ color:'#ed4245', fontSize:11, marginTop:6 }}>Parse error: {editError}</div>}
              {!editError && <div style={{ color:'#3ba55c', fontSize:11, marginTop:6 }}>✓ Valid JSON</div>}

              {/* Refine with AI */}
              <div style={{ marginTop:12, display:'flex', gap:8 }}>
                <input value={refineInput} onChange={e => setRefineInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleRefine(); }}
                  placeholder="Refine: make it more urgent, add a footer, change color..."
                  style={{ flex:1, background:'#2b2d31', color:'#dcddde', border:'1px solid #3f4147', borderRadius:8, padding:'8px 12px', fontSize:12, outline:'none', fontFamily:'inherit' }}
                />
                <button onClick={handleRefine} disabled={!refineInput.trim()} style={{
                  background: refineInput.trim()?'#5865F2':'#4f545c', color:'#fff', border:'none', borderRadius:8,
                  padding:'8px 16px', fontSize:12, fontWeight:600, cursor: refineInput.trim()?'pointer':'default',
                  fontFamily:'inherit', opacity: refineInput.trim()?1:0.5, whiteSpace:'nowrap'
                }}>Refine →</button>
              </div>
            </div>

            {/* Live Preview */}
            <div style={{ flex:1, display:'flex', flexDirection:'column', minWidth:0 }}>
              <div style={{ fontSize:12, fontWeight:600, color:'#b5bac1', marginBottom:8 }}>DISCORD PREVIEW</div>
              <div style={{ flex:1, background:'#313338', borderRadius:8, overflow:'auto' }}>
                <div style={{ padding:'16px 48px 16px 72px', position:'relative' }}>
                  <div style={{ position:'absolute', left:16, top:16, width:40, height:40, borderRadius:'50%', background:'#5865F2', display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', fontSize:14, fontWeight:700 }}>ZC</div>
                  <div>
                    <div style={{ display:'flex', alignItems:'baseline', gap:8, marginBottom:4 }}>
                      <span style={{ fontWeight:600, color:'#fff', fontSize:15 }}>ZeroClaw</span>
                      <span style={{ background:'#5865F2', color:'#fff', fontSize:10, fontWeight:600, padding:'1px 5px', borderRadius:3 }}>APP</span>
                      <span style={{ color:'#72767d', fontSize:12 }}>Today at {new Date().toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}</span>
                    </div>
                    {!editError && editPayload && <FullPreview payload={editPayload} />}
                  </div>
                </div>
              </div>

              {/* Webhook test section */}
              <div style={{ marginTop:12, background:'#2b2d31', borderRadius:8, padding:12 }}>
                <div style={{ fontSize:11, fontWeight:600, color:'#b5bac1', marginBottom:6 }}>SEND TO DISCORD (paste webhook URL)</div>
                <div style={{ display:'flex', gap:6 }}>
                  <input id="webhook-url" placeholder="https://discord.com/api/webhooks/..." style={{ flex:1, background:'#111214', color:'#dcddde', border:'1px solid #3f4147', borderRadius:4, padding:'6px 10px', fontSize:11, outline:'none', fontFamily:'monospace' }} />
                  <button onClick={async () => {
                    const url = document.getElementById('webhook-url')?.value;
                    if (!url || !editPayload) return;
                    try {
                      const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: editJson });
                      if (r.ok) alert('Sent!');
                      else { const e = await r.json(); alert('Error: ' + JSON.stringify(e)); }
                    } catch(e) { alert('Failed: ' + e.message); }
                  }} style={{ background:'#3ba55c', color:'#fff', border:'none', borderRadius:4, padding:'6px 14px', fontSize:11, fontWeight:600, cursor:'pointer', fontFamily:'inherit', whiteSpace:'nowrap' }}>Send</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }
        @keyframes pulse { 0%,100% { opacity:0.3; } 50% { opacity:1; } }
        textarea::-webkit-scrollbar, div::-webkit-scrollbar { width:6px; }
        textarea::-webkit-scrollbar-thumb, div::-webkit-scrollbar-thumb { background:#3f4147; border-radius:3px; }
        textarea::-webkit-scrollbar-track, div::-webkit-scrollbar-track { background:transparent; }
        * { box-sizing: border-box; }
      `}</style>
    </div>
  );
}
