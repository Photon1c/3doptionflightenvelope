import json
import os

class FlightRenderer:
    """
    Generates an interactive 3D HTML visualization from telemetry logs.
    """
    def __init__(self, log_data, envelope_config):
        self.log_data = log_data
        self.config = envelope_config

    def render_to_html(self, output_path="4d_flight_sim.html"):
        # Convert config and log to JSON for embedding
        config_json = json.dumps({
            "atr": self.config.atr,
            "flip": self.config.flip,
            "put_wall": self.config.put_wall,
            "call_wall": self.config.call_wall
        })
        log_json = json.dumps(self.log_data)

        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>4D Option Flight Simulator</title>
    <style>
        body {{ margin: 0; background: #050505; color: #00ff88; font-family: monospace; overflow: hidden; }}
        #hud {{ position: absolute; top: 20px; left: 20px; background: rgba(0, 40, 0, 0.7); padding: 15px; border: 1px solid #00ff88; width: 250px; pointer-events: none; }}
        #legend {{ position: absolute; bottom: 80px; right: 20px; background: rgba(0, 20, 0, 0.6); padding: 10px; border: 1px solid #00ff88; font-size: 0.8em; color: #00ff88; pointer-events: none; }}
        #controls {{ position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(0, 20, 0, 0.8); padding: 10px; border: 1px solid #00ff88; display: flex; gap: 10px; align-items: center; }}
        canvas {{ display: block; }}
        .label {{ color: #55ff55; font-weight: bold; }}
        .warning {{ color: #ff5555; animation: blink 0.5s infinite; }}
        @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0; }} 100% {{ opacity: 1; }} }}
        input[type=range] {{ width: 300px; }}
        button {{ background: #004422; color: #00ff88; border: 1px solid #00ff88; padding: 5px 10px; cursor: pointer; }}
        button:hover {{ background: #006633; }}
    </style>
</head>
<body>
    <div id="hud">
        <div style="font-size: 1.2em; border-bottom: 1px solid #00ff88; margin-bottom: 10px;">FLIGHT TELEMETRY</div>
        <div>REGIME: <span id="regime-val" class="label">TAXI</span></div>
        <div>SPOT: <span id="spot-val">0.00</span></div>
        <div>AIRSPEED (X): <span id="x-val">0.00</span></div>
        <div>LOAD (Y): <span id="y-val">0.00</span></div>
        <div>PROXIMITY (Z): <span id="z-val">0.00</span></div>
        <div id="warnings" style="margin-top: 10px;"></div>
    </div>

    <div id="legend">
        <b>CONTROLS:</b><br>
        WASD : NAVIGATE<br>
        ARROWS: LOOK<br>
        Q/E : ELEVATION<br>
        SPACE : RESET CAM
    </div>

    <div id="controls">
        <button id="play-btn">PLAY</button>
        <input type="range" id="timeline" min="0" max="0" step="1" value="0">
        <span id="step-counter">0/0</span>
        <select id="speed-select">
            <option value="1">1x</option>
            <option value="2">2x</option>
            <option value="5">5x</option>
        </select>
        <input type="file" id="log-upload" accept=".jsonl" style="display:none">
        <button onclick="document.getElementById('log-upload').click()">LOAD LOG</button>
    </div>

    <canvas id="simCanvas"></canvas>

    <script>
        const config = {config_json};
        const telemetry = {log_json};
        let currentStep = 0;
        let isPlaying = false;
        let playSpeed = 1;

        // Camera State
        const cam = {{
            pos: {{ x: 0, y: 2.5, z: -15 }},
            rot: {{ x: 0.2, y: 0 }},
            keys: {{}}
        }};

        const canvas = document.getElementById('simCanvas');
        const ctx = canvas.getContext('2d');
        
        function resize() {{
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }}
        window.addEventListener('resize', resize);
        resize();

        // HUD Elements
        const regimeEl = document.getElementById('regime-val');
        const spotEl = document.getElementById('spot-val');
        const xEl = document.getElementById('x-val');
        const yEl = document.getElementById('y-val');
        const zEl = document.getElementById('z-val');
        const warningsEl = document.getElementById('warnings');
        const timeline = document.getElementById('timeline');
        const stepCounter = document.getElementById('step-counter');
        const playBtn = document.getElementById('play-btn');

        timeline.max = telemetry.length - 1;
        stepCounter.innerText = `0/${{telemetry.length - 1}}`;

        // 3D Projection Engine - Tron Optimized & Screen-Safe with Camera
        function project(x, y, z) {{
            const baseScale = Math.min(canvas.width, canvas.height) * 0.8;
            
            // 1. Lens-Safe squash (World Space)
            const squash = (val, limit) => {{
                if (Math.abs(val) <= limit) return val;
                const sign = Math.sign(val);
                return sign * (limit + Math.log(1 + Math.abs(val) - limit));
            }};
            const sx = squash(x, 6.0);
            const sy = squash(y, 5.0);

            // 2. Translate (Camera Space)
            let tx = sx - cam.pos.x;
            let ty = sy - cam.pos.y;
            let tz = z - cam.pos.z;

            // 3. Rotate
            // Yaw (around Y)
            let x1 = tx * Math.cos(cam.rot.y) - tz * Math.sin(cam.rot.y);
            let z1 = tx * Math.sin(cam.rot.y) + tz * Math.cos(cam.rot.y);
            // Pitch (around X)
            let y2 = ty * Math.cos(cam.rot.x) - z1 * Math.sin(cam.rot.x);
            let z2 = ty * Math.sin(cam.rot.x) + z1 * Math.cos(cam.rot.x);

            const pZ = z2; 
            if (pZ <= 0.5) return {{ x: -9999, y: -9999 }}; 

            return {{
                x: (x1 / pZ) * baseScale + canvas.width / 2,
                y: ((-y2) / pZ) * baseScale + canvas.height / 2
            }};
        }}

        function drawGrid() {{
            const time = Date.now() / 1000;
            const scroll = (time * 2) % 4; 
            
            ctx.lineWidth = 1;
            ctx.shadowBlur = 5;
            ctx.shadowColor = '#00ff88';

            // Draw Neon Floor
            ctx.strokeStyle = 'rgba(0, 255, 136, 0.1)';
            for (let x = -20; x <= 20; x += 4) {{
                const p1 = project(x, -1.5, -15);
                const p2 = project(x, -1.5, 15);
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            }}
            for (let z = -15; z <= 15; z += 4) {{
                const p1 = project(-20, -1.5, z - scroll);
                const p2 = project(20, -1.5, z - scroll);
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            }}
        }}

        function drawEnvelope() {{
            ctx.shadowBlur = 10;
            ctx.shadowColor = '#00ff88';
            
            const zStart = -4;
            const zEnd = 4;
            
            const corners = [
                [-2.5, -1], [2.5, -1], [2.5, 2], [-2.5, 2]
            ];

            // Longitudinal ribs
            ctx.lineWidth = 2;
            ctx.strokeStyle = 'rgba(0, 255, 136, 0.15)';
            corners.forEach(c => {{
                const p1 = project(c[0], c[1], zStart);
                const p2 = project(c[0], c[1], zEnd);
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            }});

            // Transverse Rings
            for (let z = zStart; z <= zEnd; z += 2.0) {{
                const alpha = 1 - Math.abs(z / 6);
                ctx.strokeStyle = `rgba(0, 255, 136, ${{alpha * 0.5}})`;
                ctx.lineWidth = z === zStart || z === zEnd ? 3 : 1;
                
                ctx.beginPath();
                corners.forEach((c, i) => {{
                    const p = project(c[0], c[1], z);
                    if (i === 0) ctx.moveTo(p.x, p.y);
                    else ctx.lineTo(p.x, p.y);
                }});
                ctx.closePath();
                ctx.stroke();
            }}
        }}

        function drawFlightPath() {{
            if (telemetry.length === 0) return;
            
            ctx.shadowBlur = 15;
            
            for (let i = 1; i <= currentStep; i++) {{
                const s1 = telemetry[i-1];
                const s2 = telemetry[i];
                
                const z1 = ( (i-1) / telemetry.length ) * 8 - 4;
                const z2 = ( i / telemetry.length ) * 8 - 4;
                
                const p1 = project(s1.x - 2.5, s1.y - 0.5, z1);
                const p2 = project(s2.x - 2.5, s2.y - 0.5, z2);
                
                const alpha = 0.2 + (0.8 * i / currentStep);
                if (s2.regime === 'RUPTURE') {{
                    ctx.strokeStyle = `rgba(255, 0, 85, ${{alpha}})`;
                    ctx.shadowColor = '#ff0055';
                    ctx.lineWidth = 4;
                }} else {{
                    ctx.strokeStyle = `rgba(0, 255, 255, ${{alpha}})`;
                    ctx.shadowColor = '#00ffff';
                    ctx.lineWidth = 2;
                }}
                
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            }}

            const current = telemetry[currentStep];
            const cz = (currentStep / telemetry.length) * 8 - 4;
            const cp = project(current.x - 2.5, current.y - 0.5, cz);
            
            ctx.shadowBlur = 20;
            ctx.fillStyle = current.regime === 'RUPTURE' ? '#ff0055' : '#00ffff';
            ctx.shadowColor = ctx.fillStyle;
            
            ctx.beginPath();
            ctx.arc(cp.x, cp.y, 6, 0, Math.PI * 2);
            ctx.fill();
            
            if (current.flags.length > 0) {{
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(cp.x, cp.y, 10 + Math.sin(Date.now()/100)*5, 0, Math.PI * 2);
                ctx.stroke();
            }}
            ctx.shadowBlur = 0;
        }}

        function updateHUD() {{
            const step = telemetry[currentStep];
            regimeEl.innerText = step.regime;
            spotEl.innerText = step.spot.toFixed(2);
            xEl.innerText = step.x.toFixed(2);
            yEl.innerText = step.y.toFixed(2);
            zEl.innerText = step.z.toFixed(2);
            
            warningsEl.innerHTML = '';
            step.flags.forEach(f => {{
                const div = document.createElement('div');
                div.className = 'warning';
                div.innerText = `WARNING: ${{f}}`;
                warningsEl.appendChild(div);
            }});

            timeline.value = currentStep;
            stepCounter.innerText = `${{currentStep}}/${{telemetry.length - 1}}`;
            
            // Set regime color
            const colors = {{
                'TAXI': '#aaaaaa',
                'CRUISE': '#00ff88',
                'MANEUVER': '#ffff00',
                'RUPTURE': '#ff0000'
            }};
            regimeEl.style.color = colors[step.regime] || '#00ff88';
        }}

        function loop() {{
            updateCamera();

            ctx.fillStyle = '#050505';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            drawGrid();
            drawEnvelope();
            drawFlightPath();
            
            if (isPlaying && currentStep < telemetry.length - 1) {{
                currentStep += playSpeed;
                if (currentStep >= telemetry.length) currentStep = telemetry.length - 1;
                updateHUD();
            }} else if (currentStep >= telemetry.length - 1) {{
                isPlaying = false;
                playBtn.innerText = 'REPLAY';
            }}
            
            requestAnimationFrame(loop);
        }}

        function updateCamera() {{
            const speed = 0.2;
            const rotSpeed = 0.03;
            
            // Rotation (Arrows)
            if (cam.keys['ArrowLeft']) cam.rot.y -= rotSpeed;
            if (cam.keys['ArrowRight']) cam.rot.y += rotSpeed;
            if (cam.keys['ArrowUp']) cam.rot.x -= rotSpeed;
            if (cam.keys['ArrowDown']) cam.rot.x += rotSpeed;

            // Movement (WASD + QE)
            const forwardX = Math.sin(cam.rot.y);
            const forwardZ = -Math.cos(cam.rot.y);
            const rightX = Math.cos(cam.rot.y);
            const rightZ = Math.sin(cam.rot.y);

            if (cam.keys['KeyW']) {{
                cam.pos.x += forwardX * speed;
                cam.pos.z += forwardZ * speed;
            }}
            if (cam.keys['KeyS']) {{
                cam.pos.x -= forwardX * speed;
                cam.pos.z -= forwardZ * speed;
            }}
            if (cam.keys['KeyA']) {{
                cam.pos.x -= rightX * speed;
                cam.pos.z -= rightZ * speed;
            }}
            if (cam.keys['KeyD']) {{
                cam.pos.x += rightX * speed;
                cam.pos.z += rightZ * speed;
            }}
            if (cam.keys['KeyQ']) cam.pos.y += speed;
            if (cam.keys['KeyE']) cam.pos.y -= speed;

            if (cam.keys['Space']) {{
                cam.pos = {{ x: 0, y: 2.5, z: -15 }};
                cam.rot = {{ x: 0.2, y: 0 }};
            }}
        }}

        window.addEventListener('keydown', e => cam.keys[e.code] = true);
        window.addEventListener('keyup', e => cam.keys[e.code] = false);

        playBtn.onclick = () => {{
            if (currentStep >= telemetry.length - 1) currentStep = 0;
            isPlaying = !isPlaying;
            playBtn.innerText = isPlaying ? 'PAUSE' : 'PLAY';
        }};

        timeline.oninput = (e) => {{
            currentStep = parseInt(e.target.value);
            updateHUD();
        }};

        document.getElementById('speed-select').onchange = (e) => {{
            playSpeed = parseInt(e.target.value);
        }};

        document.getElementById('log-upload').onchange = (e) => {{
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (event) => {{
                const lines = event.target.result.split('\\n');
                const newTelemetry = [];
                lines.forEach(line => {{
                    if (line.trim()) newTelemetry.push(JSON.parse(line));
                }});
                if (newTelemetry.length > 0) {{
                    telemetry.length = 0;
                    telemetry.push(...newTelemetry);
                    currentStep = 0;
                    isPlaying = false;
                    timeline.max = telemetry.length - 1;
                    updateHUD();
                }}
            }};
            reader.readAsText(file);
        }};

        loop();
    </script>
</body>
</html>
        """
        with open(output_path, 'w') as f:
            f.write(html_template)
        return output_path
