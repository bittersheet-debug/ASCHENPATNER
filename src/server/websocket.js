/**
 * ASCHEN EVENT ORGANIZER - WebSocket Real-Time Events
 */

const { WebSocketServer } = require('ws');

function initWebSocket(server) {
  const wss = new WebSocketServer({ server });
  const clients = new Set();

  wss.on('connection', (ws) => {
    clients.add(ws);

    ws.on('close', () => {
      clients.delete(ws);
    });

    ws.on('error', (err) => {
      console.error('[WS] Client error:', err);
      clients.delete(ws);
    });
  });

  // Emulation of io.emit for simple broadcast
  const io = {
    emit: (event, data) => {
      const payload = JSON.stringify({ event, data });
      clients.forEach(client => {
        if (client.readyState === 1) { // OPEN
          try {
            client.send(payload);
          } catch (e) {}
        }
      });
    }
  };

  return { wss, io };
}

module.exports = { initWebSocket };
