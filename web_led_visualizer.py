"""
Web-based LED Visualizer for muni_map

This module provides a web-based visualization interface for LED states
using Flask and Socket.IO for real-time updates.
"""

import os
import threading
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from chip_ctrl import MockLP5018, create_led_controller
import json

# Initialize Flask app and Socket.IO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'muni-map-led-visualizer-secret-key'
app.config['JSON_AS_ASCII'] = False

socketio = SocketIO(app, cors_allowed_origins="*")

# Global LED controller instance
led_controller = None
visualizer_thread = None
stop_thread = None

# Default stop names mapping (can be overridden)
DEFAULT_STOP_NAMES = {
    0: "20th St Right Of Way",
    1: "Church St & 18th St",
    3: "Church St & 16th St",
    4: "Church St & Market St",
    5: "Van Ness",
    7: "Civic Center",
    8: "Powell",
    9: "Montgomery",
    10: "Embarcadero",
    12: "Liberty St",
    13: "21st St",
    14: "22nd St",
    15: "24th St",
    17: "26th St",
    19: "28th St",
    20: "Day St",
    21: "Randall St",
    22: "30th St & Dolores"
}


def initialize_led_controller(stop_names=None):
    """Initialize the LED controller with given stop names."""
    global led_controller
    stop_names = stop_names or DEFAULT_STOP_NAMES.copy()
    led_controller = create_led_controller(use_mock=True, stop_names=stop_names)


def led_visualizer_loop():
    """Background thread that updates LED states and broadcasts them."""
    global led_controller
    while True:
        if led_controller:
            # Get current LED states
            led_states = led_controller.get_all_led_states()
            # Get pulsing LED list
            pulsing_leds = list(led_controller.pulsing_outputs) if hasattr(led_controller, 'pulsing_outputs') else []
            # Debug output - get client count from sockets
            client_count = len(socketio.server.eio.sockets)
            print(f"Visualizer: led_states={led_states}, pulsing_leds={pulsing_leds}, clients={client_count}")
            # Broadcast to all connected clients in the room
            socketio.emit('led_update', {'led_states': led_states, 'stop_names': DEFAULT_STOP_NAMES.copy(), 'pulsing_leds': pulsing_leds}, room='led_visualizer')
            # Broadcast client count
            socketio.emit('client_count', {'count': client_count}, room='led_visualizer')
        threading.Event().wait(0.1)  # Check every 100ms


def get_brightness_state(brightness):
    """Return CSS class based on brightness level."""
    if brightness == 0:
        return "off"
    elif brightness < 64:
        return "dim"
    elif brightness < 128:
        return "medium"
    elif brightness < 200:
        return "bright"
    else:
        return "full"


def get_brightness_color(brightness):
    """Return color intensity based on brightness level."""
    if brightness == 0:
        return "#333333"
    elif brightness < 64:
        return "#ff4444"
    elif brightness < 128:
        return "#ff8800"
    elif brightness < 200:
        return "#ffcc00"
    else:
        return "#ffff00"


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Muni Map LED Visualizer</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }

        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #666;
            animation: pulse 2s infinite;
        }

        .status-dot.connected {
            background: #4ade80;
            animation: pulse-green 1s infinite;
        }

        .status-dot.disconnected {
            background: #ef4444;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        @keyframes pulse-green {
            0%, 100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.7); }
            50% { box-shadow: 0 0 0 10px rgba(74, 222, 128, 0); }
        }

        @keyframes pulse-ring-active {
            0% {
                transform: scale(1);
                opacity: 1;
            }
            50% {
                transform: scale(1.3);
                opacity: 0.7;
            }
            100% {
                transform: scale(1);
                opacity: 1;
            }
        }

        .controls {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .control-group {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255, 255, 255, 0.1);
            padding: 10px 15px;
            border-radius: 8px;
        }

        .control-group label {
            font-weight: 600;
        }

        input[type="range"] {
            width: 150px;
            cursor: pointer;
        }

        .led-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            padding: 20px 0;
        }

        .led-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            position: relative;
        }

        .led-container:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
        }

        .led-container.active {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }

        .led {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            margin: 15px auto;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            position: relative;
            z-index: 1;
        }

        .led.off {
            background: #333333;
            box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.5);
        }

        .led.dim {
            background: #ff4444;
            box-shadow: 0 0 20px #ff4444, inset 0 2px 5px rgba(0, 0, 0, 0.5);
        }

        .led.medium {
            background: #ff8800;
            box-shadow: 0 0 30px #ff8800, inset 0 2px 5px rgba(0, 0, 0, 0.5);
        }

        .led.bright {
            background: #ffcc00;
            box-shadow: 0 0 45px #ffcc00, inset 0 2px 5px rgba(0, 0, 0, 0.5);
        }

        .led.full {
            background: #ffff00;
            box-shadow: 0 0 60px #ffff00, inset 0 2px 5px rgba(0, 0, 0, 0.5);
        }

        .led-info {
            margin-top: 10px;
        }

        .led-id {
            font-size: 1.2em;
            font-weight: 600;
            color: #4ade80;
        }

        .led-name {
            font-size: 0.85em;
            color: #aaa;
            margin-top: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }

        .led-brightness {
            font-size: 0.8em;
            color: #888;
            margin-top: 5px;
        }

        .led-brightness span {
            font-weight: 600;
            color: #fff;
        }

        .pulsing-indicator {
            position: absolute;
            top: -3px;
            left: -3px;
            width: calc(100% + 6px);
            height: calc(100% + 6px);
            border: 3px solid #4ade80;
            border-radius: 50%;
            transform: none;
            pointer-events: none;
            z-index: 10;
            background: rgba(74, 222, 128, 0.3);
            box-shadow: 0 0 15px #4ade80, 0 0 30px rgba(74, 222, 128, 0.5);
        }

        .pulsing-indicator.active {
            animation: pulse-ring-active 1s infinite;
        }

        .legend {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            flex-wrap: wrap;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .legend-dot {
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }

        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }

        @media (max-width: 768px) {
            h1 {
                font-size: 1.8em;
            }

            .led-grid {
                grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
                gap: 10px;
            }

            .led {
                width: 60px;
                height: 60px;
            }

            .led-name {
                font-size: 0.7em;
            }

            .status-bar {
                flex-direction: column;
                gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Muni Map LED Visualizer</h1>
            <p>Real-time visualization of LED states for controlled stops</p>
        </header>

        <div class="status-bar">
            <div class="status-indicator">
                <div class="status-dot" id="connectionStatus"></div>
                <span id="connectionText">Connecting...</span>
            </div>
            <div class="status-indicator">
                <span>Connected Clients:</span>
                <span id="clientCount">0</span>
            </div>
        </div>

        <div class="controls">
            <div class="control-group">
                <label for="brightnessControl">Adjust Brightness:</label>
                <input type="range" id="brightnessControl" min="0" max="255" value="0">
                <span id="brightnessValue">0</span>
            </div>
        </div>

        <div class="led-grid" id="ledGrid">
            <!-- LED containers will be generated here -->
        </div>

        <div class="legend">
            <div class="legend-item">
                <div class="led-dot off"></div>
                <span>Off</span>
            </div>
            <div class="legend-item">
                <div class="led-dot dim" style="background: #ff4444;"></div>
                <span>Dim</span>
            </div>
            <div class="legend-item">
                <div class="led-dot medium" style="background: #ff8800;"></div>
                <span>Medium</span>
            </div>
            <div class="legend-item">
                <div class="led-dot bright" style="background: #ffcc00;"></div>
                <span>Bright</span>
            </div>
            <div class="legend-item">
                <div class="led-dot full" style="background: #ffff00;"></div>
                <span>Full</span>
            </div>
        </div>

        <div class="footer">
            <p>Muni Map LED Visualizer - Real-time Monitoring</p>
        </div>
    </div>

    <script>
        // Connect to Socket.IO server
        const socket = io();

        // Generate LED grid on page load
        document.addEventListener('DOMContentLoaded', function() {
            const ledGrid = document.getElementById('ledGrid');
            const ledNames = {
                0: "20th St Right Of Way",
                1: "Church St & 18th St",
                3: "Church St & 16th St",
                4: "Church St & Market St",
                5: "Van Ness",
                7: "Civic Center",
                8: "Powell",
                9: "Montgomery",
                10: "Embarcadero",
                12: "Liberty St",
                13: "21st St",
                14: "22nd St",
                15: "24th St",
                17: "26th St",
                19: "28th St",
                20: "Day St",
                21: "Randall St",
                22: "30th St & Dolores"
            };

            // Create LED container for each LED
            for (let i = 0; i <= 23; i++) {
                const ledContainer = document.createElement('div');
                ledContainer.className = 'led-container';
                ledContainer.id = `led-container-${i}`;

                const ledName = ledNames[i] || `LED ${i}`;

                ledContainer.innerHTML = `
                    <div class="led led-off" id="led-${i}">
                        <div class="pulsing-indicator" id="pulsing-${i}"></div>
                    </div>
                    <div class="led-info">
                        <div class="led-id">LED ${i}</div>
                        <div class="led-name">${ledName}</div>
                        <div class="led-brightness">Brightness: <span id="brightness-${i}">0</span></div>
                    </div>
                `;

                ledGrid.appendChild(ledContainer);
            }

            // Initialize brightness slider
            initBrightnessSlider();

            // Handle incoming LED updates
            socket.on('led_update', function(data) {
                const { led_states, stop_names, pulsing_leds } = data;

                // Update each LED
                for (const [ledId, brightness] of Object.entries(led_states)) {
                    const led = document.getElementById(`led-${ledId}`);
                    const brightnessEl = document.getElementById(`brightness-${ledId}`);
                    const pulsingEl = led ? led.querySelector('.pulsing-indicator') : null;

                    if (led) {
                        // Update brightness
                        brightnessEl.textContent = brightness;

                        // Update LED appearance - remove all brightness classes first, then add the new one
                        led.className = 'led';
                        if (brightness === 0) {
                            led.classList.add('off');
                        } else if (brightness < 64) {
                            led.classList.add('dim');
                        } else if (brightness < 128) {
                            led.classList.add('medium');
                        } else if (brightness < 200) {
                            led.classList.add('bright');
                        } else {
                            led.classList.add('full');
                        }

                        // Update container appearance
                        const container = document.getElementById(`led-container-${ledId}`);
                        if (brightness > 0) {
                            container.classList.add('active');
                        } else {
                            container.classList.remove('active');
                        }

                        // Update pulsing indicator
                        if (pulsingEl) {
                            if (pulsing_leds && pulsing_leds.includes(parseInt(ledId))) {
                                pulsingEl.classList.add('active');
                            } else {
                                pulsingEl.classList.remove('active');
                            }
                        }
                    }
                }
            });

            // Handle client count updates
            socket.on('client_count', function(data) {
                const clientCountEl = document.getElementById('clientCount');
                if (clientCountEl) {
                    clientCountEl.textContent = data.count;
                }
            });

            // Handle connection events
            socket.on('connect', function() {
                console.log('Connected to LED visualizer');
                // Join a room to receive broadcasts
                socket.join('led_visualizer');
                updateConnectionStatus(true);
            });

            socket.on('disconnect', function(reason) {
                console.log('Disconnected from LED visualizer', reason);
                updateConnectionStatus(false);
            });

            socket.on('connect_error', function(err) {
                console.error('Connection error:', err);
                updateConnectionStatus(false);
            });

            // Update connection status display
            function updateConnectionStatus(connected) {
                const statusDot = document.getElementById('connectionStatus');
                const statusText = document.getElementById('connectionText');
                if (statusDot) {
                    statusDot.className = connected ? 'status-dot connected' : 'status-dot disconnected';
                }
                if (statusText) {
                    statusText.textContent = connected ? 'Connected' : 'Disconnected';
                }
            }

            // Initialize brightness slider
            function initBrightnessSlider() {
                const slider = document.getElementById('brightnessControl');
                const valueDisplay = document.getElementById('brightnessValue');
                const ledElement = document.getElementById('led-0');

                slider.addEventListener('input', function() {
                    valueDisplay.textContent = this.value;
                    // Actually set the brightness on the LED
                    if (ledElement) {
                        ledElement.style.background = this.value === '0' ? '#333333' : `rgba(255, 255, 0, ${this.value / 255})`;
                        ledElement.style.boxShadow = this.value === '0' ? 'inset 0 2px 5px rgba(0, 0, 0, 0.5)' : `0 0 ${this.value}px rgba(255, 255, 0, ${this.value / 255}), inset 0 2px 5px rgba(0, 0, 0, 0.5)`;
                    }
                });
            }
        });
    </script>
</body>
</html>
'''


# HTML template for API response page
API_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LED API - Muni Map</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            background: #1a1a2e;
            color: #fff;
            padding: 40px;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            color: #4ade80;
            margin-bottom: 30px;
        }
        .endpoint {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .method {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 10px;
        }
        .get { background: #4ade80; color: #000; }
        .post { background: #f97316; color: #fff; }
        pre {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>LED Controller API</h1>

        <div class="endpoint">
            <span class="method get">GET</span>
            <span class="method post">POST</span>
            <strong>/api/led-states</strong>
            <p>Get current LED states</p>
            <pre>{}</pre>
        </div>

        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/api/led-states/set/<int:led_id>/<int:brightness></strong>
            <p>Set brightness for a specific LED</p>
            <pre>Example: /api/led-states/set/5/128</pre>
        </div>

        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/api/led-states/pulse/<int:led_id></strong>
            <p>Start pulsing a specific LED</p>
            <pre>Example: /api/led-states/pulse/10</pre>
        </div>

        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/api/led-states/pulsed</strong>
            <p>Set multiple LEDs to pulse</p>
            <pre>Example: /api/led-states/pulse/1,2,3,4,5</pre>
        </div>

        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/api/led-states/reset</strong>
            <p>Reset all LEDs to default state</p>
            <pre>Example: /api/led-states/reset</pre>
        </div>

        <p style="margin-top: 30px; color: #888;">
            For real-time visualization, open the main visualizer page:<br>
            <a href="/visualizer" style="color: #4ade80;">/visualizer</a>
        </p>
    </div>
</body>
</html>
'''


@app.route('/')
def index():
    """Main page - LED visualizer."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/visualizer')
def visualizer():
    """Alias for main visualizer page."""
    return render_template_string(HTML_TEMPLATE)


# Socket.IO event handlers for connection tracking
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f'>>> Client connected (sid={request.sid})')
    # Join the room so broadcasts reach this client
    join_room('led_visualizer')
    # Send current client count to the new client
    client_count = len(socketio.server.eio.sockets.keys())
    emit('client_count', {'count': client_count}, room='led_visualizer')


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f'>>> Client disconnected (sid={request.sid})')
    # Leave the room on disconnect
    leave_room('led_visualizer')


@app.route('/api')
def api_index():
    """API documentation page."""
    return render_template_string(API_TEMPLATE, json.dumps({}, indent=2))


@app.route('/api/led-states', methods=['GET'])
def get_led_states():
    """Get current LED states."""
    if led_controller:
        states = led_controller.get_all_led_states()
        pulsing_leds = list(led_controller.pulsing_outputs) if hasattr(led_controller, 'pulsing_outputs') else []
        return jsonify({
            'success': True,
            'led_states': states,
            'stop_names': DEFAULT_STOP_NAMES.copy(),
            'pulsing_leds': pulsing_leds
        })
    return jsonify({'success': False, 'error': 'LED controller not initialized'}), 500


@app.route('/api/led-states/set/<int:led_id>/<int:brightness>', methods=['GET'])
def set_led_brightness(led_id, brightness):
    """Set brightness for a specific LED."""
    if led_controller:
        try:
            led_controller.set_brightness(led_id, brightness)
            return jsonify({
                'success': True,
                'message': f'Set LED {led_id} to brightness {brightness}',
                'led_id': led_id,
                'brightness': brightness
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'LED controller not initialized'}), 500


@app.route('/api/led-states/pulse/<int:led_id>', methods=['GET'])
def pulse_led(led_id):
    """Start pulsing a specific LED."""
    if led_controller:
        try:
            led_controller.pulse_output(led_id)
            return jsonify({
                'success': True,
                'message': f'Started pulsing LED {led_id}',
                'led_id': led_id
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'LED controller not initialized'}), 500


@app.route('/api/led-states/pulse', methods=['GET'])
def set_pulsed_leds():
    """Set multiple LEDs to pulse."""
    if led_controller:
        led_ids = request.args.get('leds', '').split(',')
        try:
            led_ids = [int(x.strip()) for x in led_ids]
            led_controller.set_pulsed_outputs(led_ids)
            return jsonify({
                'success': True,
                'message': f'Started pulsing LEDs: {led_ids}',
                'led_ids': led_ids
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'LED controller not initialized'}), 500


@app.route('/api/led-states/reset', methods=['GET'])
def reset_leds():
    """Reset all LEDs to default state."""
    if led_controller:
        led_controller.reset()
        return jsonify({
            'success': True,
            'message': 'All LEDs reset to default state'
        })
    return jsonify({'success': False, 'error': 'LED controller not initialized'}), 500


def start_web_visualizer(stop_names=None, shared_led_controller=None):
    """
    Start the web-based LED visualizer server.

    Args:
        stop_names: Optional dictionary mapping LED indices to stop names
        shared_led_controller: Optional shared LED controller instance (orchestrator's controller)
    """
    global led_controller

    # Debug: print what we're receiving
    print(f"start_web_visualizer: shared_led_controller={shared_led_controller is not None}")
    print(f"start_web_visualizer: shared_led_controller id={id(shared_led_controller) if shared_led_controller else None}")

    # Use shared LED controller if provided (e.g., from orchestrator)
    if shared_led_controller is not None:
        led_controller = shared_led_controller
        print(f"start_web_visualizer: Using shared controller (id={id(led_controller)})")
    else:
        # Otherwise, initialize a new LED controller
        initialize_led_controller(stop_names)
        print(f"start_web_visualizer: Initialized new controller (id={id(led_controller)})")

    # Start the visualizer thread
    visualizer_thread = threading.Thread(target=led_visualizer_loop, daemon=True)
    visualizer_thread.start()

    # Get port from environment variable or use default
    port = int(os.environ.get('LED_VISUALIZER_PORT', 5000))
    debug = os.environ.get('LED_VISUALIZER_DEBUG', 'false').lower() == 'true'

    print(f"Starting LED Visualizer on http://localhost:{port}")
    print(f"Stop names loaded: {len(DEFAULT_STOP_NAMES)} mappings")
    print("Press Ctrl+C to stop the server")

    # Run the Flask app with Socket.IO
    socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    # Start the web visualizer
    start_web_visualizer()
