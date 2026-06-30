/**
 * Tool: query_database
 * Converts natural language → SQL → executes → returns results.
 * Supports any AI provider configured in config.ai
 */

export const name = 'query_database';

export const definition = {
  name,
  description: 'Ask a plain English question about the database. Automatically generates and executes the SQL query.',
  inputSchema: {
    type: 'object',
    properties: {
      question: {
        type: 'string',
        description: 'Plain English question about the data (e.g. "How many users failed provisioning last week?")',
      },
      explain: {
        type: 'boolean',
        description: 'If true, also return the generated SQL and an explanation.',
        default: false,
      },
    },
    required: ['question'],
  },
};

export function createHandler({ adapter, schema, safety, ai, safetyConfig }) {
  return async function ({ question, explain = false }) {
    // 1. Build system prompt from live schema
    const systemPrompt = buildSystemPrompt(schema.getText(), adapter.type);

    // 2. Ask AI to generate SQL
    let sql, explanation;
    try {
      const result = await ai.generateSQL(systemPrompt, question);
      sql = result.sql;
      explanation = result.explanation;
    } catch (e) {
      return errorResult(`AI failed to generate SQL: ${e.message}`);
    }

    if (!sql) return errorResult('AI could not generate a SQL query for this question.');

    // 3. Safety check
    try {
      safety.validate(sql);
      sql = safety.addLimit(sql, safetyConfig.maxRowsReturned);
    } catch (e) {
      return errorResult(`Query blocked by safety guard: ${e.message}`);
    }

    // 4. Execute
    let queryResult;
    try {
      queryResult = await adapter.query(sql);
    } catch (e) {
      return errorResult(`Query execution failed: ${e.message}\nSQL: ${sql}`);
    }

    // 5. Format output
    const output = formatOutput(queryResult, sql, explanation, explain);
    return { content: [{ type: 'text', text: output }] };
  };
}

function buildSystemPrompt(schemaText, dbType) {
  return [
    `You are a ${dbType.toUpperCase()} SQL expert. Generate ONLY SELECT queries.`,
    '',
    'KEY TABLE RELATIONSHIPS (always use these for joins):',
    '- Identity info       → spt_identity (id, name, display_name, manager, email, inactive)',
    '- App accounts        → spt_link (identity_id=spt_identity.id, application=spt_application.id, native_identity, disabled)',
    '- Applications        → spt_application (id, name)',
    '- Entitlements        → spt_identity_entitlement (identity_id=spt_identity.id, application=spt_application.id, name, value, display_name, type)',
    '- Certifications      → spt_certification (id, name, phase, complete, percent_complete)',
    '- Cert items          → spt_certification_item (certification_id, identity=name of identity, exception_application)',
    '- Provisioning        → spt_provisioning_transaction (identity_name, application, op, status, created)',
    '- Work items          → spt_work_item (owner_id=spt_identity.id, type, state, created)',
    '- Roles               → spt_bundle (id, name, type)',
    '- Role assignments    → spt_identity_role (identity_id=spt_identity.id, bundle_id=spt_bundle.id)',
    '- Audit events        → spt_audit_event (id, created, action, source, target, application)',
    '',
    'COMMON REPORT PATTERNS:',
    '- "manager report" or "who reports to X"   → JOIN spt_identity ON manager = manager_id or WHERE manager = X',
    '- "entitlement report"                      → JOIN spt_identity i, spt_identity_entitlement ie ON i.id=ie.identity_id, spt_application a ON ie.application=a.id',
    '- "access report"                           → JOIN spt_identity i, spt_link l ON i.id=l.identity_id, spt_application a ON l.application=a.id',
    '- "failed provisioning"                     → spt_provisioning_transaction WHERE status != "Committed"',
    '- "inactive users"                          → spt_identity WHERE inactive = 1',
    '- "pending certifications"                  → spt_certification WHERE complete = 0',
    '',
    'RULES:',
    '1. Use ONLY column names from the schema below. NEVER invent columns.',
    '2. "report/show/list/give me" = SELECT real columns, NOT COUNT(*).',
    '3. Use COUNT(*) only when user says "how many" or "count".',
    '4. Always LIMIT 100 on reports unless user asks for more.',
    '5. Use LOWER() for name searches. Use exact case for status values.',
    '6. Never use INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE.',
    '',
    'RESPONSE FORMAT — reply ONLY with JSON, no markdown:',
    '{"sql": "SELECT ...", "explanation": "one sentence"}',
    '',
    schemaText,
  ].join('\n');
}

function formatOutput(result, sql, explanation, includeSQL) {
  const parts = [];

  if (result.rowCount === 0) {
    parts.push('Query returned 0 rows.');
  } else {
    parts.push(`Returned ${result.rowCount} row(s).\n`);
    parts.push(toMarkdownTable(result.rows, result.fields));
  }

  if (includeSQL) {
    parts.push(`\n**SQL:** \`\`\`sql\n${sql}\n\`\`\``);
    if (explanation) parts.push(`**What it does:** ${explanation}`);
  }

  return parts.join('\n');
}

function toMarkdownTable(rows, fields) {
  if (!rows.length || !fields.length) return '';
  const header = '| ' + fields.join(' | ') + ' |';
  const sep    = '| ' + fields.map(() => '---').join(' | ') + ' |';
  const dataRows = rows.slice(0, 50).map(row =>
    '| ' + fields.map(f => String(row[f] ?? '')).join(' | ') + ' |'
  );
  const lines = [header, sep, ...dataRows];
  if (rows.length > 50) lines.push(`_... and ${rows.length - 50} more rows_`);
  return lines.join('\n');
}

function errorResult(message) {
  return { content: [{ type: 'text', text: `❌ ${message}` }], isError: true };
}
