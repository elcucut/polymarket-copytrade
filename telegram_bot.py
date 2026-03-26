import requests


def send_message(bot_token, chat_id, text):
    """Envía un mensaje a Telegram"""
    if not bot_token or not chat_id:
        return
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        response.raise_for_status()
    except Exception as e:
        # Silenciar errores para no interrumpir el bot
        print(f"Error enviando mensaje Telegram: {e}")


def notify_trade_executed(config, trade):
    """Notifica que se ejecutó un trade"""
    market = trade.get('market_question', 'Desconocido')
    if len(market) > 80:
        market = market[:80] + "..."
    
    msg = (
        f"✅ <b>Trade ejecutado</b>\n\n"
        f"👤 Copiando: <b>{trade.get('trader_name', 'Desconocido')}</b>\n"
        f"📊 Mercado: {market}\n"
        f"✅ Posición: <b>{trade.get('outcome', '?')}</b>\n"
        f"💰 Invertido: <b>${trade.get('amount_usdc', 0):.2f}</b>\n"
        f"📈 Precio entrada: {trade.get('price_at_entry', 0):.3f}"
    )
    
    send_message(
        config.get('telegram', {}).get('bot_token'),
        config.get('telegram', {}).get('chat_id'),
        msg
    )


def notify_trade_skipped(config, reason, market):
    """Notifica que se omitió un trade"""
    if len(market) > 60:
        market = market[:60] + "..."
    
    msg = (
        f"⏭️ <b>Trade omitido</b>\n\n"
        f"📊 {market}\n"
        f"❌ Motivo: {reason}"
    )
    
    send_message(
        config.get('telegram', {}).get('bot_token'),
        config.get('telegram', {}).get('chat_id'),
        msg
    )


def notify_daily_loss_limit(config, loss):
    """Notifica que se alcanzó el límite de pérdida diaria"""
    msg = (
        f"🛑 <b>Límite de pérdida diaria alcanzado</b>\n\n"
        f"Pérdida acumulada hoy: ${loss:.2f}\n"
        f"Bot pausado hasta mañana."
    )
    
    send_message(
        config.get('telegram', {}).get('bot_token'),
        config.get('telegram', {}).get('chat_id'),
        msg
    )


def notify_error(config, error):
    """Notifica un error en el bot"""
    msg = f"⚠️ <b>Error en el bot:</b>\n\n<code>{error}</code>"
    
    send_message(
        config.get('telegram', {}).get('bot_token'),
        config.get('telegram', {}).get('chat_id'),
        msg
    )


def notify_test(config):
    """Envía mensaje de prueba"""
    msg = "🧪 <b>Test de conexión exitoso</b>\n\n¡Las notificaciones de Telegram están configuradas correctamente!"
    
    send_message(
        config.get('telegram', {}).get('bot_token'),
        config.get('telegram', {}).get('chat_id'),
        msg
    )
