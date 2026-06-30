/**
 * Slack Bot
 * Connects your MCP tools to Slack via Bolt.
 * Supports: slash commands, @mentions in channels, direct messages.
 *
 * Anyone who gets your code only needs to change these 3 vars in .env:
 *   SLACK_BOT_TOKEN
 *   SLACK_SIGNING_SECRET
 *   SLACK_APP_TOKEN (for socket mode — no public URL needed)
 *
 * Start: node src/slack-bot.js
 */

import 'dotenv/config';
import { App } from '@slack/bolt';
import { config } from '../config/config.js';
import { createAdapter } from './adapters/adapter-factory.js';
import { createAI } from './adapters/ai-factory.js';
import { SchemaDiscovery } from './discovery/schema-discovery.js';
import { SafetyGuard } from './discovery/safety.js';
import { ToolRegistry } from './tools/registry.js';

// ─── Validate Slack config ────────────────────────────────────────────────────
const SLACK_BOT_TOKEN      = process.env.SLACK_BOT_TOKEN;
const SLACK_SIGNING_SECRET = process.env.SLACK_SIGNING_SECRET;
const SLACK_APP_TOKEN      = process.env.SLACK_APP_TOKEN; // xapp-... token for socket mode

if (!SLACK_BOT_TOKEN || !SLACK_SIGNING_SECRET || !SLACK_APP_TOKEN) {
  console.error(`
❌ Missing Slack credentials in .env. You need:

  SLACK_BOT_TOKEN=xoxb-...        (Bot User OAuth Token)
  SLACK_SIGNING_SECRET=...        (Signing Secret)
  SLACK_APP_TOKEN=xapp-...        (App-Level Token with connections:write scope)

Get these from https://api.slack.com/apps → your app → OAuth & Permissions
  `);
  process.exit(1);
}

// ─── MCP tools bootstrap ──────────────────────────────────────────────────────
async function buildRegistry() {
  const adapter = await createAdapter(config.database);
  const schema  = new SchemaDiscovery(adapter, config.schema);
  await schema.build();
  const ai      = await createAI(config.ai);
  const safety  = new SafetyGuard(config.safety);
  const context = { adapter, schema, ai, safety, safetyConfig: config.safety };
  const registry = new ToolRegistry();
  await registry.load(config.tools.enabled, context);
  return registry;
}

// ─── Format MCP result for Slack (mrkdwn) ────────────────────────────────────
function formatForSlack(text, question) {
  if (!text) return '_No results found._';

  // Convert markdown table to Slack code block for readability
  const hasTable = text.includes('| ');
  if (hasTable) {
    const lines = text.split('\n');
    const prose = lines.filter(l => !l.startsWith('|') && !l.startsWith('_')).join('\n').trim();
    const table = lines.filter(l => l.startsWith('|')).join('\n');
    const footer = lines.filter(l => l.startsWith('_')).join('\n');
    return [
      prose ? prose + '\n' : '',
      table ? '```\n' + table + '\n```' : '',
      footer,
    ].filter(Boolean).join('\n');
  }

  return text;
}

// ─── Slack blocks builder ─────────────────────────────────────────────────────
function buildBlocks(question, answer, isError = false) {
  const icon = isError ? '❌' : '✅';
  return [
    {
      type: 'section',
      text: { type: 'mrkdwn', text: `*${icon} IIQ Query*\n_${question}_` }
    },
    { type: 'divider' },
    {
      type: 'section',
      text: { type: 'mrkdwn', text: formatForSlack(answer, question) }
    },
    {
      type: 'context',
      elements: [{ type: 'mrkdwn', text: `Powered by MCP DB Server · ${new Date().toLocaleTimeString()}` }]
    }
  ];
}

// ─── Main ─────────────────────────────────────────────────────────────────────
async function startSlackBot() {
  console.log('\n💬 Slack Bot starting...');

  let registry;
  try {
    registry = await buildRegistry();
    console.log(`[Tools] Active: ${registry.list().join(', ')}`);
  } catch (e) {
    console.error('Failed to init MCP tools:', e.message);
    process.exit(1);
  }

  // Socket Mode — no public URL needed, works locally
  const app = new App({
    token: SLACK_BOT_TOKEN,
    signingSecret: SLACK_SIGNING_SECRET,
    socketMode: true,
    appToken: SLACK_APP_TOKEN,
  });

  // ── /iiq slash command ────────────────────────────────────────────────────
  // Usage: /iiq how many failed provisioning tasks last week?
  app.command('/iiq', async ({ command, ack, respond }) => {
    await ack();
    const question = command.text?.trim();

    if (!question) {
      return respond({
        response_type: 'ephemeral',
        text: 'Usage: `/iiq <your question>`\nExample: `/iiq how many identities are in the system?`'
      });
    }

    // Show typing indicator
    await respond({ response_type: 'in_channel', text: `_Querying IIQ database..._` });

    try {
      const result = await registry.execute('query_database', { question });
      const answer = result.content?.[0]?.text || 'No results.';
      await respond({
        response_type: 'in_channel',
        blocks: buildBlocks(question, answer, result.isError),
        text: answer, // fallback
      });
    } catch (e) {
      await respond({ response_type: 'ephemeral', text: `❌ Error: ${e.message}` });
    }
  });

  // ── @mention in channel ───────────────────────────────────────────────────
  // Usage: @IIQBot how many users failed provisioning?
  app.event('app_mention', async ({ event, say }) => {
    const botUserId = (await app.client.auth.test()).user_id;
    const question  = event.text.replace(`<@${botUserId}>`, '').trim();

    if (!question) {
      return say({ thread_ts: event.ts, text: 'Hi! Ask me anything about your IIQ database.\nExample: `how many identities are in the system?`' });
    }

    try {
      const result = await registry.execute('query_database', { question });
      const answer = result.content?.[0]?.text || 'No results.';
      await say({
        thread_ts: event.ts,
        blocks: buildBlocks(question, answer, result.isError),
        text: answer,
      });
    } catch (e) {
      await say({ thread_ts: event.ts, text: `❌ Error: ${e.message}` });
    }
  });

  // ── Direct message ────────────────────────────────────────────────────────
  // Just DM the bot with any question
  app.message(async ({ message, say }) => {
    if (message.subtype) return; // skip bot messages, edits, etc.
    const question = message.text?.trim();
    if (!question) return;

    try {
      const result = await registry.execute('query_database', { question });
      const answer = result.content?.[0]?.text || 'No results.';
      await say({
        blocks: buildBlocks(question, answer, result.isError),
        text: answer,
      });
    } catch (e) {
      await say(`❌ Error: ${e.message}`);
    }
  });

  // ── /iiq-schema slash command ─────────────────────────────────────────────
  app.command('/iiq-schema', async ({ ack, respond }) => {
    await ack();
    try {
      const result = await registry.execute('describe_schema', { summary: true });
      const text   = result.content?.[0]?.text || '';
      await respond({ response_type: 'ephemeral', text: '```\n' + text + '\n```' });
    } catch (e) {
      await respond({ response_type: 'ephemeral', text: `❌ ${e.message}` });
    }
  });

  // ── /iiq-sample slash command ─────────────────────────────────────────────
  // Usage: /iiq-sample spt_identity
  app.command('/iiq-sample', async ({ command, ack, respond }) => {
    await ack();
    const table = command.text?.trim();
    if (!table) return respond({ response_type: 'ephemeral', text: 'Usage: `/iiq-sample <table_name>`' });
    try {
      const result = await registry.execute('sample_data', { table, limit: 5 });
      const text   = result.content?.[0]?.text || '';
      await respond({ response_type: 'ephemeral', text: '```\n' + text + '\n```' });
    } catch (e) {
      await respond({ response_type: 'ephemeral', text: `❌ ${e.message}` });
    }
  });

  await app.start();
  console.log(`\n✅ Slack bot running (socket mode — no public URL needed)`);
  console.log(`\n   Slash commands registered:`);
  console.log(`   /iiq <question>     — query the database`);
  console.log(`   /iiq-schema         — show DB schema summary`);
  console.log(`   /iiq-sample <table> — preview a table`);
  console.log(`\n   Also listens to @mentions and direct messages.`);
  console.log(`\n   Add these slash commands in your Slack app at:`);
  console.log(`   https://api.slack.com/apps → Slash Commands`);
}

startSlackBot().catch(e => {
  console.error('Fatal:', e.message);
  process.exit(1);
});
