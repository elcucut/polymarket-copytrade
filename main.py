import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import os
from datetime import datetime
from database import Database
from trader import CopyTrader
from telegram_bot import notify_test


class App:
    """Aplicación principal con UI Tkinter"""
    
    CONFIG_FILE = "config.json"
    
    def __init__(self, root):
        self.root = root
        self.root.title("Polymarket Copy Trader")
        self.root.geometry("900x700")
        self.root.configure(bg='#1a1a2e')
        self.root.minsize(800, 600)
        
        # Configurar estilo dark
        self.setup_styles()
        
        # Cargar configuración
        self.config = self.load_config()
        
        # Inicializar base de datos
        self.db = Database()
        self.db.init_db()
        
        # Variables del bot
        self.trader = None
        self.trader_thread = None
        
        # Construir UI
        self.build_ui()
        
        # Actualizar estadísticas
        self.refresh_stats()
        self.refresh_trades()
    
    def setup_styles(self):
        """Configura los estilos de la UI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores
        bg_color = '#1a1a2e'
        fg_color = 'white'
        accent_color = '#7c3aed'
        secondary_bg = '#0d0d1a'
        
        # Configurar estilos
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10), padding=5)
        style.configure('TEntry', font=('Segoe UI', 10))
        style.configure('TNotebook', background=bg_color, tabmargins=[2, 5, 2, 0])
        style.configure('TNotebook.Tab', font=('Segoe UI', 10, 'bold'), padding=[10, 5])
        
        # Colores de las pestañas
        style.map('TNotebook.Tab',
            background=[('selected', accent_color), ('!selected', secondary_bg)],
            foreground=[('selected', 'white'), ('!selected', '#888')]
        )
        
        # Treeview estilo dark
        style.configure('Treeview', 
            background=secondary_bg, 
            foreground=fg_color, 
            fieldbackground=secondary_bg,
            font=('Segoe UI', 9)
        )
        style.configure('Treeview.Heading', 
            background=accent_color, 
            foreground='white',
            font=('Segoe UI', 10, 'bold')
        )
        style.map('Treeview', 
            background=[('selected', accent_color)],
            foreground=[('selected', 'white')]
        )
    
    def build_ui(self):
        """Construye la interfaz de usuario"""
        # Notebook (pestañas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Crear pestañas
        self.build_control_tab()
        self.build_traders_tab()
        self.build_config_tab()
        self.build_history_tab()
    
    def build_control_tab(self):
        """Pestaña de Panel de Control"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Panel de Control")
        
        # Frame superior - Estado
        status_frame = ttk.LabelFrame(tab, text="Estado del Bot", padding=10)
        status_frame.pack(fill='x', padx=10, pady=10)
        
        # Indicador de estado
        self.status_label = ttk.Label(
            status_frame, 
            text="⚫ DETENIDO",
            font=('Segoe UI', 24, 'bold'),
            foreground='#ff4444'
        )
        self.status_label.pack(pady=10)
        
        # Botones de control
        btn_frame = ttk.Frame(status_frame)
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            btn_frame,
            text="▶ INICIAR BOT",
            bg='#22c55e',
            fg='white',
            font=('Segoe UI', 12, 'bold'),
            padx=30,
            pady=10,
            command=self.start_bot,
            cursor='hand2'
        )
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹ DETENER",
            bg='#ef4444',
            fg='white',
            font=('Segoe UI', 12, 'bold'),
            padx=30,
            pady=10,
            command=self.stop_bot,
            state='disabled',
            cursor='hand2'
        )
        self.stop_btn.pack(side='left', padx=5)
        
        # Estadísticas rápidas
        stats_frame = ttk.Frame(status_frame)
        stats_frame.pack(fill='x', pady=10)
        
        self.balance_label = ttk.Label(stats_frame, text="Balance USDC: $---", font=('Segoe UI', 12))
        self.balance_label.pack(side='left', padx=20)
        
        self.daily_loss_label = ttk.Label(stats_frame, text="Pérdida hoy: $0.00", font=('Segoe UI', 12))
        self.daily_loss_label.pack(side='left', padx=20)
        
        self.total_pnl_label = ttk.Label(stats_frame, text="P&L total: $0.00", font=('Segoe UI', 12))
        self.total_pnl_label.pack(side='left', padx=20)
        
        # Frame inferior - Log
        log_frame = ttk.LabelFrame(tab, text="Log en tiempo real", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            bg='#0d0d1a',
            fg='#00ff88',
            font=('Consolas', 10),
            state='disabled',
            wrap='word'
        )
        self.log_text.pack(fill='both', expand=True)
    
    def build_traders_tab(self):
        """Pestaña de Traders Seguidos"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Traders Seguidos")
        
        # Formulario para añadir trader
        add_frame = ttk.LabelFrame(tab, text="Añadir Nuevo Trader", padding=10)
        add_frame.pack(fill='x', padx=10, pady=10)
        
        # Dirección
        ttk.Label(add_frame, text="Dirección wallet (0x...):").grid(row=0, column=0, sticky='w', pady=5)
        self.trader_address_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.trader_address_var, width=50).grid(row=0, column=1, padx=5)
        
        # Nombre
        ttk.Label(add_frame, text="Nombre (opcional):").grid(row=1, column=0, sticky='w', pady=5)
        self.trader_name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.trader_name_var, width=30).grid(row=1, column=1, sticky='w', padx=5)
        
        # Win Rate
        ttk.Label(add_frame, text="Win Rate (0-1, ej: 0.65):").grid(row=2, column=0, sticky='w', pady=5)
        self.trader_winrate_var = tk.StringVar(value="0.50")
        ttk.Entry(add_frame, textvariable=self.trader_winrate_var, width=10).grid(row=2, column=1, sticky='w', padx=5)
        
        # Botón añadir
        ttk.Button(add_frame, text="➕ Añadir Trader", command=self.add_trader).grid(row=3, column=0, columnspan=2, pady=10)
        
        # Lista de traders
        list_frame = ttk.LabelFrame(tab, text="Traders Configurados", padding=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Treeview
        columns = ('Nombre', 'Dirección', 'Win Rate', 'Estado')
        self.traders_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.traders_tree.heading(col, text=col)
            if col == 'Nombre':
                self.traders_tree.column(col, width=150)
            elif col == 'Dirección':
                self.traders_tree.column(col, width=250)
            elif col == 'Win Rate':
                self.traders_tree.column(col, width=80)
            else:
                self.traders_tree.column(col, width=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.traders_tree.yview)
        self.traders_tree.configure(yscrollcommand=scrollbar.set)
        
        self.traders_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Botones de acción
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="🗑️ Eliminar Seleccionado", command=self.remove_trader).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="⏸️ Activar/Desactivar", command=self.toggle_trader).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔄 Actualizar Lista", command=self.refresh_traders_list).pack(side='left', padx=5)
        
        # Cargar traders existentes
        self.refresh_traders_list()
    
    def build_config_tab(self):
        """Pestaña de Configuración"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Configuración")
        
        # Canvas con scrollbar para contenido extenso
        canvas = tk.Canvas(tab, bg='#1a1a2e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient='vertical', command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Wallet
        wallet_frame = ttk.LabelFrame(scroll_frame, text="Wallet", padding=10)
        wallet_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(wallet_frame, text="Private Key:").grid(row=0, column=0, sticky='w', pady=5)
        self.pk_var = tk.StringVar()
        self.pk_entry = ttk.Entry(wallet_frame, textvariable=self.pk_var, width=50, show='*')
        self.pk_entry.grid(row=0, column=1, padx=5)
        ttk.Button(wallet_frame, text="👁", width=3, command=self.toggle_pk_visibility).grid(row=0, column=2)
        
        ttk.Label(wallet_frame, text="Funder Address:").grid(row=1, column=0, sticky='w', pady=5)
        self.funder_var = tk.StringVar()
        ttk.Entry(wallet_frame, textvariable=self.funder_var, width=50).grid(row=1, column=1, padx=5)
        
        ttk.Label(wallet_frame, text="Tipo de Firma:").grid(row=2, column=0, sticky='w', pady=5)
        self.sig_type_var = tk.IntVar(value=1)
        sig_frame = ttk.Frame(wallet_frame)
        sig_frame.grid(row=2, column=1, sticky='w', padx=5)
        ttk.Radiobutton(sig_frame, text="0 = EOA/MetaMask", variable=self.sig_type_var, value=0).pack(side='left')
        ttk.Radiobutton(sig_frame, text="1 = Email/Magic", variable=self.sig_type_var, value=1).pack(side='left')
        ttk.Radiobutton(sig_frame, text="2 = Browser", variable=self.sig_type_var, value=2).pack(side='left')

        # RPC URL para consultas on-chain (opcional)
        ttk.Label(wallet_frame, text="Polygon RPC (opcional):").grid(row=3, column=0, sticky='w', pady=5)
        self.rpc_var = tk.StringVar()
        rpc_entry = ttk.Entry(wallet_frame, textvariable=self.rpc_var, width=50)
        rpc_entry.grid(row=3, column=1, padx=5)
        ttk.Label(wallet_frame, text="Para modo 'Copiar % trader' - Alchemy/Infura",
                 font=('Segoe UI', 8), foreground='#94a3b8').grid(row=4, column=1, sticky='w', padx=5)
        
        # Trading
        trading_frame = ttk.LabelFrame(scroll_frame, text="Estrategia de Trading", padding=10)
        trading_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(trading_frame, text="Modo:").grid(row=0, column=0, sticky='w', pady=5)
        self.mode_var = tk.StringVar(value='fixed')
        mode_frame = ttk.Frame(trading_frame)
        mode_frame.grid(row=0, column=1, sticky='w', padx=5)
        ttk.Radiobutton(mode_frame, text="Cantidad fija", variable=self.mode_var, value='fixed').pack(side='left')
        ttk.Radiobutton(mode_frame, text="% del portfolio", variable=self.mode_var, value='portfolio_pct').pack(side='left')
        ttk.Radiobutton(mode_frame, text="Copiar % trader", variable=self.mode_var, value='copy_trader_pct').pack(side='left')

        # Label explicativo para copy_trader_pct
        ttk.Label(trading_frame, text="💡 Copiar % de exposición del trader: invierte el mismo porcentaje que el trader invierte de su portfolio",
                 font=('Segoe UI', 8), foreground='#94a3b8').grid(row=0, column=2, sticky='w', padx=5)
        
        ttk.Label(trading_frame, text="Cantidad fija ($):").grid(row=1, column=0, sticky='w', pady=5)
        self.fixed_var = tk.StringVar(value="5.0")
        ttk.Entry(trading_frame, textvariable=self.fixed_var, width=15).grid(row=1, column=1, sticky='w', padx=5)
        
        ttk.Label(trading_frame, text="% Portfolio:").grid(row=2, column=0, sticky='w', pady=5)
        self.pct_var = tk.StringVar(value="2.0")
        ttk.Entry(trading_frame, textvariable=self.pct_var, width=15).grid(row=2, column=1, sticky='w', padx=5)
        
        ttk.Label(trading_frame, text="Win Rate mínimo (0-1):").grid(row=3, column=0, sticky='w', pady=5)
        self.min_winrate_var = tk.StringVar(value="0.55")
        ttk.Entry(trading_frame, textvariable=self.min_winrate_var, width=15).grid(row=3, column=1, sticky='w', padx=5)
        
        ttk.Label(trading_frame, text="Límite pérdida diaria ($):").grid(row=4, column=0, sticky='w', pady=5)
        self.max_loss_var = tk.StringVar(value="50.0")
        ttk.Entry(trading_frame, textvariable=self.max_loss_var, width=15).grid(row=4, column=1, sticky='w', padx=5)
        
        ttk.Label(trading_frame, text="Intervalo polling (s):").grid(row=5, column=0, sticky='w', pady=5)
        self.poll_var = tk.StringVar(value="120")
        ttk.Entry(trading_frame, textvariable=self.poll_var, width=15).grid(row=5, column=1, sticky='w', padx=5)
        
        # Telegram
        telegram_frame = ttk.LabelFrame(scroll_frame, text="Telegram", padding=10)
        telegram_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(telegram_frame, text="Bot Token:").grid(row=0, column=0, sticky='w', pady=5)
        self.token_var = tk.StringVar()
        ttk.Entry(telegram_frame, textvariable=self.token_var, width=50).grid(row=0, column=1, padx=5)
        
        ttk.Label(telegram_frame, text="Chat ID:").grid(row=1, column=0, sticky='w', pady=5)
        self.chat_var = tk.StringVar()
        ttk.Entry(telegram_frame, textvariable=self.chat_var, width=30).grid(row=1, column=1, sticky='w', padx=5)
        ttk.Button(telegram_frame, text="🧪 Probar", command=self.test_telegram).grid(row=1, column=2, padx=5)
        
        # Botón guardar
        ttk.Button(scroll_frame, text="💾 Guardar Configuración", command=self.save_config).pack(pady=20)
        
        # Cargar valores actuales
        self.load_config_values()
    
    def build_history_tab(self):
        """Pestaña de Historial de Trades con filtros"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Historial de Trades")
        
        # Frame de filtros
        filter_frame = ttk.LabelFrame(tab, text="Filtros", padding=10)
        filter_frame.pack(fill='x', padx=10, pady=5)
        
        # Filtro por estado
        ttk.Label(filter_frame, text="Estado:").pack(side='left', padx=5)
        self.filter_status = ttk.Combobox(filter_frame, values=['Todos', 'Ejecutados', 'Omitidos', 'Fallidos'], state='readonly', width=15)
        self.filter_status.set('Ejecutados')  # Por defecto mostrar solo ejecutados
        self.filter_status.pack(side='left', padx=5)
        self.filter_status.bind('<<ComboboxSelected>>', lambda e: self.refresh_trades())
        
        # Filtro por trader
        ttk.Label(filter_frame, text="Trader:").pack(side='left', padx=(20, 5))
        self.filter_trader = ttk.Combobox(filter_frame, values=['Todos'], state='readonly', width=15)
        self.filter_trader.set('Todos')
        self.filter_trader.pack(side='left', padx=5)
        self.filter_trader.bind('<<ComboboxSelected>>', lambda e: self.refresh_trades())
        
        # Botón actualizar
        ttk.Button(filter_frame, text="🔄 Actualizar", command=self.refresh_trades).pack(side='right', padx=5)
        ttk.Button(filter_frame, text="💰 Calcular P&L", command=self.update_open_positions_pnl).pack(side='right', padx=5)
        ttk.Button(filter_frame, text="✅ Cerrar Posición", command=self.close_position_dialog).pack(side='right', padx=5)
        ttk.Button(filter_frame, text="📥 Importar CSV", command=self.import_polymarket_csv).pack(side='right', padx=5)
        ttk.Button(filter_frame, text="📊 Rendimiento", command=self.show_trader_performance).pack(side='right', padx=5)
        ttk.Button(filter_frame, text="🧹 Limpiar", command=self.clear_filters).pack(side='right', padx=5)
        
        # Resumen
        self.history_summary = ttk.Label(tab, text="Total invertido: $0 | P&L total: $0 | Trades: 0", font=('Segoe UI', 11, 'bold'))
        self.history_summary.pack(pady=10)
        
        # Frame para treeview
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview con columnas de P&L
        columns = ('Fecha/Hora', 'Trader', 'Mercado', 'Posición', 'Invertido', 'Precio Entrada', 'Precio Actual', 'P&L $', 'P&L %', 'Estado')
        self.trades_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        widths = [120, 90, 200, 50, 65, 70, 70, 70, 60, 80]
        for col, width in zip(columns, widths):
            self.trades_tree.heading(col, text=col)
            self.trades_tree.column(col, width=width, anchor='center')
        
        # Configurar colores especiales para P&L
        self.trades_tree.tag_configure('profit', foreground='#22c55e', font=('Segoe UI', 9, 'bold'))
        self.trades_tree.tag_configure('loss', foreground='#ef4444', font=('Segoe UI', 9, 'bold'))
        self.trades_tree.tag_configure('neutral', foreground='#94a3b8')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.trades_tree.yview)
        self.trades_tree.configure(yscrollcommand=scrollbar.set)
        
        self.trades_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def clear_filters(self):
        """Limpia los filtros y muestra todo"""
        self.filter_status.set('Todos')
        self.filter_trader.set('Todos')
        self.refresh_trades()
    
    def update_open_positions_pnl(self):
        """Calcula y actualiza el P&L de las posiciones abiertas"""
        try:
            from polymarket_api import PolymarketAPI
            
            self.log("Calculando P&L para posiciones abiertas...")
            
            # Obtener TODOS los trades ejecutados
            all_trades = self.db.get_trades(limit=500)
            
            # Filtrar solo los que tienen status 'executed' (sin importar el P&L)
            # Consideramos 'abiertos' aquellos que no tienen price_at_exit
            open_trades = [t for t in all_trades if t.get('status') == 'executed' and t.get('price_at_exit') is None]
            
            if not open_trades:
                self.log("No hay posiciones abiertas para calcular P&L")
                return
            
            self.log(f"Encontradas {len(open_trades)} posiciones abiertas")
            
            # Inicializar API
            wallet = self.config.get('wallet', {})
            if not wallet.get('private_key'):
                messagebox.showerror("Error", "Configura tu wallet primero")
                return
                
            api = PolymarketAPI(
                private_key=wallet.get('private_key', ''),
                funder_address=wallet.get('funder_address', ''),
                signature_type=wallet.get('signature_type', 1),
                polygon_rpc_url=wallet.get('polygon_rpc_url', None)
            )
            
            updated = 0
            errors = 0
            closed_markets = 0
            
            for trade in open_trades:
                token_id = trade.get('token_id')
                trade_id = trade.get('id')
                
                if not token_id:
                    continue
                
                try:
                    # Obtener precio actual
                    current_price = api.get_token_price(token_id)
                    entry_price = trade.get('price_at_entry', 0)
                    amount = trade.get('amount_usdc', 0)
                    
                    # Si el precio es None, el mercado está cerrado/resuelto
                    if current_price is None:
                        closed_markets += 1
                        self.log(f"  🔒 {trade.get('trader_name', '')}: Mercado cerrado/resuelto - Usa 'Cerrar Posición' o 'Importar CSV'")
                        continue
                    
                    if entry_price > 0 and current_price > 0:
                        # Calcular P&L no realizado
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        pnl = amount * (pnl_pct / 100)
                        
                        # Guardar en DB
                        self.db.update_trade_pnl(trade_id, pnl)
                        updated += 1
                        self.log(f"  {trade.get('trader_name', '')}: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
                
                except Exception as e:
                    errors += 1
                    self.log(f"  Error en {token_id[:10]}...: {str(e)[:50]}")
                    continue
            
            msg = f"P&L actualizado: {updated} posiciones"
            if closed_markets > 0:
                msg += f" | {closed_markets} mercados cerrados (requiere cerrar manual)"
            if errors > 0:
                msg += f" | {errors} errores"
            self.log(msg)
            if closed_markets > 0:
                self.log("💡 Tip: Para mercados cerrados, usa 'Cerrar Posición' o 'Importar CSV' de Polymarket")
            self.refresh_trades()
            
        except Exception as e:
            error_msg = str(e)
            self.log(f"Error actualizando P&L: {error_msg}")
            messagebox.showerror("Error", f"No se pudo actualizar P&L:\n{error_msg}")
    
    def debug_compare_data(self):
        """Función de debug para comparar DB vs CSV"""
        from tkinter import filedialog
        import csv
        
        filename = filedialog.askopenfilename(
            title="DEBUG - Seleccionar CSV de Polymarket",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if not filename:
            return
        
        # Leer CSV limpiando BOM y comillas
        csv_markets = []
        csv_raw_first_lines = []
        
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:  # utf-8-sig quita el BOM automáticamente
                content = f.read()
                f.seek(0)
                
                # Debug: mostrar primeras líneas
                lines = content.split('\n')[:10]
                
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                # Limpiar headers (quitar comillas y espacios)
                clean_headers = [h.strip().strip('"') if h else '' for h in headers]
                csv_raw_first_lines.append(f"Headers limpios: {clean_headers}")
                
                buy_count = 0
                redeem_count = 0
                
                for i, row in enumerate(reader):
                    # Limpiar nombres de columnas y valores
                    clean_row = {}
                    for k, v in row.items():
                        clean_key = k.strip().strip('"') if k else ''
                        clean_value = v.strip().strip('"') if v else ''
                        clean_row[clean_key] = clean_value
                    
                    if i < 3:
                        csv_raw_first_lines.append(f"Row {i}: {clean_row}")
                    
                    market = clean_row.get('marketName', '')
                    action = clean_row.get('action', '')
                    usdc_str = clean_row.get('usdcAmount', '0')
                    
                    try:
                        usdc_val = float(usdc_str) if usdc_str else 0
                    except:
                        usdc_val = 0
                    
                    if action == 'Buy':
                        buy_count += 1
                        if market and usdc_val > 0:
                            csv_markets.append(market)
                    elif action == 'Redeem':
                        redeem_count += 1
                
                csv_raw_first_lines.append(f"\nTotal Buy: {buy_count}, Total Redeem: {redeem_count}")
                        
        except Exception as e:
            self.log(f"Error leyendo CSV: {e}")
            return
        
        # Obtener DB
        db_trades = self.db.get_trades(limit=1000)
        db_markets = [t.get('market_question', '') for t in db_trades if t.get('status') == 'executed']
        
        # Mostrar comparación
        debug_window = tk.Toplevel(self.root)
        debug_window.title("DEBUG - Comparación DB vs CSV")
        debug_window.geometry("900x600")
        debug_window.configure(bg='#1e293b')
        
        text = tk.Text(debug_window, wrap=tk.WORD, font=('Consolas', 10), 
                      bg='#0d0d1a', fg='#00ff88')
        text.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(debug_window, command=text.yview)
        scrollbar.pack(side='right', fill='y')
        text.config(yscrollcommand=scrollbar.set)
        
        text.insert('end', "=== RAW DATA DEL CSV (primeras líneas) ===\n\n")
        for line in lines:
            text.insert('end', f"{line}\n")
        
        text.insert('end', "\n=== DATOS PARSEADOS ===\n\n")
        for info in csv_raw_first_lines:
            text.insert('end', f"{info}\n")
        
        text.insert('end', "\n=== MERCADOS EN BASE DE DATOS ===\n\n")
        for i, m in enumerate(db_markets[:20], 1):
            text.insert('end', f"{i}. {m}\n")
        
        text.insert('end', f"\n... y {len(db_markets) - 20} más\n\n")
        text.insert('end', "=== MERCADOS EN CSV (Buy) ===\n\n")
        for i, m in enumerate(csv_markets[:20], 1):
            text.insert('end', f"{i}. {m}\n")
        
        text.insert('end', f"\n... y {len(csv_markets) - 20} más\n")
        text.config(state='disabled')
    
    def import_polymarket_csv(self):
        """Importa el CSV de exportación de Polymarket y actualiza P&L automáticamente"""
        from tkinter import filedialog
        import csv
        from datetime import datetime
        
        # Abrir diálogo para seleccionar archivo
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo CSV de Polymarket",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            self.log(f"Importando CSV: {filename}")
            
            # Leer CSV limpiando BOM
            trades_from_csv = []
            with open(filename, 'r', encoding='utf-8-sig') as f:  # utf-8-sig quita BOM
                reader = csv.DictReader(f)
                for row in reader:
                    # Limpiar claves y valores
                    clean_row = {}
                    for k, v in row.items():
                        clean_key = k.strip().strip('"') if k else ''
                        clean_value = v.strip().strip('"') if v else ''
                        clean_row[clean_key] = clean_value
                    
                    try:
                        usdc_val = float(clean_row.get('usdcAmount', 0) or 0)
                    except:
                        usdc_val = 0
                    
                    try:
                        tokens_val = float(clean_row.get('tokenAmount', 0) or 0)
                    except:
                        tokens_val = 0
                    
                    try:
                        ts_val = int(clean_row.get('timestamp', 0) or 0)
                    except:
                        ts_val = 0
                    
                    trades_from_csv.append({
                        'market': clean_row.get('marketName', ''),
                        'action': clean_row.get('action', ''),
                        'usdc': usdc_val,
                        'tokens': tokens_val,
                        'token_name': clean_row.get('tokenName', ''),
                        'timestamp': ts_val,
                        'hash': clean_row.get('hash', '')
                    })
            
            self.log(f"Encontradas {len(trades_from_csv)} operaciones en CSV")
            
            # Procesar operaciones
            updated = 0
            matched = 0
            checked = 0
            
            # Obtener todos los trades de la base de datos
            db_trades = self.db.get_trades(limit=1000)
            db_executed = [t for t in db_trades if t.get('status') == 'executed' and not t.get('price_at_exit')]
            
            self.log(f"Trades ejecutados sin cerrar en DB: {len(db_executed)}")
            
            # Primero, mostrar algunos ejemplos para debug
            if db_executed:
                self.log(f"Ejemplo en DB: {db_executed[0].get('market_question', '')[:60]}")
            
            buys_in_csv = [t for t in trades_from_csv if t['action'] == 'Buy' and t['usdc'] > 0]
            if buys_in_csv:
                self.log(f"Ejemplo en CSV: {buys_in_csv[0].get('market', '')[:60]}")
            
            for csv_trade in trades_from_csv:
                # Buscar operaciones Buy (entradas) que coincidan con nuestros trades
                if csv_trade['action'] == 'Buy' and csv_trade['usdc'] > 0:
                    # Buscar en DB un trade con mismo mercado
                    for db_trade in db_executed:
                        db_market = db_trade.get('market_question', '')
                        checked += 1
                        
                        # Coincidencia por nombre de mercado (aproximada)
                        if self._markets_match(db_market, csv_trade['market']):
                            # Coincidencia encontrada
                            matched += 1
                            self.log(f"🎯 Match encontrado: {csv_trade['market'][:50]}")
                            
                            # Buscar si hay un Redeem correspondiente
                            for redeem in trades_from_csv:
                                if (redeem['action'] == 'Redeem' and 
                                    self._markets_match(csv_trade['market'], redeem['market']) and
                                    redeem['timestamp'] > csv_trade['timestamp']):
                                    
                                    # Calcular P&L
                                    exit_usdc = redeem['usdc']
                                    entry_usdc = csv_trade['usdc']
                                    
                                    if exit_usdc > 0:
                                        # Ganó
                                        pnl = exit_usdc - entry_usdc
                                        exit_price = 1.0
                                    else:
                                        # Perdió todo
                                        pnl = -entry_usdc
                                        exit_price = 0.0
                                    
                                    # Actualizar en DB
                                    self.db.update_trade_pnl(
                                        db_trade['id'], 
                                        pnl, 
                                        exit_price
                                    )
                                    updated += 1
                                    self.log(f"✅ {db_trade['trader_name']}: {csv_trade['market'][:40]}... P&L: ${pnl:+.2f}")
                                    break
            
            self.log(f"Total comparaciones: {checked}, Matches: {matched}, Actualizados: {updated}")
            
            messagebox.showinfo(
                "Importación completada",
                f"Operaciones en CSV: {len(trades_from_csv)}\n"
                f"Trades coincididos: {matched}\n"
                f"P&L actualizados: {updated}"
            )
            
            self.refresh_trades()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar CSV:\n{str(e)}")
            self.log(f"Error importando CSV: {e}")
    
    def _markets_match(self, market1, market2):
        """Compara dos nombres de mercado para ver si son el mismo"""
        if not market1 or not market2:
            return False
        
        # Normalizar: minúsculas, quitar espacios extras y caracteres especiales
        m1 = market1.lower().strip()
        m2 = market2.lower().strip()
        
        # Qitar caracteres especiales y normalizar espacios
        import re
        m1_clean = re.sub(r'[^\w\s]', ' ', m1)
        m2_clean = re.sub(r'[^\w\s]', ' ', m2)
        m1_clean = ' '.join(m1_clean.split())  # Normalizar espacios
        m2_clean = ' '.join(m2_clean.split())
        
        # Coincidencia exacta
        if m1_clean == m2_clean:
            return True
        
        # Coincidencia parcial (uno contiene al otro)
        if len(m1_clean) > 15 and len(m2_clean) > 15:
            if m1_clean in m2_clean or m2_clean in m1_clean:
                return True
        
        # Extraer palabras significativas (más de 3 caracteres)
        words1 = set([w for w in m1_clean.split() if len(w) > 3])
        words2 = set([w for w in m2_clean.split() if len(w) > 3])
        
        if not words1 or not words2:
            return False
        
        common = words1.intersection(words2)
        
        # Debug: mostrar qué está comparando
        if len(common) > 0:
            print(f"  Comparando: '{m1_clean[:50]}' vs '{m2_clean[:50]}'")
            print(f"  Palabras comunes: {common}")
        
        # Si comparten al menos 2 palabras significativas (nombres de equipos)
        if len(common) >= 2:
            return True
        
        return False
    
    def close_position_dialog(self):
        """Diálogo simple para cerrar una posición y registrar P&L"""
        selection = self.trades_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona un trade en la tabla para cerrar")
            return
        
        # Obtener el item seleccionado
        item = self.trades_tree.selection()[0]
        values = self.trades_tree.item(item, 'values')
        
        if not values:
            return
        
        # Crear ventana simple
        dialog = tk.Toplevel(self.root)
        dialog.title("Cerrar Posición")
        dialog.geometry("400x350")
        dialog.configure(bg='#1e293b')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Info del trade
        ttk.Label(dialog, text="CERRAR POSICIÓN", font=('Segoe UI', 14, 'bold'), 
                 background='#1e293b', foreground='white').pack(pady=10)
        
        ttk.Label(dialog, text=f"Trader: {values[1]}", background='#1e293b', 
                 foreground='#94a3b8').pack()
        ttk.Label(dialog, text=f"Mercado: {values[2][:40]}...", background='#1e293b', 
                 foreground='#94a3b8').pack()
        ttk.Label(dialog, text=f"Invertido: {values[4]}", background='#1e293b', 
                 foreground='#94a3b8').pack()
        ttk.Label(dialog, text=f"Precio entrada: {values[5]}", background='#1e293b', 
                 foreground='#94a3b8').pack(pady=(0, 10))
        
        # Separador
        ttk.Separator(dialog, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # Resultado
        ttk.Label(dialog, text="¿CÓMO TERMINÓ LA APUESTA?", font=('Segoe UI', 11, 'bold'),
                 background='#1e293b', foreground='white').pack(pady=10)
        
        result_frame = ttk.Frame(dialog)
        result_frame.pack(pady=5)
        
        result_var = tk.StringVar(value="win")
        ttk.Radiobutton(result_frame, text="✅ GANÉ (cobra $1 por share)", variable=result_var, 
                       value="win").pack(anchor='w', pady=2)
        ttk.Radiobutton(result_frame, text="❌ PERDÍ (cobra $0)", variable=result_var, 
                       value="loss").pack(anchor='w', pady=2)
        
        # Nota
        ttk.Label(dialog, text="Nota: En Polymarket, las apuestas ganadoras\npagan $1.00 por cada share.",
                 background='#1e293b', foreground='#64748b', justify='center').pack(pady=10)
        
        def do_close():
            try:
                entry_price_str = values[5].replace('-', '')
                entry_price = float(entry_price_str) if entry_price_str else 0
                amount_str = values[4].replace('$', '').replace(',', '')
                amount = float(amount_str) if amount_str else 0
                
                if result_var.get() == "win":
                    exit_price = 1.0  # Ganó -> $1 por share
                    pnl = amount * ((1.0 - entry_price) / entry_price) if entry_price > 0 else 0
                else:
                    exit_price = 0.0  # Perdió -> $0
                    pnl = -amount  # Pierde todo lo invertido
                
                # Guardar en DB - necesitamos encontrar el trade_id
                # Obtener todos los trades y buscar el que coincida
                all_trades = self.db.get_trades(limit=500)
                for trade in all_trades:
                    if (trade.get('trader_name') == values[1] and 
                        trade.get('market_question', '')[:40] in values[2] and
                        abs(trade.get('price_at_entry', 0) - entry_price) < 0.001):
                        # Encontrado! Actualizar
                        self.db.update_trade_pnl(trade['id'], pnl, exit_price)
                        self.log(f"✅ Posición cerrada: {values[1]} - P&L: ${pnl:+.2f}")
                        break
                
                dialog.destroy()
                self.refresh_trades()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cerrar: {e}")
        
        ttk.Button(dialog, text="💾 Guardar Resultado", command=do_close).pack(pady=15)
    
    def show_trader_performance(self):
        """Muestra ventana con rendimiento por trader"""
        # Crear ventana popup
        perf_window = tk.Toplevel(self.root)
        perf_window.title("Rendimiento por Trader")
        perf_window.geometry("800x500")
        perf_window.configure(bg='#1a1a2e')
        
        # Título
        ttk.Label(perf_window, text="📊 Rendimiento por Trader", 
                 font=('Segoe UI', 16, 'bold'), background='#1a1a2e', foreground='white').pack(pady=10)
        
        # Treeview para estadísticas
        columns = ('Trader', 'Trades', 'Ganadas', 'Perdidas', 'Win Rate', 'Invertido', 'P&L Total', 'ROI %')
        tree = ttk.Treeview(perf_window, columns=columns, show='headings', height=12)
        
        widths = [120, 60, 60, 60, 80, 90, 100, 80]
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(perf_window, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y', pady=10)
        
        # Obtener datos
        try:
            performance = self.db.get_trader_performance()
            
            total_invested_all = 0
            total_pnl_all = 0
            
            for perf in performance:
                trader = perf.get('trader_name', '')
                total = perf.get('total_trades', 0)
                wins = perf.get('wins', 0)
                losses = perf.get('losses', 0)
                win_rate = perf.get('win_rate', 0) or 0
                invested = perf.get('total_invested', 0) or 0
                pnl = perf.get('total_pnl', 0) or 0
                roi = perf.get('avg_pnl_pct', 0) or 0
                
                total_invested_all += invested
                total_pnl_all += pnl
                
                # Color según P&L
                tag = 'profit' if pnl > 0 else 'loss' if pnl < 0 else 'neutral'
                
                tree.insert('', 'end', values=(
                    trader,
                    total,
                    wins,
                    losses,
                    f"{win_rate:.1f}%",
                    f"${invested:.2f}",
                    f"${pnl:+.2f}",
                    f"{roi:+.1f}%"
                ), tags=(tag,))
            
            # Configurar colores
            tree.tag_configure('profit', foreground='#22c55e', font=('Segoe UI', 9, 'bold'))
            tree.tag_configure('loss', foreground='#ef4444', font=('Segoe UI', 9, 'bold'))
            tree.tag_configure('neutral', foreground='#94a3b8')
            
            # Resumen total
            ttk.Label(perf_window, 
                     text=f"TOTAL: Invertido ${total_invested_all:.2f} | P&L ${total_pnl_all:+.2f} | ROI {(total_pnl_all/total_invested_all*100) if total_invested_all > 0 else 0:.1f}%",
                     font=('Segoe UI', 11, 'bold'), background='#1a1a2e', 
                     foreground='#22c55e' if total_pnl_all >= 0 else '#ef4444').pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar estadísticas: {e}", parent=perf_window)
    
    def toggle_pk_visibility(self):
        """Muestra/oculta la private key"""
        if self.pk_entry.cget('show') == '*':
            self.pk_entry.config(show='')
        else:
            self.pk_entry.config(show='*')
    
    def load_config(self):
        """Carga la configuración del archivo"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Error cargando config: {e}")
        
        # Config por defecto
        return {
            "wallet": {"private_key": "", "funder_address": "", "signature_type": 1},
            "trading": {"mode": "fixed", "fixed_amount": 5.0, "portfolio_pct": 2.0, 
                       "min_win_rate": 0.55, "max_daily_loss": 50.0, "active_hours_start": 0, "active_hours_end": 24},
            "telegram": {"bot_token": "", "chat_id": ""},
            "tracked_wallets": [],
            "poll_interval": 120
        }
    
    def load_config_values(self):
        """Carga los valores en la UI"""
        w = self.config.get('wallet', {})
        self.pk_var.set(w.get('private_key', ''))
        self.funder_var.set(w.get('funder_address', ''))
        self.sig_type_var.set(w.get('signature_type', 1))
        self.rpc_var.set(w.get('polygon_rpc_url', ''))
        
        t = self.config.get('trading', {})
        self.mode_var.set(t.get('mode', 'fixed'))
        self.fixed_var.set(str(t.get('fixed_amount', 5.0)))
        self.pct_var.set(str(t.get('portfolio_pct', 2.0)))
        self.min_winrate_var.set(str(t.get('min_win_rate', 0.55)))
        self.max_loss_var.set(str(t.get('max_daily_loss', 50.0)))
        self.poll_var.set(str(self.config.get('poll_interval', 120)))
        
        tg = self.config.get('telegram', {})
        self.token_var.set(tg.get('bot_token', ''))
        self.chat_var.set(tg.get('chat_id', ''))
    
    def save_config(self):
        """Guarda la configuración"""
        try:
            self.config['wallet'] = {
                'private_key': self.pk_var.get(),
                'funder_address': self.funder_var.get(),
                'signature_type': self.sig_type_var.get(),
                'polygon_rpc_url': self.rpc_var.get()
            }
            
            self.config['trading'] = {
                'mode': self.mode_var.get(),
                'fixed_amount': float(self.fixed_var.get() or 5.0),
                'portfolio_pct': float(self.pct_var.get() or 2.0),
                'min_win_rate': float(self.min_winrate_var.get() or 0.55),
                'max_daily_loss': float(self.max_loss_var.get() or 50.0),
                'active_hours_start': 0,
                'active_hours_end': 24
            }
            
            self.config['telegram'] = {
                'bot_token': self.token_var.get(),
                'chat_id': self.chat_var.get()
            }
            
            self.config['poll_interval'] = int(self.poll_var.get() or 120)
            
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            messagebox.showinfo("Éxito", "Configuración guardada correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando config: {e}")
    
    def add_trader(self):
        """Añade un trader a la lista"""
        address = self.trader_address_var.get().strip()
        name = self.trader_name_var.get().strip()
        
        if not address.startswith('0x') or len(address) < 10:
            messagebox.showerror("Error", "La dirección debe empezar por 0x")
            return
        
        try:
            win_rate = float(self.trader_winrate_var.get() or 0.5)
        except:
            win_rate = 0.5
        
        trader = {
            'address': address,
            'name': name or address[:8],
            'win_rate': win_rate,
            'active': True
        }
        
        if 'tracked_wallets' not in self.config:
            self.config['tracked_wallets'] = []
        
        # Verificar duplicados
        for t in self.config['tracked_wallets']:
            if t.get('address') == address:
                messagebox.showwarning("Duplicado", "Este trader ya está en la lista")
                return
        
        self.config['tracked_wallets'].append(trader)
        self.save_config()
        
        # Limpiar campos
        self.trader_address_var.set('')
        self.trader_name_var.set('')
        
        self.refresh_traders_list()
        messagebox.showinfo("Éxito", "Trader añadido correctamente")
    
    def remove_trader(self):
        """Elimina el trader seleccionado"""
        selection = self.traders_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona un trader para eliminar")
            return
        
        item = self.traders_tree.item(selection[0])
        address = item['values'][1]
        
        self.config['tracked_wallets'] = [
            t for t in self.config.get('tracked_wallets', [])
            if t.get('address') != address
        ]
        
        self.save_config()
        self.refresh_traders_list()
    
    def toggle_trader(self):
        """Activa/desactiva el trader seleccionado"""
        selection = self.traders_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Selecciona un trader para activar/desactivar")
            return
        
        item = self.traders_tree.item(selection[0])
        address = item['values'][1]
        
        # Buscar el trader y toggle
        for trader in self.config.get('tracked_wallets', []):
            if trader.get('address') == address:
                current_status = trader.get('active', True)
                trader['active'] = not current_status
                new_status = "ON" if trader['active'] else "OFF"
                self.log(f"Trader {trader.get('name', address[:8])} {new_status}")
                break
        
        self.save_config()
        self.refresh_traders_list()
    
    def refresh_traders_list(self):
        """Actualiza la lista de traders"""
        for item in self.traders_tree.get_children():
            self.traders_tree.delete(item)
        
        # Configurar colores para estados
        self.traders_tree.tag_configure('active', foreground='#22c55e')
        self.traders_tree.tag_configure('inactive', foreground='#94a3b8')
        
        for trader in self.config.get('tracked_wallets', []):
            is_active = trader.get('active', True)
            status_text = "🟢 ON" if is_active else "⚪ OFF"
            tag = 'active' if is_active else 'inactive'
            
            self.traders_tree.insert('', 'end', values=(
                trader.get('name', ''),
                trader.get('address', ''),
                f"{trader.get('win_rate', 0):.0%}",
                status_text
            ), tags=(tag,))
    
    def test_telegram(self):
        """Envía mensaje de prueba"""
        temp_config = {
            'telegram': {
                'bot_token': self.token_var.get(),
                'chat_id': self.chat_var.get()
            }
        }
        notify_test(temp_config)
        messagebox.showinfo("Test", "Mensaje enviado. Revisa Telegram.")
    
    def start_bot(self):
        """Inicia el bot"""
        # Validar
        if not self.config.get('wallet', {}).get('private_key'):
            messagebox.showerror("Error", "Configura tu Private Key primero")
            return
        
        if not self.config.get('wallet', {}).get('funder_address'):
            messagebox.showerror("Error", "Configura tu Funder Address primero")
            return
        
        if not self.config.get('tracked_wallets'):
            messagebox.showwarning("Advertencia", "No hay traders configurados para seguir")
        
        # Iniciar
        self.trader = CopyTrader(self.config, self.db, self.log)
        self.trader_thread = threading.Thread(target=self.trader.run_loop, daemon=True)
        self.trader_thread.start()
        
        self.update_status(True)
        
        # Obtener balance
        threading.Thread(target=self.show_balance, daemon=True).start()
    
    def stop_bot(self):
        """Detiene el bot"""
        if self.trader:
            self.trader.stop()
        self.update_status(False)
    
    def update_status(self, running):
        """Actualiza el indicador de estado"""
        if running:
            self.status_label.config(text="🟢 ACTIVO", foreground='#22c55e')
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
        else:
            self.status_label.config(text="⚫ DETENIDO", foreground='#ff4444')
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
    
    def show_balance(self):
        """Muestra el balance"""
        try:
            wallet = self.config.get('wallet', {})
            api = CopyTrader(self.config, self.db, lambda x: None).api
            balance = api.get_balance()
            self.root.after(0, lambda: self.balance_label.config(text=f"Balance USDC: ${balance:.2f}"))
        except Exception as e:
            self.root.after(0, lambda: self.balance_label.config(text="Balance USDC: Error"))
    
    def log(self, msg):
        """Añade mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state='normal')
        self.log_text.insert('end', f"[{timestamp}] {msg}\n")
        self.log_text.see('end')
        self.log_text.configure(state='disabled')
    
    def refresh_stats(self):
        """Actualiza estadísticas"""
        try:
            daily_loss = self.db.get_daily_loss_today()
            total_pnl = self.db.get_total_pnl()
            
            self.daily_loss_label.config(text=f"Pérdida hoy: ${daily_loss:.2f}")
            self.total_pnl_label.config(text=f"P&L total: ${total_pnl:.2f}")
        except:
            pass
        
        self.root.after(60000, self.refresh_stats)
    
    def refresh_trades(self):
        """Actualiza el historial de trades con filtros"""
        try:
            # Obtener filtros actuales
            status_filter = self.filter_status.get()
            trader_filter = self.filter_trader.get()
            
            # Mapear filtro de estado
            status_map = {
                'Todos': None,
                'Ejecutados': 'executed',
                'Omitidos': 'skipped',
                'Fallidos': 'failed'
            }
            target_status = status_map.get(status_filter)
            
            # Obtener trades
            trades = self.db.get_trades(limit=200)
            
            # Actualizar lista de traders en el filtro
            traders_list = ['Todos'] + list(set(t.get('trader_name', '') for t in trades if t.get('trader_name')))
            if sorted(self.filter_trader['values']) != sorted(traders_list):
                current = self.filter_trader.get()
                self.filter_trader['values'] = traders_list
                self.filter_trader.set(current if current in traders_list else 'Todos')
            
            # Limpiar treeview
            for item in self.trades_tree.get_children():
                self.trades_tree.delete(item)
            
            # Filtrar trades
            filtered_trades = []
            for trade in trades:
                status = trade.get('status', '')
                
                # Filtro por estado
                if target_status and status != target_status:
                    continue
                
                # Filtro por trader
                if trader_filter != 'Todos' and trade.get('trader_name') != trader_filter:
                    continue
                
                filtered_trades.append(trade)
            
            # Calcular estadísticas (solo de trades ejecutados visibles)
            total_invested = 0
            total_pnl = 0
            executed_count = 0
            
            for trade in filtered_trades:
                if trade.get('status') == 'executed':
                    total_invested += trade.get('amount_usdc', 0)
                    total_pnl += trade.get('pnl', 0)
                    executed_count += 1
            
            # Mostrar trades (ya vienen ordenados por fecha descendente de la DB)
            for trade in filtered_trades:
                status = trade.get('status', '')
                amount = trade.get('amount_usdc', 0)
                entry_price = trade.get('price_at_entry', 0) or 0
                exit_price = trade.get('price_at_exit')
                pnl = trade.get('pnl', 0) or 0
                
                # Calcular P&L
                if status == 'executed':
                    # Determinar si está cerrado o abierto
                    is_closed = exit_price is not None and exit_price > 0
                    
                    if is_closed:
                        # Trade cerrado - usar P&L guardado
                        current_price = exit_price
                        pnl_pct = (pnl / amount * 100) if amount > 0 else 0
                        status_display = 'CERRADO'
                    else:
                        # Trade abierto
                        current_price = entry_price  # No tenemos precio actual
                        pnl_pct = (pnl / amount * 100) if amount > 0 else 0
                        status_display = 'ABIERTO'
                    
                    # Determinar tag de color para P&L
                    pnl_tag = 'neutral'
                    if pnl > 0:
                        pnl_tag = 'profit'
                    elif pnl < 0:
                        pnl_tag = 'loss'
                    
                    # Formatear valores
                    if pnl != 0:
                        pnl_str = f"${pnl:+.2f}"
                        pnl_pct_str = f"{pnl_pct:+.1f}%"
                    else:
                        pnl_str = "Sin calcular"
                        pnl_pct_str = "-"
                    
                else:
                    current_price = "-"
                    pnl_str = "-"
                    pnl_pct_str = "-"
                    pnl_tag = 'neutral'
                    status_display = {
                        'skipped': 'OMITIDO',
                        'failed': 'FALLIDO'
                    }.get(status, status.upper())
                    
                # Ajustar status_display para ejecutados según si está cerrado o no
                if status == 'executed':
                    is_closed = exit_price is not None
                    if is_closed:
                        if pnl > 0:
                            status_display = '✅ GANADO'
                        elif pnl < 0:
                            status_display = '❌ PERDIDO'
                        else:
                            status_display = '➖ NEUTRO'
                    else:
                        status_display = '⏳ ABIERTO'
                
                # Colores según estado
                tags = (pnl_tag,)
                
                # Formatear timestamp
                ts = trade.get('timestamp', '')
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts)
                        ts = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                self.trades_tree.insert('', 'end', values=(
                    ts,
                    trade.get('trader_name', ''),
                    trade.get('market_question', '')[:45] + '...' if len(trade.get('market_question', '')) > 45 else trade.get('market_question', ''),
                    trade.get('outcome', ''),
                    f"${amount:.2f}",
                    f"{entry_price:.3f}" if entry_price else '-',
                    f"{current_price:.3f}" if isinstance(current_price, (int, float)) else current_price,
                    pnl_str,
                    pnl_pct_str,
                    status_display
                ), tags=tags)
            
            # Configurar colores básicos
            self.trades_tree.tag_configure('executed', foreground='#22c55e')
            self.trades_tree.tag_configure('failed', foreground='#ef4444')
            self.trades_tree.tag_configure('skipped', foreground='#888')
            
            # Actualizar resumen
            filter_text = f" | Filtro: {status_filter}" if status_filter != 'Todos' else ''
            self.history_summary.config(
                text=f"Mostrando: {len(filtered_trades)} trades | Total invertido: ${total_invested:.2f} | P&L: ${total_pnl:.2f}{filter_text}"
            )
        except Exception as e:
            print(f"Error actualizando trades: {e}")
        
        # Programar siguiente actualización (solo si no hay filtros activos)
        if self.filter_status.get() == 'Todos' and self.filter_trader.get() == 'Todos':
            self.root.after(30000, self.refresh_trades)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
