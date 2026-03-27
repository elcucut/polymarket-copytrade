import requests
from py_clob_client.client import ClobClient
from py_clob_client.order_builder.constants import BUY
from py_clob_client.clob_types import ApiCreds, MarketOrderArgs, OrderType


class PolymarketAPI:
    """Wrapper limpio sobre py-clob-client y la Data API de Polymarket"""

    DATA_API_URL = "https://data-api.polymarket.com"
    GAMMA_API_URL = "https://gamma-api.polymarket.com"
    POLYGON_RPC_URL = "https://polygon-mainnet.g.alchemy.com/v2/demo"  # Fallback público limitado
    USDC_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC en Polygon
    
    def __init__(self, private_key, funder_address, signature_type, polygon_rpc_url=None):
        """
        Inicializa el cliente de Polymarket

        Args:
            private_key: Clave privada de la wallet
            funder_address: Dirección del funder (dirección de depósito)
            signature_type: Tipo de firma (0=EOA, 1=Email/Magic, 2=Browser)
            polygon_rpc_url: URL del RPC de Polygon (opcional, para consultas on-chain)
        """
        self.private_key = private_key
        self.funder_address = funder_address
        self.signature_type = signature_type
        self.polygon_rpc_url = polygon_rpc_url or self.POLYGON_RPC_URL
        
        # Inicializa ClobClient
        self.client = ClobClient(
            "https://clob.polymarket.com",
            key=private_key,
            chain_id=137,  # Polygon
            signature_type=signature_type,
            funder=funder_address
        )
        
        # Crear o derivar credenciales API
        try:
            api_creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(api_creds)
        except Exception as e:
            print(f"Advertencia: No se pudieron crear credenciales API: {e}")
    
    def get_trader_positions(self, address):
        """
        Obtiene las posiciones activas de un trader

        Args:
            address: Dirección de la wallet del trader

        Returns:
            Lista de posiciones activas
        """
        try:
            url = f"{self.DATA_API_URL}/positions"
            params = {
                "user": address,
                "sizeThreshold": 1
            }
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            positions = response.json()

            # Normalizar el formato de las posiciones
            normalized = []
            for pos in positions:
                normalized.append({
                    "market": pos.get("market", ""),
                    "outcome": pos.get("outcome", ""),
                    "size": pos.get("size", 0),
                    "currentValue": pos.get("currentValue", 0),
                    "asset": pos.get("asset", ""),
                    "title": pos.get("title", "Desconocido"),
                    "token_id": pos.get("asset", "")  # El asset es el token_id
                })
            return normalized
        except Exception as e:
            print(f"Error obteniendo posiciones: {e}")
            return []

    def get_trader_trades(self, address, limit=50):
        """
        Obtiene los trades históricos de un trader

        Args:
            address: Dirección de la wallet del trader
            limit: Número máximo de trades a obtener

        Returns:
            Lista de trades
        """
        try:
            url = f"{self.DATA_API_URL}/trades"
            params = {
                "user": address,
                "limit": limit
            }
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            trades = response.json()

            # Normalizar el formato de los trades
            normalized = []
            for trade in trades:
                normalized.append({
                    "market": trade.get("market", ""),
                    "outcome": trade.get("outcome", ""),
                    "size": trade.get("size", 0),
                    "price": trade.get("price", 0),
                    "timestamp": trade.get("timestamp", ""),
                    "side": trade.get("side", ""),
                    "transactionHash": trade.get("transactionHash", ""),
                    "asset": trade.get("asset", "")
                })
            return normalized
        except Exception as e:
            print(f"Error obteniendo trades: {e}")
            return []

    def get_wallet_usdc_balance(self, address):
        """
        Obtiene el balance de USDC de una wallet en Polygon (on-chain)

        Args:
            address: Dirección de la wallet (0x...)

        Returns:
            Balance en USDC como float
        """
        try:
            # Limpiar y validar dirección
            address = address.lower().strip()
            if not address.startswith("0x"):
                print(f"Dirección inválida: {address}")
                return 0.0

            # Selector de función balanceOf(address): keccak256("balanceOf(address)")[:4] = 0x70a08231
            # + address paddeado a 32 bytes (quitar 0x y paddear con ceros a la izquierda)
            address_padded = "0" * 24 + address[2:]
            data = "0x70a08231" + address_padded

            payload = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": self.USDC_CONTRACT,
                    "data": data
                }, "latest"],
                "id": 1
            }

            response = requests.post(self.polygon_rpc_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                print(f"RPC Error: {result['error']}")
                return 0.0

            # El resultado viene como hex string (uint256)
            balance_hex = result.get("result", "0x0")
            balance_wei = int(balance_hex, 16)

            # USDC tiene 6 decimales
            balance_usdc = balance_wei / 1e6

            return balance_usdc

        except Exception as e:
            print(f"Error consultando balance USDC on-chain: {e}")
            return 0.0

    def get_trader_portfolio_value(self, address):
        """
        Obtiene el valor total del portfolio de un trader incluyendo:
        - Valor de posiciones abiertas (currentValue)
        - Cash disponible en USDC (balance on-chain)

        Args:
            address: Dirección de la wallet del trader

        Returns:
            Diccionario con:
                - positions_value: Valor de posiciones abiertas
                - cash_balance: Cash en USDC
                - total_value: Suma total (exposición + cash)
        """
        try:
            # Obtener valor de posiciones abiertas
            positions = self.get_trader_positions(address)
            positions_value = sum(pos.get('currentValue', 0) for pos in positions)

            # Obtener balance de USDC on-chain
            cash_balance = self.get_wallet_usdc_balance(address)

            # Total = posiciones + cash
            total_value = positions_value + cash_balance

            return {
                'positions_value': float(positions_value),
                'cash_balance': float(cash_balance),
                'total_value': float(total_value)
            }

        except Exception as e:
            print(f"Error obteniendo valor del portfolio: {e}")
            return {
                'positions_value': 0.0,
                'cash_balance': 0.0,
                'total_value': 0.0
            }
    
    def get_market_info(self, condition_id):
        """
        Obtiene información de un mercado
        
        Args:
            condition_id: ID de la condición del mercado
            
        Returns:
            Diccionario con información del mercado
        """
        try:
            url = f"{self.GAMMA_API_URL}/markets"
            params = {"condition_id": condition_id}
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                market = data[0]
                return {
                    "question": market.get("question", ""),
                    "tokens": market.get("tokens", []),
                    "active": market.get("active", True),
                    "closed": market.get("closed", False)
                }
            return {}
        except Exception as e:
            print(f"Error obteniendo info del mercado: {e}")
            return {}
    
    def get_token_price(self, token_id):
        """
        Obtiene el precio actual de un token
        
        Args:
            token_id: ID del token
            
        Returns:
            Precio entre 0 y 1
        """
        try:
            price = self.client.get_price(token_id, side=BUY)
            return float(price) if price else 0.5
        except Exception as e:
            print(f"Error obteniendo precio: {e}")
            return 0.5
    
    def get_balance(self):
        """
        Obtiene el balance USDC disponible usando on-chain query
        
        Returns:
            Balance USDC como float
        """
        try:
            # Usar consulta on-chain directa (más confiable que CLOB client)
            balance = self.get_wallet_usdc_balance(self.funder_address)
            if balance > 0:
                return balance
            
            # Fallback: intentar con CLOB client
            try:
                balance = self.client.get_balance()
                if balance:
                    return float(balance) / 1e6
            except:
                pass
            
            # Fallback 2: allowances
            try:
                allowances = self.client.get_allowances()
                if allowances:
                    return float(allowances) / 1e6
            except:
                pass
            
            return 0.0
        except Exception as e:
            print(f"Error obteniendo balance: {e}")
            return 0.0
    
    def execute_order(self, token_id, amount_usdc):
        """
        Ejecuta una orden de mercado
        
        Args:
            token_id: ID del token a comprar
            amount_usdc: Cantidad en USDC
            
        Returns:
            Tuple (success: bool, response/error)
        """
        try:
            # Crear orden de mercado FOK (Fill or Kill)
            mo = MarketOrderArgs(
                token_id=token_id,
                amount=amount_usdc,
                side=BUY,
                order_type=OrderType.FOK
            )
            
            # Firmar la orden
            signed = self.client.create_market_order(mo)
            
            # Enviar la orden
            resp = self.client.post_order(signed, OrderType.FOK)
            
            # Verificar si fue exitosa
            if resp and isinstance(resp, dict):
                if resp.get("success") or resp.get("orderId"):
                    return (True, resp)
                else:
                    return (False, resp.get("error", "Orden rechazada"))
            
            return (True, resp)
        except Exception as e:
            return (False, str(e))
