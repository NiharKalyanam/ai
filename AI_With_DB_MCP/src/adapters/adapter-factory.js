/**
 * Adapter Factory
 * Returns the right DB adapter based on config.database.type.
 * To add a new DB: create src/adapters/yourdb.js → register here.
 */
import { MySQLAdapter } from './mysql.js';
import { PostgresAdapter } from './postgres.js';
import { SQLiteAdapter } from './sqlite.js';

const REGISTRY = {
  mysql: MySQLAdapter,
  postgres: PostgresAdapter,
  postgresql: PostgresAdapter, // alias
  sqlite: SQLiteAdapter,
  sqlite3: SQLiteAdapter,      // alias
};

export async function createAdapter(dbConfig) {
  const type = (dbConfig.type || 'mysql').toLowerCase();
  const AdapterClass = REGISTRY[type];

  if (!AdapterClass) {
    const supported = Object.keys(REGISTRY).join(', ');
    throw new Error(`Unknown DB_TYPE="${type}". Supported: ${supported}`);
  }

  console.error(`[DB] Connecting via ${type} adapter...`);
  const adapter = new AdapterClass(dbConfig);
  await adapter.connect();
  console.error(`[DB] Connected to ${type} (${dbConfig.name || dbConfig.file})`);
  return adapter;
}

/** Register a custom adapter at runtime — use this in plugins/extensions */
export function registerAdapter(name, AdapterClass) {
  REGISTRY[name.toLowerCase()] = AdapterClass;
  console.error(`[DB] Custom adapter registered: ${name}`);
}
