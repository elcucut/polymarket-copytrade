import time
from datetime import datetime
from database import Database
from polymarket_api import PolymarketAPI
from telegram_bot import (
    notify_trade_executed, 
    notify_trade_skipped, 
    notify_daily_loss_limit, 
    notify_error
)


class CopyTrader:
    """Lógica principal de copy trading"""
    
    def __init__(self, config, db, log_callback=None):
        """
        Inicializa el copy trader
        
        Args:
            config: Diccionario de configuración
            db: Instancia de Database
            log_callback: Función para logging en UI
        """
        self.config = config
        self.db = db
        self.log = log_callback or print
        
        # Inicializar API
        wallet_config = config.get('wallet', {})
        self.api = PolymarketAPI(
            private_key=wallet_config.get('private_key', ''),
            funder_address=wallet_config.get('funder_address', ''),
            signature_type=wallet_config.get('signature_type', 1),
            polygon_rpc_url=wallet_config.get('polygon_rpc_url', None)
        )
        
        self.running = False
        self._paused_for_daily_limit = False
    
    def check_traders(self):
        """Verifica los traders seguidos y busca nuevas posiciones"""
        tracked_wallets = self.config.get('tracked_wallets', [])
        
        if not tracked_wallets:
            self.log("No hay traders configurados para seguir")
            return
        
        for wallet in tracked_wallets:
            address = wallet.get('address', '')
            if not address:
                continue
            
            try:
                self.log(f"Verificando {wallet.get('name', address[:8])}...")
                
                # 1. Obtener posiciones actuales
                positions = self.api.get_trader_positions(address)
                
                # 2. Obtener snapshot anterior
                previous_positions = self.db.get_snapshot(address)
                
                # 3. PROTECCIÓN PRIMERA EJECUCIÓN: Si no hay snapshot previo, 
                # guardamos snapshot AHORA y NO procesamos nada
                if not previous_positions:
                    self.log(f"📸 PRIMERA EJECUCIÓN para {wallet.get('name', address[:8])} - Solo guardando snapshot, NO copiando")
                    self.db.save_snapshot(address, positions)
                    continue  # Saltar al siguiente trader, no procesar nada
                
                # 4. Calcular posiciones nuevas (solo si ya teníamos snapshot)
                previous_token_ids = {p.get('token_id') for p in previous_positions}
                new_positions = []
                for pos in positions:
                    token_id = pos.get('token_id') or pos.get('asset')
                    if token_id and token_id not in previous_token_ids:
                        new_positions.append(pos)
                
                # 5. Guardar snapshot actualizado ANTES de procesar
                # (así si hay error, ya tenemos guardado el estado actual)
                self.db.save_snapshot(address, positions)
                
                # 6. Procesar cada posición nueva
                for position in new_positions:
                    self.process_new_position(wallet, position)
                
                if new_positions:
                    self.log(f"  → {len(new_positions)} posición(es) nueva(s) detectada(s)")
                
            except Exception as e:
                self.log(f"Error verificando {address[:8]}: {e}")
                notify_error(self.config, f"Error con trader {address[:8]}: {e}")
    
    def process_new_position(self, wallet, position):
        """
        Procesa una nueva posición detectada
        
        Args:
            wallet: Configuración del wallet seguido
            position: Datos de la posición
        """
        trading_config = self.config.get('trading', {})
        market = position.get('title', position.get('market', 'Desconocido'))
        
        # CHECK 1 — Win rate mínimo
        win_rate = wallet.get('win_rate', 1.0)
        min_win_rate = trading_config.get('min_win_rate', 0.55)
        if win_rate < min_win_rate:
            reason = f"Win rate del trader ({win_rate:.0%}) por debajo del mínimo ({min_win_rate:.0%})"
            self._skip_trade(reason, market, wallet, position)
            return
        
        # CHECK 2 — Límite de pérdida diaria
        daily_loss = self.db.get_daily_loss_today()
        max_daily_loss = trading_config.get('max_daily_loss', 50.0)
        if daily_loss >= max_daily_loss:
            if not self._paused_for_daily_limit:
                notify_daily_loss_limit(self.config, daily_loss)
                self._paused_for_daily_limit = True
            reason = f"Límite de pérdida diaria alcanzado (${daily_loss:.2f})"
            self._skip_trade(reason, market, wallet, position)
            return
        
        # CHECK 3 — Horario activo
        now = datetime.now()
        hour = now.hour
        start_hour = trading_config.get('active_hours_start', 0)
        end_hour = trading_config.get('active_hours_end', 24)
        
        if hour < start_hour or hour >= end_hour:
            reason = f"Fuera del horario activo ({start_hour}:00 - {end_hour}:00)"
            self._skip_trade(reason, market, wallet, position)
            return
        
        # CHECK 4 — Mercado aún activo
        current_value = position.get('currentValue', 0)
        if current_value <= 0:
            reason = "Mercado no tiene valor actual (posiblemente cerrado)"
            self._skip_trade(reason, market, wallet, position)
            return
        
        # Calcular cantidad a invertir
        mode = trading_config.get('mode', 'fixed')

        if mode == 'fixed':
            amount = trading_config.get('fixed_amount', 5.0)
        elif mode == 'portfolio_pct':
            try:
                balance = self.api.get_balance()
                pct = trading_config.get('portfolio_pct', 2.0)
                amount = balance * pct / 100
            except Exception as e:
                self.log(f"Error obteniendo balance, usando cantidad fija: {e}")
                amount = trading_config.get('fixed_amount', 5.0)
        elif mode == 'copy_trader_pct':
            try:
                # Obtener el valor de la nueva posición del trader
                new_position_value = position.get('currentValue', 0) or position.get('size', 0)

                # Obtener el portfolio total del trader (posiciones + cash on-chain)
                trader_address = wallet.get('address', '')
                portfolio_data = self.api.get_trader_portfolio_value(trader_address)
                trader_total_value = portfolio_data['total_value']
                trader_positions = portfolio_data['positions_value']
                trader_cash = portfolio_data['cash_balance']

                self.log(f"  📊 Trader: Posiciones=${trader_positions:.2f} | Cash=${trader_cash:.2f} | Total=${trader_total_value:.2f}")
                self.log(f"  📊 Nueva posición: ${new_position_value:.2f}")

                # Verificar que el portfolio no sea 0 para evitar división por cero
                if trader_total_value <= 0:
                    self.log(f"  ⚠️ Portfolio del trader es 0, usando modo fixed como fallback")
                    amount = trading_config.get('fixed_amount', 5.0)
                else:
                    # Calcular el porcentaje que representa esta posición en el TOTAL del trader
                    # (posiciones + cash), no solo en las posiciones abiertas
                    trader_pct = new_position_value / trader_total_value

                    # Obtener nuestro balance
                    our_balance = self.api.get_balance()

                    # Calcular nuestra inversión proporcional
                    amount = our_balance * trader_pct

                    # PROTECCIÓN: Si el trader invierte más del 100% (apalancamiento/extremo),
                    # o si nosotros no tenemos suficiente, ajustar al máximo posible
                    max_safe_amount = our_balance * 0.95  # Dejar 5% para fees/gas

                    if trader_pct > 1.0:
                        self.log(f"  ⚠️ Trader invierte {trader_pct:.2%} (>100%, posible apalancamiento)")
                        self.log(f"  ⚠️ Ajustando a máximo seguro: ${max_safe_amount:.2f} (95% de balance)")
                        amount = max_safe_amount
                    elif amount > max_safe_amount:
                        self.log(f"  ⚠️ Cantidad calculada (${amount:.2f}) excede balance disponible")
                        self.log(f"  ⚠️ Ajustando a máximo seguro: ${max_safe_amount:.2f} (95% de balance)")
                        amount = max_safe_amount
                    else:
                        self.log(f"  📈 Trader invierte {trader_pct:.2%} de su capital total")
                        self.log(f"  📈 Nosotros invertimos: ${amount:.2f} ({trader_pct:.2%} de ${our_balance:.2f})")

            except Exception as e:
                self.log(f"Error en modo copy_trader_pct, usando cantidad fija: {e}")
                amount = trading_config.get('fixed_amount', 5.0)
        else:
            amount = trading_config.get('fixed_amount', 5.0)
        
        # CHECK 5 — Cantidad mínima
        if amount < 1.0:
            reason = f"Cantidad calculada (${amount:.2f}) por debajo del mínimo ($1.00)"
            self._skip_trade(reason, market, wallet, position)
            return
        
        # Ejecutar orden
        token_id = position.get('token_id') or position.get('asset', '')
        
        if not token_id:
            reason = "No se pudo identificar el token_id"
            self._skip_trade(reason, market, wallet, position)
            return
        
        try:
            # Obtener precio actual
            price = self.api.get_token_price(token_id)
            
            self.log(f"Ejecutando orden: {market[:50]}... por ${amount:.2f}")
            
            # Ejecutar
            success, resp = self.api.execute_order(token_id, amount)
            
            # Guardar en DB
            trade = {
                'timestamp': datetime.now().isoformat(),
                'trader_address': wallet.get('address', ''),
                'trader_name': wallet.get('name', wallet.get('address', '')[:8]),
                'market_question': market,
                'outcome': position.get('outcome', '?'),
                'token_id': token_id,
                'amount_usdc': amount,
                'price_at_entry': price,
                'status': 'executed' if success else 'failed',
                'skip_reason': '' if success else str(resp)
            }
            
            self.db.save_trade(trade)
            
            if success:
                notify_trade_executed(self.config, trade)
                self.log(f"  ✅ Trade ejecutado exitosamente")
            else:
                error_msg = str(resp) if resp else "Error desconocido"
                self.log(f"  ❌ Falló la ejecución: {error_msg}")
                
        except Exception as e:
            error_msg = str(e)
            self.log(f"  ❌ Error ejecutando orden: {error_msg}")
            
            # Guardar como fallido
            trade = {
                'timestamp': datetime.now().isoformat(),
                'trader_address': wallet.get('address', ''),
                'trader_name': wallet.get('name', wallet.get('address', '')[:8]),
                'market_question': market,
                'outcome': position.get('outcome', '?'),
                'token_id': token_id,
                'amount_usdc': amount,
                'price_at_entry': 0,
                'status': 'failed',
                'skip_reason': error_msg
            }
            self.db.save_trade(trade)
    
    def _skip_trade(self, reason, market, wallet, position):
        """Registra un trade omitido"""
        self.log(f"  ⏭️ Omitido: {reason}")
        
        # Guardar en DB como skipped
        trade = {
            'timestamp': datetime.now().isoformat(),
            'trader_address': wallet.get('address', ''),
            'trader_name': wallet.get('name', wallet.get('address', '')[:8]),
            'market_question': market,
            'outcome': position.get('outcome', '?'),
            'token_id': position.get('token_id') or position.get('asset', ''),
            'amount_usdc': 0,
            'price_at_entry': 0,
            'status': 'skipped',
            'skip_reason': reason
        }
        self.db.save_trade(trade)
        
        # Notificar - COMENTADO para reducir spam, solo log local
        # notify_trade_skipped(self.config, reason, market)
    
    def run_loop(self):
        """Bucle principal del bot"""
        self.running = True
        self._paused_for_daily_limit = False
        
        interval = self.config.get('poll_interval', 120)
        
        self.log("=" * 50)
        self.log("🚀 Bot de Copy Trading iniciado")
        self.log(f"⏱️ Intervalo de verificación: {interval}s")
        self.log("=" * 50)
        
        while self.running:
            try:
                self.check_traders()
                
                if self.running:
                    self.log(f"💤 Próxima verificación en {interval}s")
                    
                    # Dormir en intervalos pequeños para poder detener rápido
                    slept = 0
                    while slept < interval and self.running:
                        time.sleep(1)
                        slept += 1
                        
            except Exception as e:
                error_msg = str(e)
                self.log(f"❌ Error en el bucle principal: {error_msg}")
                notify_error(self.config, f"Error en bucle principal: {error_msg}")
                time.sleep(30)
        
        self.log("🛑 Bot detenido")
    
    def stop(self):
        """Detiene el bot"""
        self.running = False
        self.log("Solicitando detención del bot...")
