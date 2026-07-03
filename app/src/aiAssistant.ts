import { query } from './db';
import { highlightAndZoomToSegments } from './map';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  segIds?: number[];
  error?: string;
}

const DEFAULT_MODELS: Record<string, string> = {
  gemini: 'gemini-2.5-flash',
  openai: 'gpt-4o-mini',
  anthropic: 'claude-3-5-haiku-20241022',
  groq: 'llama-3.3-70b-versatile',
  grok: 'grok-2-1212',
  openrouter: 'google/gemini-2.5-flash',
};

const SCHEMA_GROUNDING = `
You are a Text-to-SQL assistant for the PHLCRSH (Philadelphia Environmental Safety Analysis & Spatial Diagnostic Engine) running a local DuckDB database.
Given a user's prompt, generate a single executable DuckDB SQL query.

TABLES:
1. 'segments'
Represents street centerline segments. Columns:
- seg_id (INTEGER): Unique street centerline segment identifier (Primary Key).
- st_name (VARCHAR): Name of the street (e.g., "Broad", "Market").
- st_type (VARCHAR): Street suffix type (e.g., "St", "Ave", "Blvd").
- class (INTEGER): Functional classification code (1: Expressway, 2: Major Arterial, 3: Minor Arterial, 4: Collector, 5: Local, 9: Ramp).
- road_class (VARCHAR): Human-readable functional classification corresponding to class (e.g. 'Expressway', 'Major Arterial', 'Local').
- length (FLOAT): Geometry length of the street segment in feet.
- cartway_width_ft (FLOAT): Estimated width of the roadway cartway (curb-to-curb) in feet.
- maxspeed_final (FLOAT): Posted speed limit in mph.
- canopy_pct (FLOAT): Percentage of tree canopy cover (0.0 to 1.0).
- grade_range_smooth (FLOAT): Smoothed segment slope grade (0.0 to 1.0 representing 0% to 100% slope).
- state_total_width_ft (FLOAT): Total roadway width from State Road attributes.
- state_lane_cnt (INTEGER): Number of traffic lanes.
- state_divisor_type (VARCHAR): Median separator category (e.g., "Divided", "Undivided", "Barrier").
- GEOID (VARCHAR): Census block group identifier containing the segment midpoint.
- adt (FLOAT): Average Daily Traffic volume.
- vmt (FLOAT): Daily Vehicle Miles Traveled on this segment.
- risk_index (FLOAT): Normalized Risk Index representing crash frequency per million Daily Vehicle-Feet traveled.
- crash_count (INTEGER): Total snapped crashes.
- fatal_count (INTEGER): Number of fatal crashes.
- injury_count (INTEGER): Number of general injury crashes.
- susp_serious_inj_count (INTEGER): Number of suspected serious injury crashes.
- severity_score (INTEGER): Weighted severity score (10*fatal + 4*serious + 1*injury).
- has_fatality (INTEGER): Binary indicator (1: has fatality; 0: otherwise).
- has_severe_injury (INTEGER): Binary indicator (1: has suspected serious injury; 0: otherwise).
- ped_count (INTEGER): Crashes involving pedestrians.
- bicycle_count (INTEGER): Crashes involving bicyclists.
- bike_infra_type (VARCHAR): Snapped bicycle facility category: 'Protected', 'Painted', 'Sharrow', or 'None'.
- intersection_control (VARCHAR): Intersection control type: 'Signalized', 'Stop-Controlled', or 'Uncontrolled'.
- nighttime_illumination (FLOAT): Streetlight pole density proxy.
- is_glare_prone (INTEGER): Binary (1: East-West segment; 0: otherwise).
- crash_count_day (INTEGER), crash_count_night (INTEGER), crash_count_clear (INTEGER), crash_count_wet (INTEGER)
- crash_count_day_clear (INTEGER), crash_count_day_wet (INTEGER), crash_count_night_clear (INTEGER), crash_count_night_wet (INTEGER)
- is_school_zone (INTEGER): Binary (1: within 500ft of school; 0: otherwise).
- high_heat_vulnerability (INTEGER): Binary (1: Heat Vulnerability Index score of 4 or 5; 0: otherwise).
- geometry (GEOMETRY): LineString geometry of the centerline segment (EPSG:4326).

2. 'block_groups'
Contains census block groups. Columns:
- GEOID (VARCHAR): FIPS block group unique identifier (Primary Key).
- population (INTEGER): Total population count.
- median_income (INTEGER): Median household income in USD.
- geometry (GEOMETRY): Polygon boundary geometry of the census block group (EPSG:4326).

CRITICAL RULES:
1. ALWAYS select 'seg_id' as a column in your query if the query returns street segments. This is required to highlight them on the map.
2. DuckDB has spatial support, so you can perform spatial filters or joins if needed. Do NOT call spatial functions on non-geometry columns.
3. Do NOT make up columns. Use only columns listed above.
4. Output ONLY valid SQL. Do not include markdown explanations. You MUST wrap the query in \`\`\`sql ... \`\`\` code blocks.
5. For South Philadelphia or general neighborhoods: Philadelphia FIPS code starts with "42101". South Philly block groups generally have GEOIDs starting with "42101000100" to "42101005000" or similar. You can do a filter on \`GEOID LIKE '4210100%'\`.
6. To avoid browser crashes, ALWAYS append a \`LIMIT 20\` to the query unless the user explicitly requests more.
`;

function extractSQL(text: string): string {
  const sqlMatch = text.match(/```sql([\s\S]*?)```/i);
  if (sqlMatch) {
    return sqlMatch[1].trim();
  }
  const codeMatch = text.match(/```([\s\S]*?)```/i);
  if (codeMatch) {
    return codeMatch[1].trim();
  }
  return text.trim();
}

function cleanQueryResults(rows: any[]): any[] {
  return rows.map((row) => {
    const cleaned: any = {};
    for (const key of Object.keys(row)) {
      const val = row[key];
      if (typeof val === 'bigint') {
        cleaned[key] = Number(val);
      } else if (val instanceof Uint8Array) {
        cleaned[key] = '[Binary/Geometry Data]';
      } else if (typeof val === 'object' && val !== null) {
        cleaned[key] = val.toString();
      } else {
        cleaned[key] = val;
      }
    }
    return cleaned;
  });
}

async function callLLM(
  provider: string,
  model: string,
  apiKey: string,
  systemPrompt: string,
  userPrompt: string
): Promise<string> {
  if (!apiKey) {
    throw new Error('API Key is missing. Please configure it in the assistant settings (gear icon).');
  }

  if (provider === 'gemini') {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [
          {
            role: 'user',
            parts: [{ text: userPrompt }],
          },
        ],
        systemInstruction: {
          parts: [{ text: systemPrompt }],
        },
        generationConfig: {
          temperature: 0.1,
        },
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      let errorMsg = `Error ${response.status}`;
      try {
        const parsed = JSON.parse(errText);
        if (parsed.error?.message) errorMsg = parsed.error.message;
      } catch {}
      throw new Error(`Gemini API error: ${errorMsg}`);
    }

    const data = await response.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) {
      throw new Error('Gemini API returned an empty response.');
    }
    return text;
  } else if (provider === 'anthropic') {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model,
        max_tokens: 1024,
        system: systemPrompt,
        messages: [{ role: 'user', content: userPrompt }],
        temperature: 0.1,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      let errorMsg = `Error ${response.status}`;
      try {
        const parsed = JSON.parse(errText);
        if (parsed.error?.message) errorMsg = parsed.error.message;
      } catch {}
      throw new Error(`Anthropic API error: ${errorMsg}. Note: Browser requests may be blocked by CORS.`);
    }

    const data = await response.json();
    const text = data.content?.[0]?.text;
    if (!text) {
      throw new Error('Anthropic API returned an empty response.');
    }
    return text;
  } else {
    // OpenAI-compatible endpoint configurations
    let endpoint = '';
    if (provider === 'openai') {
      endpoint = 'https://api.openai.com/v1/chat/completions';
    } else if (provider === 'groq') {
      endpoint = 'https://api.groq.com/openai/v1/chat/completions';
    } else if (provider === 'grok') {
      endpoint = 'https://api.x.ai/v1/chat/completions';
    } else if (provider === 'openrouter') {
      endpoint = 'https://openrouter.ai/api/v1/chat/completions';
    } else {
      throw new Error(`Unknown provider: ${provider}`);
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        temperature: 0.1,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      let errorMsg = `Error ${response.status}`;
      try {
        const parsed = JSON.parse(errText);
        if (parsed.error?.message) errorMsg = parsed.error.message;
      } catch {}
      throw new Error(`${provider.toUpperCase()} API error: ${errorMsg}`);
    }

    const data = await response.json();
    const text = data.choices?.[0]?.message?.content;
    if (!text) {
      throw new Error(`${provider.toUpperCase()} API returned an empty response.`);
    }
    return text;
  }
}

export function initAIAssistant() {
  const container = document.getElementById('app');
  if (!container) return;

  // Create UI elements
  const chatBubble = document.createElement('button');
  chatBubble.id = 'ai-chat-bubble';
  chatBubble.className = 'ai-chat-bubble';
  chatBubble.setAttribute('aria-label', 'Open safety assistant');
  chatBubble.setAttribute('aria-haspopup', 'true');
  chatBubble.innerHTML = `
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      <circle cx="9" cy="10" r="1" fill="currentColor"></circle>
      <circle cx="15" cy="10" r="1" fill="currentColor"></circle>
    </svg>
  `;

  const chatPanel = document.createElement('div');
  chatPanel.id = 'ai-chat-panel';
  chatPanel.className = 'ai-chat-panel is-collapsed';
  chatPanel.setAttribute('aria-hidden', 'true');
  chatPanel.innerHTML = `
    <div class="ai-panel-header">
      <div class="ai-panel-title-area">
        <svg class="ai-title-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
          <polyline points="2 17 12 22 22 17"></polyline>
          <polyline points="2 12 12 17 22 12"></polyline>
        </svg>
        <span class="ai-panel-title">Safety Assistant</span>
      </div>
      <div class="ai-panel-actions">
        <button id="ai-settings-toggle" class="ai-panel-action-btn" aria-label="Toggle LLM settings">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </button>
        <button id="ai-chat-close" class="ai-panel-action-btn" aria-label="Close safety assistant">×</button>
      </div>
    </div>

    <div id="ai-settings-pane" class="ai-settings-pane is-hidden">
      <h4 class="ai-settings-title">Assistant Settings</h4>
      <div class="ai-settings-field">
        <label for="ai-provider">LLM Provider</label>
        <select id="ai-provider">
          <option value="gemini">Gemini</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="groq">Groq</option>
          <option value="grok">Grok</option>
          <option value="openrouter">OpenRouter</option>
        </select>
        <div id="ai-provider-note" class="ai-settings-alert" style="display: none;"></div>
      </div>
      <div class="ai-settings-field">
        <label for="ai-model">Model Name</label>
        <input type="text" id="ai-model" placeholder="gemini-2.5-flash">
      </div>
      <div class="ai-settings-field">
        <label for="ai-api-key">API Key</label>
        <input type="password" id="ai-api-key" placeholder="Enter API key...">
      </div>
      <button id="ai-settings-save" class="ai-settings-save-btn">Save & Close</button>
    </div>

    <div id="ai-chat-messages" class="ai-chat-messages">
      <div class="ai-message assistant-message">
        Hi! I'm your PHLCRSH Safety Assistant. Ask me a safety query (e.g., "Find the top 5 highest risk streets with no bike lanes in South Philly") and I will query the local DuckDB database and summarize the insights.
      </div>
    </div>

    <form id="ai-chat-form" class="ai-chat-input-area">
      <input type="text" id="ai-chat-input" placeholder="Ask about safety..." autocomplete="off" required>
      <button type="submit" id="ai-chat-send" class="ai-chat-send-btn" aria-label="Send message">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"></line>
          <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
        </svg>
      </button>
    </form>
  `;

  container.appendChild(chatBubble);
  container.appendChild(chatPanel);

  // DOM references
  const messagesContainer = document.getElementById('ai-chat-messages') as HTMLDivElement;
  const chatForm = document.getElementById('ai-chat-form') as HTMLFormElement;
  const chatInput = document.getElementById('ai-chat-input') as HTMLInputElement;
  const chatSendBtn = document.getElementById('ai-chat-send') as HTMLButtonElement;
  const settingsToggle = document.getElementById('ai-settings-toggle') as HTMLButtonElement;
  const settingsPane = document.getElementById('ai-settings-pane') as HTMLDivElement;
  const settingsSaveBtn = document.getElementById('ai-settings-save') as HTMLButtonElement;
  const chatCloseBtn = document.getElementById('ai-chat-close') as HTMLButtonElement;

  const providerSelect = document.getElementById('ai-provider') as HTMLSelectElement;
  const modelInput = document.getElementById('ai-model') as HTMLInputElement;
  const apiKeyInput = document.getElementById('ai-api-key') as HTMLInputElement;
  const providerNote = document.getElementById('ai-provider-note') as HTMLDivElement;

  // Load Settings from LocalStorage
  let currentProvider = localStorage.getItem('phlcrsh_ai_provider') || 'gemini';
  let currentModel = localStorage.getItem('phlcrsh_ai_model') || DEFAULT_MODELS[currentProvider];
  let currentApiKey = localStorage.getItem(`phlcrsh_ai_key_${currentProvider}`) || '';

  // Initialize form fields
  providerSelect.value = currentProvider;
  modelInput.value = currentModel;
  apiKeyInput.value = currentApiKey;

  const updateProviderNote = (provider: string) => {
    if (provider === 'anthropic') {
      providerNote.style.display = 'block';
      providerNote.textContent = 'Warning: Direct browser requests to Anthropic will fail due to CORS. Use Gemini or OpenRouter for pure client-side calls.';
      providerNote.style.color = 'var(--color-warn)';
    } else if (provider === 'gemini') {
      providerNote.style.display = 'block';
      providerNote.textContent = 'Note: Gemini API keys can be requested on Google AI Studio. Direct browser requests work seamlessly.';
      providerNote.style.color = 'var(--color-good)';
    } else {
      providerNote.style.display = 'none';
    }
  };
  updateProviderNote(currentProvider);

  // Toggle Settings Pane
  const toggleSettings = () => {
    const isHidden = settingsPane.classList.contains('is-hidden');
    if (isHidden) {
      // Refresh inputs
      currentProvider = localStorage.getItem('phlcrsh_ai_provider') || 'gemini';
      currentModel = localStorage.getItem('phlcrsh_ai_model') || DEFAULT_MODELS[currentProvider];
      currentApiKey = localStorage.getItem(`phlcrsh_ai_key_${currentProvider}`) || '';

      providerSelect.value = currentProvider;
      modelInput.value = currentModel;
      apiKeyInput.value = currentApiKey;
      updateProviderNote(currentProvider);

      settingsPane.classList.remove('is-hidden');
      settingsPane.setAttribute('aria-hidden', 'false');
    } else {
      settingsPane.classList.add('is-hidden');
      settingsPane.setAttribute('aria-hidden', 'true');
    }
  };

  settingsToggle.addEventListener('click', toggleSettings);

  // Handle Provider Change (update default models)
  providerSelect.addEventListener('change', () => {
    const prov = providerSelect.value;
    modelInput.value = DEFAULT_MODELS[prov] || '';
    apiKeyInput.value = localStorage.getItem(`phlcrsh_ai_key_${prov}`) || '';
    updateProviderNote(prov);
  });

  // Save Settings
  settingsSaveBtn.addEventListener('click', () => {
    const prov = providerSelect.value;
    const model = modelInput.value.trim();
    const key = apiKeyInput.value.trim();

    localStorage.setItem('phlcrsh_ai_provider', prov);
    localStorage.setItem('phlcrsh_ai_model', model);
    localStorage.setItem(`phlcrsh_ai_key_${prov}`, key);

    currentProvider = prov;
    currentModel = model;
    currentApiKey = key;

    toggleSettings();
  });

  // Toggle Chat Panel visibility
  const toggleChatPanel = () => {
    const isCollapsed = chatPanel.classList.contains('is-collapsed');
    if (isCollapsed) {
      chatPanel.classList.remove('is-collapsed');
      chatPanel.setAttribute('aria-hidden', 'false');
      chatBubble.style.transform = 'scale(0) rotate(-90deg)';
      setTimeout(() => chatInput.focus(), 150);
    } else {
      chatPanel.classList.add('is-collapsed');
      chatPanel.setAttribute('aria-hidden', 'true');
      chatBubble.style.transform = '';
    }
  };

  chatBubble.addEventListener('click', toggleChatPanel);
  chatCloseBtn.addEventListener('click', toggleChatPanel);

  // Scroll messages area to bottom
  const scrollToBottom = () => {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  };

  // Append new message bubble to list
  const appendMessage = (msg: Message) => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `ai-message ${msg.role}-message`;

    let html = msg.content.replace(/\n/g, '<br>');

    // Format inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Add SQL details if present
    if (msg.sql) {
      const sqlId = `sql-${Math.random().toString(36).substr(2, 9)}`;
      html += `
        <br>
        <button class="sql-details-btn" data-sql-id="${sqlId}">
          <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
          View Generated SQL
        </button>
        <div id="${sqlId}" style="display: none; margin-top: 6px;">
          <pre><code>${msg.sql}</code></pre>
        </div>
      `;
    }

    // Add Highlight and Zoom button if segments exist
    if (msg.segIds && msg.segIds.length > 0) {
      html += `
        <br>
        <button class="show-on-map-btn" data-segs="${msg.segIds.join(',')}">
          <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right: 2px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
          Flash & Zoom to Streets (${msg.segIds.length})
        </button>
      `;
    }

    if (msg.error) {
      html += `
        <div style="color: var(--color-warn); font-size: 10px; margin-top: 6px; border-left: 2px solid var(--color-warn); padding-left: 6px;">
          <strong>Error:</strong> ${msg.error}
        </div>
      `;
    }

    msgDiv.innerHTML = html;
    messagesContainer.appendChild(msgDiv);

    // Event listener for SQL toggle
    msgDiv.querySelector('.sql-details-btn')?.addEventListener('click', (e) => {
      const btn = e.currentTarget as HTMLButtonElement;
      const id = btn.getAttribute('data-sql-id');
      const detailsDiv = document.getElementById(id!);
      if (detailsDiv) {
        const isHidden = detailsDiv.style.display === 'none';
        detailsDiv.style.display = isHidden ? 'block' : 'none';
        btn.innerHTML = isHidden 
          ? `<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"></polyline></svg> Hide Generated SQL`
          : `<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg> View Generated SQL`;
        scrollToBottom();
      }
    });

    // Event listener for Highlight and Zoom
    msgDiv.querySelector('.show-on-map-btn')?.addEventListener('click', (e) => {
      const btn = e.currentTarget as HTMLButtonElement;
      const idsStr = btn.getAttribute('data-segs');
      if (idsStr) {
        const ids = idsStr.split(',').map(Number);
        highlightAndZoomToSegments(ids);
      }
    });

    scrollToBottom();
  };

  // Submit Handler
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const promptText = chatInput.value.trim();
    if (!promptText) return;

    chatInput.value = '';
    chatInput.disabled = true;
    chatSendBtn.disabled = true;

    appendMessage({ role: 'user', content: promptText });

    if (!currentApiKey) {
      appendMessage({
        role: 'assistant',
        content: 'I need an API key to orchestrate the safety query. Please click the gear icon in the top right of this chat box, select a provider, input your API key, and save it.',
      });
      chatInput.disabled = false;
      chatSendBtn.disabled = false;
      return;
    }

    const statusIndicator = document.createElement('div');
    statusIndicator.className = 'ai-status-indicator';
    statusIndicator.innerHTML = `
      <div class="ai-spinner"></div>
      <span class="ai-status-text">Formulating SQL query...</span>
    `;
    messagesContainer.appendChild(statusIndicator);
    scrollToBottom();

    const updateStatus = (text: string) => {
      const txtSpan = statusIndicator.querySelector('.ai-status-text');
      if (txtSpan) txtSpan.textContent = text;
    };

    let generatedSQL = '';
    let segIds: number[] = [];
    let duckdbRows: any[] = [];

    try {
      updateStatus('Formulating SQL query...');
      const sqlLLMResult = await callLLM(
        currentProvider,
        currentModel,
        currentApiKey,
        SCHEMA_GROUNDING,
        `Generate a DuckDB SQL query for this request: "${promptText}". Return ONLY the query wrapped in a \`\`\`sql ... \`\`\` code block.`
      );

      generatedSQL = extractSQL(sqlLLMResult);
      console.log('[AI Chat] Generated SQL:', generatedSQL);

      updateStatus('Executing query locally on DuckDB...');
      const queryResult = await query(generatedSQL);
      duckdbRows = queryResult.toArray();
      const cleanedRows = cleanQueryResults(duckdbRows);
      console.log('[AI Chat] Query rows count:', cleanedRows.length);

      duckdbRows.forEach((row: any) => {
        if (row.seg_id !== undefined && row.seg_id !== null) {
          const id = Number(row.seg_id);
          if (!isNaN(id)) segIds.push(id);
        }
      });

      if (segIds.length > 0) {
        highlightAndZoomToSegments(segIds);
      }

      updateStatus('Analyzing results & drafting insights...');
      const summarySystemPrompt = `You are a professional transportation safety analyst.
The user asked a safety question. We ran a DuckDB query on local Philly street segment datasets to fetch grounded facts.
Analyze the query results and summarize the findings into a concise, human-readable safety insight.
Do NOT output raw code or raw JSON. Keep it professional and focus on high risk indexes, crashes, speed limits, lack of bike lanes, canopy cover, or other variables.
Suggest safety improvements or highlighting observations.`;

      const summaryUserPrompt = `The user asked: "${promptText}"

Executed SQL Query:
\`\`\`sql
${generatedSQL}
\`\`\`

DuckDB Local Query Results:
\`\`\`json
${JSON.stringify(cleanedRows.slice(0, 15), null, 2)}
\`\`\`
${cleanedRows.length > 15 ? `\n(Note: ${cleanedRows.length - 15} more rows were returned but omitted here for size)` : ''}

Summarize these findings and provide actionable insights.`;

      const summaryResult = await callLLM(
        currentProvider,
        currentModel,
        currentApiKey,
        summarySystemPrompt,
        summaryUserPrompt
      );

      statusIndicator.remove();

      appendMessage({
        role: 'assistant',
        content: summaryResult,
        sql: generatedSQL,
        segIds: segIds.length > 0 ? segIds : undefined,
      });

    } catch (err: any) {
      console.error('[AI Chat] Error:', err);
      statusIndicator.remove();

      appendMessage({
        role: 'assistant',
        content: `Sorry, I encountered an issue orchestrating that safety query.`,
        sql: generatedSQL || undefined,
        error: err.message || String(err),
      });
    } finally {
      chatInput.disabled = false;
      chatSendBtn.disabled = false;
      chatInput.focus();
    }
  });
}
