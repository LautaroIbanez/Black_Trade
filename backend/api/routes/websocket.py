"""WebSocket endpoints for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.active_connections.discard(conn)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Handle client messages if needed
                logger.debug(f"Received message: {message}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Helper function to broadcast updates
async def broadcast_order_update(order_id: str, status: str, details: dict = None):
    """Broadcast order update to all connected clients."""
    await manager.broadcast({
        "type": "order_update",
        "payload": {
            "order_id": order_id,
            "status": status,
            **({"details": details} if details else {})
        }
    })


async def broadcast_risk_update(metrics: dict):
    """Broadcast risk metrics update."""
    await manager.broadcast({
        "type": "risk_update",
        "payload": metrics
    })


async def broadcast_alert(severity: str, title: str, message: str, details: dict = None):
    """Broadcast alert to all connected clients."""
    await manager.broadcast({
        "type": "alert",
        "payload": {
            "severity": severity,
            "title": title,
            "message": message,
            **({"details": details} if details else {})
        }
    })


async def broadcast_order_filled(order_id: str, price: float, quantity: float):
    """Broadcast order fill notification."""
    await manager.broadcast({
        "type": "order_filled",
        "payload": {
            "order_id": order_id,
            "price": price,
            "quantity": quantity
        }
    })

