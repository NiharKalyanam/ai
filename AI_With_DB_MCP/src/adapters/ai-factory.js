/**
 * AI Provider Factory
 */

class AnthropicAI {
  constructor(aiConfig) {
    this.config = aiConfig;
    this.client = null;
  }

  async init() {
    const { default: Anthropic } = await import('@anthropic-ai/sdk');
    const apiKey = process.env.ANTHROPIC_API_KEY || this.config.apiKey;
    this.client = new Anthropic({ apiKey });
    return this;
  }

  async generateSQL(systemPrompt, question) {
    const resp = await this.client.messages.create({
      model: this.config.model || 'claude-sonnet-4-5',
      max_tokens: this.config.maxTokens || 1024,
      system: systemPrompt,
      messages: [{ role: 'user', content: question }],
    });
    const text = resp.content.find(b => b.type === 'text')?.text || '';
    return parseAIResponse(text);
  }

  get name() { return `anthropic/${this.config.model}`; }
}

class OpenAIAI {
  constructor(aiConfig) {
    this.config = aiConfig;
    this.client = null;
  }

  async init() {
    const { default: OpenAI } = await import('openai');
    const apiKey = process.env.OPENAI_API_KEY || this.config.apiKey;
    this.client = new OpenAI({ apiKey });
    return this;
  }

  async generateSQL(systemPrompt, question) {
    const resp = await this.client.chat.completions.create({
      model: this.config.model || 'gpt-4o',
      max_tokens: this.config.maxTokens || 1024,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: question },
      ],
    });
    const text = resp.choices[0]?.message?.content || '';
    return parseAIResponse(text);
  }

  get name() { return `openai/${this.config.model}`; }
}

class NoAI {
  async init() { return this; }
  async generateSQL() {
    throw new Error('No AI provider configured. Set AI_PROVIDER=anthropic or openai in .env');
  }
  get name() { return 'none'; }
}

const AI_REGISTRY = {
  anthropic: AnthropicAI,
  openai: OpenAIAI,
  none: NoAI,
};

export async function createAI(aiConfig) {
  const provider = (aiConfig.provider || 'anthropic').toLowerCase();
  const AIClass = AI_REGISTRY[provider];
  if (!AIClass) throw new Error(`Unknown AI_PROVIDER="${provider}". Supported: ${Object.keys(AI_REGISTRY).join(', ')}`);
  console.error(`[AI] Initializing provider: ${provider}`);
  const ai = new AIClass(aiConfig);
  await ai.init();
  console.error(`[AI] Ready: ${ai.name}`);
  return ai;
}

export function registerAI(name, AIClass) {
  AI_REGISTRY[name.toLowerCase()] = AIClass;
}

function parseAIResponse(text) {
  const clean = text.replace(/^```[a-z]*\n?/i, '').replace(/\n?```$/, '').trim();
  try {
    const parsed = JSON.parse(clean);
    return { sql: parsed.sql?.trim(), explanation: parsed.explanation };
  } catch {
    const sqlMatch = clean.match(/SELECT[\s\S]+/i);
    if (sqlMatch) return { sql: sqlMatch[0].trim(), explanation: '' };
    return { sql: null, explanation: clean };
  }
}