/**
 * Safety Guard
 * Validates SQL before execution. Driven entirely by config — no hardcoded rules.
 */

export class SafetyGuard {
  constructor(safetyConfig) {
    this.cfg = safetyConfig;
  }

  validate(sql) {
    const trimmed = sql.trim();
    if (!trimmed) throw new SafetyError('Empty query');

    // Strip string literals to avoid false positives on keywords inside values
    const stripped = trimmed
      .replace(/'[^']*'/g, "''")
      .replace(/"[^"]*"/g, '""')
      .toUpperCase();

    // Must start with an allowed statement
    const startsOk = this.cfg.allowedStatements.some(s => stripped.trimStart().startsWith(s));
    if (!startsOk) {
      throw new SafetyError(`Only ${this.cfg.allowedStatements.join('/')} queries are allowed. Got: ${trimmed.slice(0, 40)}`);
    }

    // Block dangerous keywords
    for (const kw of this.cfg.blockedKeywords) {
      if (new RegExp(`\\b${kw}\\b`).test(stripped)) {
        throw new SafetyError(`Blocked keyword detected: ${kw}`);
      }
    }

    return true;
  }

  /** Add a LIMIT clause if missing */
  addLimit(sql, maxRows) {
    const upper = sql.toUpperCase();
    if (upper.includes('LIMIT')) return sql;
    return `${sql.trimEnd()} LIMIT ${maxRows}`;
  }
}

export class SafetyError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SafetyError';
  }
}
