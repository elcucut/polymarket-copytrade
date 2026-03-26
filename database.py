import sqlite3
from datetime import datetime
import json

class Database:
    DB_FILE = "copytrade.db"
    
    def __init__(self, db_file=None):
        self.db_file = db_file or self.DB_FILE
    
    def _connect(self):
        return sqlite3.connect(self.db_file)
    
    def init_db(self):
        """Crea las tablas si no existen y migra si es necesario"""
        conn = self._connect()
        cursor = conn.cursor()
        
        # Tabla de trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                trader_address TEXT,
                trader_name TEXT,
                market_question TEXT,
                outcome TEXT,
                token_id TEXT,
                amount_usdc REAL,
                price_at_entry REAL,
                price_at_exit REAL,
                status TEXT,
                skip_reason TEXT,
                pnl REAL DEFAULT 0
            )
        ''')
        
        # Verificar si necesitamos migrar columnas (para DB existentes)
        try:
            cursor.execute("SELECT price_at_exit FROM trades LIMIT 1")
        except sqlite3.OperationalError:
            # La columna no existe, agregarla
            cursor.execute("ALTER TABLE trades ADD COLUMN price_at_exit REAL")
            conn.commit()
            print("✅ Columna price_at_exit agregada a la base de datos")
        
        # Tabla de snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                trader_address TEXT PRIMARY KEY,
                positions_json TEXT,
                updated_at TEXT
            )
        ''')
        
        # Tabla de estadísticas diarias
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_invested REAL DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                trades_count INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_trade(self, trade_dict):
        """Inserta un nuevo trade"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades 
            (timestamp, trader_address, trader_name, market_question, outcome, 
             token_id, amount_usdc, price_at_entry, price_at_exit, status, skip_reason, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_dict.get('timestamp'),
            trade_dict.get('trader_address'),
            trade_dict.get('trader_name'),
            trade_dict.get('market_question'),
            trade_dict.get('outcome'),
            trade_dict.get('token_id'),
            trade_dict.get('amount_usdc'),
            trade_dict.get('price_at_entry'),
            trade_dict.get('price_at_exit'),
            trade_dict.get('status'),
            trade_dict.get('skip_reason', ''),
            trade_dict.get('pnl', 0)
        ))
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id
    
    def get_trades(self, limit=50):
        """Devuelve los últimos trades"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM trades 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    
    def get_snapshot(self, address):
        """Devuelve el snapshot anterior de un trader"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT positions_json FROM snapshots 
            WHERE trader_address = ?
        ''', (address,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return []
    
    def save_snapshot(self, address, positions):
        """Guarda el snapshot actual de posiciones"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO snapshots 
            (trader_address, positions_json, updated_at)
            VALUES (?, ?, ?)
        ''', (address, json.dumps(positions), datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_daily_loss_today(self):
        """Suma las inversiones de hoy"""
        conn = self._connect()
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COALESCE(SUM(amount_usdc), 0) FROM trades 
            WHERE date(timestamp) = ? AND status = 'executed'
        ''', (today,))
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    def get_total_pnl(self):
        """Suma todo el P&L"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COALESCE(SUM(pnl), 0) FROM trades 
            WHERE status = 'executed'
        ''')
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    def update_trade_pnl(self, trade_id, pnl, exit_price=None):
        """Actualiza el P&L y opcionalmente el precio de salida de un trade"""
        conn = self._connect()
        cursor = conn.cursor()
        if exit_price is not None:
            cursor.execute('''
                UPDATE trades SET pnl = ?, price_at_exit = ? WHERE id = ?
            ''', (pnl, exit_price, trade_id))
        else:
            cursor.execute('''
                UPDATE trades SET pnl = ? WHERE id = ?
            ''', (pnl, trade_id))
        conn.commit()
        conn.close()
    
    def get_trades_by_trader(self, trader_name=None, status=None):
        """Obtiene trades filtrados por trader y/o estado"""
        conn = self._connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if trader_name:
            query += " AND trader_name = ?"
            params.append(trader_name)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    
    def get_trader_performance(self):
        """Obtiene estadísticas de rendimiento por trader"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                trader_name,
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'executed' THEN 1 ELSE 0 END) as executed,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN status = 'executed' THEN amount_usdc ELSE 0 END) as total_invested,
                SUM(pnl) as total_pnl,
                AVG(CASE WHEN pnl != 0 THEN (pnl / amount_usdc * 100) ELSE NULL END) as avg_pnl_pct
            FROM trades 
            WHERE status IN ('executed', 'closed')
            GROUP BY trader_name
            ORDER BY total_pnl DESC
        ''')
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
    
    def close_trade(self, trade_id, exit_price, pnl):
        """Marca un trade como cerrado con su precio de salida y P&L"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE trades 
            SET status = 'closed', price_at_exit = ?, pnl = ? 
            WHERE id = ?
        ''', (exit_price, pnl, trade_id))
        conn.commit()
        conn.close()
