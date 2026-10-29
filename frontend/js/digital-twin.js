/**
 * VisionGuard AI 2.0 - 3D Industrial Digital Twin
 * Three.js interactive 3D conveyor system with component selection,
 * defect overlay markers, telemetry state, and animated motion.
 */

class ConveyorDigitalTwin {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentAssetId = "CONV-01";
    this.components = [];
    this.selectedComponent = null;
    this.hoveredObject = null;
    this.overlaysEnabled = true;
    this.labelsEnabled = true;
    this.isRunning = true;
    this.speed = 1.8; // m/s
    this.beltOffset = 0;

    // Three.js instances
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.raycaster = null;
    this.mouse = null;
    this.animationFrameId = null;

    // Mesh groups
    this.conveyorGroup = null;
    this.interactiveObjects = [];
    this.defectMarkers = [];
    this.beltMesh = null;
    this.beltMaterial = null;
  }

  init() {
    if (!this.container) return;
    if (typeof THREE === "undefined") {
      this.container.innerHTML = `
        <div class="d-flex align-items-center justify-content-center h-100 text-muted flex-column">
          <i class="bi bi-exclamation-triangle fs-1 text-warning mb-2"></i>
          <div>Three.js 3D Engine could not be loaded from CDN.</div>
          <small>Check network connection or CDN availability.</small>
        </div>`;
      return;
    }

    this.setupScene();
    this.setupLighting();
    this.buildConveyorModel();
    this.setupEventListeners();
    this.animate();

    // Load initial asset data
    this.loadAsset(this.currentAssetId);

    // Listen to real-time telemetry if WS client is active
    if (window.vgWS) {
      window.vgWS.on("telemetry.updated", (data) => this.handleLiveTelemetry(data));
      window.vgWS.on("asset.status_changed", (data) => {
        if (data.asset_id === this.currentAssetId) this.loadAsset(this.currentAssetId);
      });
    }
  }

  setupScene() {
    const width = this.container.clientWidth || 800;
    const height = this.container.clientHeight || 500;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x070a10); // Deep industrial graphite
    this.scene.fog = new THREE.FogExp2(0x070a10, 0.018);

    // Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    this.camera.position.set(12, 8, 14);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Clear previous elements
    this.container.innerHTML = "";
    this.container.appendChild(this.renderer.domElement);

    // OrbitControls
    if (typeof THREE.OrbitControls !== "undefined") {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      this.controls.maxPolarAngle = Math.PI / 2 - 0.05; // Prevent flipping below ground
      this.controls.minDistance = 3;
      this.controls.maxDistance = 40;
      this.controls.target.set(0, 1, 0);
    }

    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    // Industrial Grid Floor
    const grid = new THREE.GridHelper(30, 30, 0x06b6d4, 0x1e293b);
    grid.position.y = -0.01;
    this.scene.add(grid);
  }

  setupLighting() {
    // Ambient light
    const ambientLight = new THREE.AmbientLight(0x1e293b, 1.2);
    this.scene.add(ambientLight);

    // Main Key Light (cyan/cool white)
    const keyLight = new THREE.DirectionalLight(0xe0f2fe, 1.8);
    keyLight.position.set(15, 20, 10);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 0.5;
    keyLight.shadow.camera.far = 50;
    this.scene.add(keyLight);

    // Cyan Industrial Rim Accent Light
    const cyanLight = new THREE.DirectionalLight(0x06b6d4, 1.5);
    cyanLight.position.set(-15, 10, -10);
    this.scene.add(cyanLight);

    // Under-chassis glow light
    const pointLight = new THREE.PointLight(0x38bdf8, 1.0, 15);
    pointLight.position.set(0, 1, 0);
    this.scene.add(pointLight);
  }

  buildConveyorModel() {
    this.conveyorGroup = new THREE.Group();
    this.interactiveObjects = [];

    // Materials
    const metalDark = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.8,
      roughness: 0.3
    });

    const steelFrameMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      metalness: 0.6,
      roughness: 0.4
    });

    const rollerMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      metalness: 0.9,
      roughness: 0.2
    });

    const motorMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7, // Electric blue industrial motor casing
      metalness: 0.5,
      roughness: 0.3
    });

    // Conveyor Belt Length and Profile
    const beltLength = 16;
    const beltWidth = 2.2;
    const rollerRadius = 0.6;

    // 1. Structural Truss / Legs
    const legGeo = new THREE.BoxGeometry(0.2, 2.2, 0.2);
    const crossBarGeo = new THREE.BoxGeometry(0.15, 0.15, beltWidth + 0.6);
    const railGeo = new THREE.BoxGeometry(beltLength + 0.5, 0.2, 0.15);

    const legPositions = [-7, -3.5, 0, 3.5, 7];
    legPositions.forEach((x) => {
      // Left leg
      const legL = new THREE.Mesh(legGeo, steelFrameMat);
      legL.position.set(x, 1.1, -(beltWidth / 2 + 0.25));
      legL.castShadow = true;
      this.conveyorGroup.add(legL);

      // Right leg
      const legR = new THREE.Mesh(legGeo, steelFrameMat);
      legR.position.set(x, 1.1, beltWidth / 2 + 0.25);
      legR.castShadow = true;
      this.conveyorGroup.add(legR);

      // Cross bar
      const cross = new THREE.Mesh(crossBarGeo, steelFrameMat);
      cross.position.set(x, 0.5, 0);
      this.conveyorGroup.add(cross);
    });

    // Side safety rails
    const railL = new THREE.Mesh(railGeo, steelFrameMat);
    railL.position.set(0, 2.3, -(beltWidth / 2 + 0.25));
    this.conveyorGroup.add(railL);

    const railR = new THREE.Mesh(railGeo, steelFrameMat);
    railR.position.set(0, 2.3, beltWidth / 2 + 0.25);
    this.conveyorGroup.add(railR);

    // 2. Head Roller (Drive Drum)
    const headRollerGeo = new THREE.CylinderGeometry(rollerRadius, rollerRadius, beltWidth + 0.1, 32);
    headRollerGeo.rotateX(Math.PI / 2);
    const headRollerMesh = new THREE.Mesh(headRollerGeo, rollerMat);
    headRollerMesh.position.set(beltLength / 2, 2.2, 0);
    headRollerMesh.castShadow = true;
    headRollerMesh.userData = {
      componentId: `${this.currentAssetId}-ROLLER-01`,
      name: "Head Drive Roller",
      type: "roller",
      health: 98,
      status: "Optimal"
    };
    this.conveyorGroup.add(headRollerMesh);
    this.interactiveObjects.push(headRollerMesh);

    // 3. Tail Roller (Tension Drum)
    const tailRollerMesh = new THREE.Mesh(headRollerGeo.clone(), rollerMat);
    tailRollerMesh.position.set(-beltLength / 2, 2.2, 0);
    tailRollerMesh.castShadow = true;
    tailRollerMesh.userData = {
      componentId: `${this.currentAssetId}-ROLLER-02`,
      name: "Tail Tension Roller",
      type: "roller",
      health: 94,
      status: "Optimal"
    };
    this.conveyorGroup.add(tailRollerMesh);
    this.interactiveObjects.push(tailRollerMesh);

    // 4. Carry Idlers (Troughing sets along the top)
    const idlerRadius = 0.25;
    const idlerGeo = new THREE.CylinderGeometry(idlerRadius, idlerRadius, beltWidth, 24);
    idlerGeo.rotateX(Math.PI / 2);

    [-4.5, -1.5, 1.5, 4.5].forEach((x, idx) => {
      const idler = new THREE.Mesh(idlerGeo, rollerMat);
      idler.position.set(x, 2.05, 0);
      idler.userData = {
        componentId: `${this.currentAssetId}-ROLLER-03`,
        name: `Carry Idler Set #${idx + 1}`,
        type: "idler",
        health: 91,
        status: "Optimal"
      };
      this.conveyorGroup.add(idler);
      this.interactiveObjects.push(idler);
    });

    // 5. Electric Drive Motor Assembly
    const motorGroup = new THREE.Group();
    const motorBodyGeo = new THREE.CylinderGeometry(0.7, 0.7, 1.6, 24);
    motorBodyGeo.rotateZ(Math.PI / 2);
    const motorBody = new THREE.Mesh(motorBodyGeo, motorMat);
    motorBody.castShadow = true;
    motorGroup.add(motorBody);

    // Motor Cooling Fan Cover
    const fanGeo = new THREE.CylinderGeometry(0.72, 0.72, 0.4, 24);
    fanGeo.rotateZ(Math.PI / 2);
    const fanCover = new THREE.Mesh(fanGeo, metalDark);
    fanCover.position.set(1.0, 0, 0);
    motorGroup.add(fanCover);

    // Gearbox reducer
    const gearboxGeo = new THREE.BoxGeometry(0.9, 1.2, 0.9);
    const gearbox = new THREE.Mesh(gearboxGeo, metalDark);
    gearbox.position.set(-1.1, 0, 0);
    gearbox.castShadow = true;
    motorGroup.add(gearbox);

    motorGroup.position.set(beltLength / 2, 2.2, beltWidth / 2 + 1.2);
    motorGroup.userData = {
      componentId: `${this.currentAssetId}-MOTOR-01`,
      name: "Primary Electric Drive Motor",
      type: "motor",
      health: 88,
      status: "Optimal"
    };
    this.conveyorGroup.add(motorGroup);
    // Add all children of motor group to interactive raycast list
    motorGroup.traverse((child) => {
      if (child.isMesh) {
        child.userData = motorGroup.userData;
        this.interactiveObjects.push(child);
      }
    });

    // 6. Belt Top & Bottom Surfaces
    // Create canvas texture with conveyor belt pattern
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(0, 0, 512, 512);

    // Subtle rubber grain lines
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 4;
    for (let y = 0; y < 512; y += 32) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(512, y);
      ctx.stroke();
    }
    // High-tech center indicator line
    ctx.strokeStyle = "rgba(6, 182, 212, 0.4)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, 256);
    ctx.lineTo(512, 256);
    ctx.stroke();

    const beltTexture = new THREE.CanvasTexture(canvas);
    beltTexture.wrapS = THREE.RepeatWrapping;
    beltTexture.wrapT = THREE.RepeatWrapping;
    beltTexture.repeat.set(8, 1);

    this.beltMaterial = new THREE.MeshStandardMaterial({
      map: beltTexture,
      roughness: 0.7,
      metalness: 0.1
    });

    const beltTopGeo = new THREE.PlaneGeometry(beltLength, beltWidth);
    beltTopGeo.rotateX(-Math.PI / 2);
    this.beltMesh = new THREE.Mesh(beltTopGeo, this.beltMaterial);
    this.beltMesh.position.set(0, 2.2 + rollerRadius, 0);
    this.beltMesh.receiveShadow = true;
    this.beltMesh.userData = {
      componentId: `${this.currentAssetId}-BELT`,
      name: "Heavy Duty Fabric Belt",
      type: "belt",
      health: 82,
      status: "Warning"
    };
    this.conveyorGroup.add(this.beltMesh);
    this.interactiveObjects.push(this.beltMesh);

    // Belt return strand (bottom)
    const beltBottomGeo = new THREE.PlaneGeometry(beltLength, beltWidth);
    beltBottomGeo.rotateX(Math.PI / 2);
    const beltBottom = new THREE.Mesh(beltBottomGeo, this.beltMaterial);
    beltBottom.position.set(0, 2.2 - rollerRadius, 0);
    this.conveyorGroup.add(beltBottom);

    // 7. Inlet Feed Hopper (Entry Chute)
    const hopperMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      metalness: 0.7,
      roughness: 0.3,
      side: THREE.DoubleSide
    });
    const hopperGeo = new THREE.CylinderGeometry(1.6, 1.0, 2.0, 4, 1, true);
    hopperGeo.rotateY(Math.PI / 4);
    const hopper = new THREE.Mesh(hopperGeo, hopperMat);
    hopper.position.set(-beltLength / 2 + 1.2, 4.0, 0);
    this.conveyorGroup.add(hopper);

    // 8. Vision AI Camera Sensor Pod (Mounted on top arch)
    const archMat = new THREE.MeshStandardMaterial({ color: 0x06b6d4, metalness: 0.8, roughness: 0.2 });
    const archGeo = new THREE.TorusGeometry(beltWidth / 2 + 0.4, 0.08, 8, 24, Math.PI);
    const arch = new THREE.Mesh(archGeo, archMat);
    arch.position.set(2, 2.8, 0);
    arch.rotateY(Math.PI / 2);
    this.conveyorGroup.add(arch);

    // Camera Pod
    const camPodGeo = new THREE.BoxGeometry(0.4, 0.3, 0.4);
    const camPod = new THREE.Mesh(camPodGeo, new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.9 }));
    camPod.position.set(2, 4.0, 0);
    this.conveyorGroup.add(camPod);

    // Camera Lens (Glowing cyan eye)
    const lensGeo = new THREE.SphereGeometry(0.12, 16, 16);
    const lensMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe });
    const lens = new THREE.Mesh(lensGeo, lensMat);
    lens.position.set(2, 3.82, 0);
    this.conveyorGroup.add(lens);

    // Camera Inspection Frustum (subtle scan cone)
    const coneGeo = new THREE.ConeGeometry(beltWidth * 0.6, 1.6, 4, 1, true);
    coneGeo.rotateX(Math.PI);
    const coneMat = new THREE.MeshBasicMaterial({
      color: 0x06b6d4,
      transparent: true,
      opacity: 0.15,
      side: THREE.DoubleSide
    });
    const scanCone = new THREE.Mesh(coneGeo, coneMat);
    scanCone.position.set(2, 3.0, 0);
    this.conveyorGroup.add(scanCone);

    // Build Defect Markers
    this.createDefectOverlays();

    this.scene.add(this.conveyorGroup);
  }

  createDefectOverlays() {
    // Clear old markers
    this.defectMarkers.forEach((m) => this.conveyorGroup.remove(m));
    this.defectMarkers = [];

    // Defect Marker 1: Longitudinal Crack (High Severity)
    const crackMarker = this.buildDefectMarker(
      "Cracking Defect #104",
      "High",
      0xef4444, // Red
      new THREE.Vector3(2.5, 2.85, 0.3)
    );
    this.defectMarkers.push(crackMarker);
    this.conveyorGroup.add(crackMarker);

    // Defect Marker 2: Edge Tear (Medium Severity)
    const tearMarker = this.buildDefectMarker(
      "Edge Tear #105",
      "Medium",
      0xf59e0b, // Amber
      new THREE.Vector3(-3.2, 2.85, -0.9)
    );
    this.defectMarkers.push(tearMarker);
    this.conveyorGroup.add(tearMarker);

    // Defect Marker 3: Roller Misalignment (Critical Severity)
    const misalignMarker = this.buildDefectMarker(
      "Roller Misalignment #108",
      "Critical",
      0xd946ef, // Neon Magenta
      new THREE.Vector3(-8.0, 2.85, 0)
    );
    this.defectMarkers.push(misalignMarker);
    this.conveyorGroup.add(misalignMarker);
  }

  buildDefectMarker(title, severity, hexColor, position) {
    const markerGroup = new THREE.Group();
    markerGroup.position.copy(position);

    // Pulsing diamond ring
    const ringGeo = new THREE.RingGeometry(0.25, 0.32, 16);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({
      color: hexColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    markerGroup.add(ring);

    // Vertical pointer line
    const lineGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.6);
    const lineMat = new THREE.MeshBasicMaterial({ color: hexColor });
    const line = new THREE.Mesh(lineGeo, lineMat);
    line.position.y = 0.3;
    markerGroup.add(line);

    // Diamond sphere beacon
    const beaconGeo = new THREE.OctahedronGeometry(0.18);
    const beacon = new THREE.Mesh(beaconGeo, lineMat);
    beacon.position.y = 0.6;
    markerGroup.add(beacon);

    markerGroup.userData = {
      isDefectMarker: true,
      title: title,
      severity: severity,
      color: hexColor
    };

    return markerGroup;
  }

  toggleOverlays(enabled) {
    this.overlaysEnabled = enabled;
    this.defectMarkers.forEach((m) => {
      m.visible = enabled;
    });
  }

  resetCamera() {
    if (this.controls) {
      this.controls.reset();
      this.camera.position.set(12, 8, 14);
      this.controls.target.set(0, 1, 0);
      this.controls.update();
    }
  }

  async loadAsset(assetId) {
    this.currentAssetId = assetId;
    const badge = document.getElementById("twin-asset-name");
    if (badge) badge.innerText = assetId;

    try {
      const res = await fetch(`/api/assets/${assetId}`);
      if (!res.ok) throw new Error("Failed to fetch asset");
      const data = await res.json();
      this.components = data.components || [];

      // Update Health score in UI
      const healthEl = document.getElementById("twin-asset-health");
      if (healthEl) {
        healthEl.innerText = `${Math.round(data.health_score)}%`;
        healthEl.className = `stat-badge ${data.health_score > 85 ? "good" : data.health_score > 70 ? "warn" : "critical"}`;
      }

      // Populate component list in twin sidebar
      this.renderComponentList();
    } catch (err) {
      console.warn("[Twin] Could not load asset details:", err);
    }
  }

  renderComponentList() {
    const listEl = document.getElementById("twin-components-list");
    if (!listEl) return;

    if (this.components.length === 0) {
      listEl.innerHTML = `<div class="p-3 text-muted small">No components mapped.</div>`;
      return;
    }

    listEl.innerHTML = this.components
      .map(
        (c) => `
        <div class="twin-comp-item ${this.selectedComponent?.component_id === c.component_id ? "active" : ""}" 
             onclick="window.twin.selectComponentById('${c.component_id}')">
          <div class="d-flex justify-content-between align-items-center">
            <strong class="text-truncate" style="max-width: 140px;">${c.name}</strong>
            <span class="badge ${c.health_score > 85 ? "bg-success" : c.health_score > 70 ? "bg-warning" : "bg-danger"}">${Math.round(c.health_score)}%</span>
          </div>
          <small class="text-muted text-uppercase">${c.component_type} &bull; ${c.status}</small>
        </div>`
      )
      .join("");
  }

  selectComponentById(componentId) {
    const comp = this.components.find((c) => c.component_id === componentId);
    if (!comp) return;

    this.selectedComponent = comp;
    this.renderComponentList();
    this.showComponentDetails(comp);

    // Visual camera focus animation
    if (comp.component_type === "motor") {
      this.focusCamera(new THREE.Vector3(8, 2.2, 2.5));
    } else if (comp.component_type === "roller") {
      this.focusCamera(new THREE.Vector3(8, 2.2, 0));
    } else {
      this.focusCamera(new THREE.Vector3(0, 2.5, 0));
    }
  }

  focusCamera(targetPos) {
    if (this.controls) {
      this.controls.target.copy(targetPos);
      this.controls.update();
    }
  }

  showComponentDetails(comp) {
    const panel = document.getElementById("twin-detail-panel");
    if (!panel) return;

    panel.innerHTML = `
      <div class="card-custom p-3 animate-fade-in">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="mb-0 text-cyan"><i class="bi bi-cpu me-1"></i>${comp.name}</h6>
          <span class="badge ${comp.health_score > 85 ? "bg-success" : comp.health_score > 70 ? "bg-warning" : "bg-danger"}">${Math.round(comp.health_score)}% Health</span>
        </div>
        <div class="small text-muted mb-2">ID: <code>${comp.component_id}</code> | Type: <strong>${comp.component_type.toUpperCase()}</strong></div>
        
        <div class="row g-2 text-center my-2">
          <div class="col-6">
            <div class="p-2 bg-dark rounded border border-secondary">
              <div class="small text-muted">Operating State</div>
              <strong class="text-success">${comp.status}</strong>
            </div>
          </div>
          <div class="col-6">
            <div class="p-2 bg-dark rounded border border-secondary">
              <div class="small text-muted">Vibration RMS</div>
              <strong class="text-info">2.1 mm/s</strong>
            </div>
          </div>
        </div>

        <div class="d-flex gap-2 mt-3">
          <button class="btn btn-sm btn-outline-info flex-grow-1" onclick="window.twin.askCopilotAbout('${comp.component_id}', '${comp.name}')">
            <i class="bi bi-robot me-1"></i> Ask AI Copilot
          </button>
          <button class="btn btn-sm btn-outline-warning flex-grow-1" onclick="window.twin.createMaintenanceTask('${comp.component_id}', '${comp.name}')">
            <i class="bi bi-wrench me-1"></i> Schedule Maint
          </button>
        </div>
      </div>
    `;
  }

  askCopilotAbout(compId, name) {
    // Open copilot drawer and query
    if (window.vgCopilot) {
      window.vgCopilot.openWithPrompt(`Give me an operational summary and health assessment for component ${name} (${compId}).`);
    }
  }

  createMaintenanceTask(compId, name) {
    // Populate existing maintenance modal
    const taskTitleInput = document.getElementById("edit-task-title");
    if (taskTitleInput) {
      taskTitleInput.value = `Routine Inspection & Servicing: ${name}`;
    }
    const modalEl = document.getElementById("editTaskModal");
    if (modalEl && typeof bootstrap !== "undefined") {
      const modal = new bootstrap.Modal(modalEl);
      modal.show();
    }
  }

  handleLiveTelemetry(data) {
    if (data.channel === "belt_speed" && data.value !== undefined) {
      this.speed = data.value;
      this.isRunning = this.speed > 0.1;
    }
  }

  setupEventListeners() {
    window.addEventListener("resize", () => this.onWindowResize());

    const dom = this.renderer.domElement;
    dom.addEventListener("pointermove", (e) => this.onPointerMove(e));
    dom.addEventListener("pointerdown", (e) => this.onPointerDown(e));
  }

  onWindowResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  onPointerMove(e) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.interactiveObjects, true);

    if (intersects.length > 0) {
      this.renderer.domElement.style.cursor = "pointer";
    } else {
      this.renderer.domElement.style.cursor = "default";
    }
  }

  onPointerDown(e) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.interactiveObjects, true);

    if (intersects.length > 0) {
      let hit = intersects[0].object;
      while (hit && !hit.userData?.componentId && hit.parent) {
        hit = hit.parent;
      }
      if (hit && hit.userData?.componentId) {
        this.selectComponentById(hit.userData.componentId);
      }
    }
  }

  animate() {
    this.animationFrameId = requestAnimationFrame(() => this.animate());

    // Update controls
    if (this.controls) this.controls.update();

    // Scroll belt texture if conveyor running
    if (this.isRunning && this.beltMaterial && this.beltMaterial.map) {
      this.beltOffset += this.speed * 0.005;
      this.beltMaterial.map.offset.x = this.beltOffset;
    }

    // Animate defect marker pulsing
    if (this.overlaysEnabled && this.defectMarkers.length > 0) {
      const time = performance.now() * 0.003;
      this.defectMarkers.forEach((m) => {
        const beacon = m.children[2];
        if (beacon) {
          beacon.rotation.y = time;
          beacon.scale.setScalar(1.0 + 0.15 * Math.sin(time * 3));
        }
      });
    }

    this.renderer.render(this.scene, this.camera);
  }

  destroy() {
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
    if (this.renderer) this.renderer.dispose();
  }
}

// Global initialization helper
window.initConveyorDigitalTwin = function (containerId) {
  if (!window.twin) {
    window.twin = new ConveyorDigitalTwin(containerId);
    window.twin.init();
  }
  return window.twin;
};
