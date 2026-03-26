# Polymarket Copy Trader

Bot de copy trading para Polymarket con interfaz gráfica. Copia automáticamente las operaciones de traders exitosos.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Características

- **Copy Trading Automático**: Detecta y copia nuevas posiciones de traders configurados
- **3 Modos de Inversión**:
  - Cantidad fija ($)
  - Porcentaje de tu portfolio (%)
  - **Copiar % del trader**: Replica el mismo % de capital que invierte el trader
- **Protecciones**:
  - Win rate mínimo por trader
  - Límite de pérdida diaria
  - Horario de trading configurable
- **Notificaciones Telegram**: Recibe alertas de trades ejecutados, omitidos o errores
- **Seguimiento de P&L**: Calcula ganancias/pérdidas en tiempo real
- **Base de datos SQLite**: Guarda historial de trades y snapshots de posiciones

## Requisitos

- Python 3.8+
- Cuenta en Polymarket con fondos (USDC en Polygon)
- (Opcional) Bot de Telegram para notificaciones
- (Opcional) API Key de Alchemy/Infura para modo "Copiar % del trader"

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/elcucutrecords/polymarket-copytrade.git
cd polymarket-copytrade

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración

1. **Copiar el archivo de configuración de ejemplo**:
```bash
cp config.example.json config.json
```

2. **Editar `config.json`** con tus datos:

### Wallet (Obligatorio)

#### Paso 1: Crear cuenta en Polymarket (modo Email/Magic)

El bot funciona mejor con cuentas creadas mediante **Email/Magic** (no MetaMask):

1. Ve a [Polymarket.com](https://polymarket.com)
2. Click en **"Sign Up"** o **"Connect"**
3. Selecciona **"Continue with Email"** (no uses MetaMask para el bot)
4. Ingresa tu email y verifica con el código
5. Configura tu perfil

#### Paso 2: Obtener tu Funder Address

1. Inicia sesión en [Polymarket](https://polymarket.com)
2. Ve a tu **perfil** (click en tu foto/nombre arriba a la derecha)
3. Al lado de tu nombre de usuario, verás un botón **"Copy address"**
4. Click y pégalo en el campo `funder_address` de tu configuración

La dirección tendrá formato: `0x...`

#### Paso 3: Exportar tu Private Key

1. Ve a: https://polymarket.com/settings?tab=export-private-key
2. Sigue los pasos de verificación de seguridad que te pide Polymarket
3. Una vez verificado, se te mostrará tu **Private Key**
4. Copia la clave completa (empieza con `0x`)
5. Pégala en el campo `private_key` de tu configuración

⚠️ **Importante**: Nunca compartas tu private key con nadie. Guárdala de forma segura.

#### Paso 4: Configurar en el bot

Edita tu `config.json` con los datos obtenidos:

```json
"wallet": {
  "private_key": "0xTU_CLAVE_PRIVADA_AQUI",
  "funder_address": "0xTU_DIRECCION_AQUI",
  "signature_type": 1,
  "polygon_rpc_url": "https://polygon-mainnet.g.alchemy.com/v2/TU_API_KEY"
}
```

**Tipos de firma**:
- `0` = EOA/MetaMask (no recomendado para este bot)
- `1` = Email/Magic ✅ **Recomendado y más estable**
- `2` = Browser

**Polygon RPC** (solo requerido para modo "Copiar % trader"):
- Ve a [Alchemy](https://www.alchemy.com/) y crea una cuenta gratuita
- Crea una nueva app en la red **Polygon Mainnet**
- Copia la URL del HTTP API
- URL típica: `https://polygon-mainnet.g.alchemy.com/v2/TU_API_KEY`

### Modo de Trading
```json
"trading": {
  "mode": "copy_trader_pct",  // Opciones: "fixed", "portfolio_pct", "copy_trader_pct"
  "fixed_amount": 5.0,        // Cantidad fija en USD
  "portfolio_pct": 2.0,       // % de tu portfolio
  "min_win_rate": 0.55,       // Win rate mínimo del trader
  "max_daily_loss": 50.0      // Límite de pérdida diaria
}
```

### Traders a seguir
```json
"tracked_wallets": [
  {
    "address": "0x...",
    "name": "NombreDelTrader",
    "win_rate": 0.55
  }
]
```

Puedes encontrar traders en [Polymarket Leaderboard](https://polymarket.com/leaderboard)

### Telegram (Opcional)
```json
"telegram": {
  "bot_token": "TOKEN_DE_BOTFATHER",
  "chat_id": "TU_CHAT_ID"
}
```

## Uso

```bash
python main.py
```

Se abrirá una interfaz gráfica con 4 pestañas:
- **Panel de Control**: Iniciar/detener bot y ver estado
- **Traders Seguidos**: Añadir/eliminar traders
- **Configuración**: Editar todos los parámetros
- **Historial**: Ver trades ejecutados y calcular P&L

## Cómo funciona "Copiar % del trader"

Este modo avanzado replica el riesgo que asume el trader:

1. Calcula el capital total del trader (posiciones abiertas + cash USDC)
2. Detecta qué % de su capital invierte en la nueva posición
3. Aplica ese mismo % a tu balance

**Ejemplo**:
- Trader tiene $5,000 en posiciones + $5,000 cash = $10,000 total
- Abre posición de $1,000 → 10% de su capital
- Tú tienes $1,000 → inviertes $100 (10%)

### Protecciones de seguridad

El bot incluye protecciones automáticas:

1. **Trader invierte >100%** (apalancamiento/extremo):
   - Se ajusta automáticamente al 95% de tu balance disponible
   - Se registra en logs: `"Trader invierte 120%, ajustando a máximo seguro"`

2. **Cantidad calculada > balance disponible**:
   - Se ajusta al 95% de tu balance (dejando 5% para fees/gas)
   - Se registra en logs: `"Cantidad calculada excede balance, ajustando"`

3. **Balance insuficiente** (< $1):
   - El trade se omite automáticamente

⚠️ **Requiere configurar Polygon RPC** para consultar el balance on-chain.

## Seguridad

- Las claves privadas se guardan localmente en `config.json` (nunca se suben a Git)
- `.gitignore` está configurado para excluir:
  - `config.json`
  - `copytrade.db` (base de datos local)
  - Archivos de caché Python

## Estructura del proyecto

```
polymarket-copytrade/
├── main.py              # Interfaz gráfica principal
├── trader.py            # Lógica de copy trading
├── polymarket_api.py    # Wrapper de API de Polymarket
├── database.py          # Gestión de SQLite
├── telegram_bot.py      # Notificaciones
├── config.example.json  # Ejemplo de configuración
├── requirements.txt     # Dependencias
└── README.md           # Este archivo
```

## Precauciones

⚠️ **Riesgos del copy trading**:
- Los traders pueden perder dinero
- El pasado no garantiza futuro rendimiento
- Configura límites de pérdida y no inviertas más de lo que puedes perder

⚠️ **Seguridad**:
- Nunca compartas tu `config.json` o claves privadas
- Usa una wallet dedicada para el bot, no tu wallet principal

## Licencia

MIT - Ver [LICENSE](LICENSE)

## Contribuciones

Pull requests bienvenidos. Para cambios grandes, abre un issue primero.

---

**Disclaimer**: Este software es experimental. Úsalo bajo tu propia responsabilidad.
