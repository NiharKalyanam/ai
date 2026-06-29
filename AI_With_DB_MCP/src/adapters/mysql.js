import mysql from 'mysql2/promise';
import { BaseAdapter } from './base.js';

export class MySQLAdapter extends BaseAdapter {
  constructor(config) {
    super(config);
    this.pool = null;
  }

  async connect() {
    this.pool = mysql.createPool({
      host: this.config.host,
      port: this.config.port,
      database: this.config.name,
      user: this.config.user,
      password: this.config.password,
      waitForConnections: true,
      connectionLimit: this.config.connectionLimit || 10,
      queueLimit: 0,
    });
    await this.ping();
    return this;
  }

  async query(sql, params = []) {
    const [rows, fields] = await this.pool.query(sql, params);
    return {
      rows: Array.isArray(rows) ? rows : [],
      fields: fields ? fields.map(f => f.name) : Object.keys((rows[0]) || {}),
      rowCount: Array.isArray(rows) ? rows.length : 0,
    };
  }

  async getTables(prefix = '') {
    const sql = prefix
      ? `SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE ? ORDER BY TABLE_NAME`
      : `SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME`;
    const params = prefix ? [`${prefix}%`] : [];
    const [rows] = await this.pool.query(sql, params);
    return rows.map(r => r.TABLE_NAME);
  }

  async getColumns(tableName) {
    const [rows] = await this.pool.query(
      `SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION`,
      [tableName]
    );
    return rows.map(r => ({ name: r.COLUMN_NAME, type: r.DATA_TYPE }));
  }

  async getDistinctValues(tableName, columnName, limit = 15) {
    const [rows] = await this.pool.query(
      `SELECT DISTINCT \`${columnName}\` FROM \`${tableName}\` WHERE \`${columnName}\` IS NOT NULL LIMIT ?`,
      [limit]
    );
    return rows.map(r => r[columnName]).filter(Boolean);
  }

  async ping() {
    await this.pool.query('SELECT 1');
    return true;
  }

  async disconnect() {
    if (this.pool) await this.pool.end();
  }

  get type() { return 'mysql'; }
}
