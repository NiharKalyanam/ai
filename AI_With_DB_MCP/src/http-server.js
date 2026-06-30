/**
 * HTTP Transport Layer
 * Serves UI at http://localhost:3344
 * Start: node src/http-server.js
 */

// dotenv MUST load before config.js is imported
// We do this by NOT importing config.js at all — read process.env directly below.
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { createAdapter } from './adapters/adapter-factory.js';
import { createAI } from './adapters/ai-factory.js';
import { SchemaDiscovery } from './discovery/schema-discovery.js';
import { SafetyGuard } from './discovery/safety.js';
import { ToolRegistry } from './tools/registry.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ─── Build config directly from process.env (already loaded by dotenv above) ──
function getConfig() {
  return {
    database: {
      type:           process.env.DB_TYPE           || 'mysql',
      host:           process.env.DB_HOST           || 'localhost',
      port:           parseInt(process.env.DB_PORT  || '3306'),
      name:           process.env.DB_NAME           || 'identityiq',
      user:           process.env.DB_USER           || 'root',
      password:       process.env.DB_PASSWORD       || '',
      file:           process.env.DB_FILE           || './data.db',
      tablePrefix:    process.env.DB_TABLE_PREFIX   || '',
      connectionLimit: 10,
    },
    ai: {
      provider:  process.env.AI_PROVIDER  || 'anthropic',
      model:     process.env.AI_MODEL     || 'claude-sonnet-4-5',
      apiKey:    process.env.ANTHROPIC_API_KEY || process.env.OPENAI_API_KEY || '',
      maxTokens: parseInt(process.env.AI_MAX_TOKENS || '2048'),
    },
    tools: {
      enabled: (process.env.MCP_TOOLS || 'query_database,describe_schema,sample_data,search_records')
        .split(',').map(t => t.trim()),
    },
    schema: {
      autoDiscover:      process.env.SCHEMA_AUTO_DISCOVER !== 'false',
      maxTablesInContext: parseInt(process.env.SCHEMA_MAX_TABLES || '50'),
      enumColumnNames:   (process.env.SCHEMA_ENUM_COLUMNS || 'status,state,type,phase,action,op,operation,source,level,completion_status,result,severity,outcome').split(','),
      maxEnumValues:     parseInt(process.env.SCHEMA_MAX_ENUM_VALUES || '15'),
      skipColumns:       (process.env.SCHEMA_SKIP_COLUMNS || 'attributes,xml,extended_attributes,scorecard,preferences,arguments,config').split(','),
    },
    safety: {
      allowedStatements: ['SELECT', 'WITH'],
      blockedKeywords:   ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE'],
      maxRowsReturned:   parseInt(process.env.MAX_ROWS || '500'),
    },
  };
}

// ─── Auth ──────────────────────────────────────────────────────────────────────
const API_TOKEN = process.env.API_TOKEN || 'change-me-before-sharing';

function requireAuth(req, res, next) {
  const header = req.headers['authorization'] || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : req.query.token;
  if (!token || token !== API_TOKEN) {
    return res.status(401).json({ error: 'Unauthorized. Pass: Authorization: Bearer <API_TOKEN>' });
  }
  next();
}

// ─── Webhook verifier ──────────────────────────────────────────────────────────
function verifyWebhook(req, res, next) {
  const secret = process.env.WEBHOOK_SECRET;
  if (!secret) return next();
  const sig = req.headers['x-hub-signature-256'] || req.headers['x-webhook-signature'] || '';
  if (!sig) return res.status(400).json({ error: 'Missing webhook signature' });
  import('crypto').then(({ createHmac }) => {
    const expected = 'sha256=' + createHmac('sha256', secret).update(JSON.stringify(req.body)).digest('hex');
    if (sig !== expected) return res.status(403).json({ error: 'Invalid webhook signature' });
    next();
  });
}

// ─── Webhook question extractor ────────────────────────────────────────────────
function extractQuestionFromWebhook(payload) {
  if (payload.pull_request) return `Show recent provisioning activity for user ${payload.pull_request.user?.login}`;
  if (payload.issue)        return `Show recent failed provisioning transactions`;
  return payload.question || payload.text || payload.message || payload.query || null;
}

// ─── Main ──────────────────────────────────────────────────────────────────────
async function startHTTPServer() {
  console.log('\n🌐 MCP HTTP Server starting...');

  const config = getConfig();

  // Verify key is loaded
  console.log(`[ENV] ANTHROPIC_API_KEY loaded: ${config.ai.apiKey ? 'YES (' + config.ai.apiKey.slice(0,15) + '...)' : 'NO ← CHECK YOUR .env FILE'}`);
  console.log(`[ENV] DB_PASSWORD loaded: ${config.database.password ? 'YES' : 'NO (empty)'}`);

  const adapter  = await createAdapter(config.database);
  const schema   = new SchemaDiscovery(adapter, config.schema);
  await schema.build();
  const ai       = await createAI(config.ai);
  const safety   = new SafetyGuard(config.safety);
  const context  = { adapter, schema, ai, safety, safetyConfig: config.safety };
  const registry = new ToolRegistry();
  await registry.load(config.tools.enabled, context);
  console.log(`[Tools] Active: ${registry.list().join(', ')}`);

  const app = express();
  app.use(cors());
  app.use(express.json());

  // Serve UI
  app.use(express.static(join(__dirname, '../ui')));
  app.get('/', (req, res) => res.sendFile(join(__dirname, '../ui/index.html')));

  // Health (public)
  app.get('/health', async (req, res) => {
    try {
      await adapter.ping();
      res.json({ status: 'ok', db: `${config.database.type}/${config.database.name}`, ai: `${config.ai.provider}/${config.ai.model}`, tools: registry.list(), schema: schema.getSummary() });
    } catch (e) { res.status(500).json({ status: 'error', message: e.message }); }
  });

  // List tools
  app.get('/api/tools', requireAuth, (req, res) => res.json({ tools: registry.getDefinitions() }));

  // Ask in plain English
  app.post('/api/ask', requireAuth, async (req, res) => {
    const { question, explain = false } = req.body;
    if (!question?.trim()) return res.status(400).json({ error: 'question is required' });
    try {
      const result = await registry.execute('query_database', { question, explain });
      res.json({ answer: result.content?.[0]?.text || '', isError: result.isError || false });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  // Call any tool directly
  app.post('/api/tools/:toolName', requireAuth, async (req, res) => {
    const { toolName } = req.params;
    if (!registry.has(toolName)) return res.status(404).json({ error: `Tool "${toolName}" not found`, available: registry.list() });
    try {
      const result = await registry.execute(toolName, req.body || {});
      res.json({ result: result.content?.[0]?.text, isError: result.isError || false });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  // Schema
  app.get('/api/schema', requireAuth, async (req, res) => {
    const result = await registry.execute('describe_schema', { summary: req.query.summary === 'true' });
    res.json({ schema: result.content?.[0]?.text });
  });

  // Webhooks
  app.post('/api/webhook', verifyWebhook, async (req, res) => {
    const question = extractQuestionFromWebhook(req.body);
    if (!question) return res.status(400).json({ error: 'Add a "question" field to your webhook payload.' });
    console.log(`[Webhook] ${question}`);
    try {
      const result = await registry.execute('query_database', { question });
      res.json({ question, answer: result.content?.[0]?.text || '', timestamp: new Date().toISOString() });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  const PORT = process.env.HTTP_PORT || 3344;
  app.listen(PORT, () => {
    console.log(`\n✅ HTTP server ready`);
    console.log(`\n   🌐 Open UI:  http://localhost:${PORT}`);
    console.log(`   🔑 Token:    ${API_TOKEN}`);
    console.log(`\n   POST /api/ask  →  { "question": "how many identities?" }`);
  });
}

startHTTPServer().catch(e => { console.error('Fatal:', e.message); process.exit(1); });