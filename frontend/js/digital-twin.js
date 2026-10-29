/**
 * VisionGuard AI 2.0 - 3D Industrial Digital Twin
 * Three.js interactive 3D conveyor system with mathematically aligned geometry,
 * continuous closed-loop belt wrapping, 3-roll troughing idlers, shaft-mounted motor drive,
 * inspection gantry, camera presets, and interactive diagnostic inspector.
 */

class ConveyorDigitalTwin {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentAssetId = "CONV-01";
    this.components = [];
    this.selectedComponent = null;
    this.hoveredObject = null;
    this.overlaysEnabled = true;
    this.isRunning = true;
    this.speed = 1.8; // m/s
    this.beltOffset = 0;

    // Three.js core instances
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.raycaster = null;
    this.mouse = null;
    this.animationFrameId = null;

    // Camera animation state
    this.isCameraAnimating = false;
    this.camTargetPos = new THREE.Vector3();
    this.controlsTargetPos = new THREE.Vector3();
    this.camAnimSpeed = 0.08;

    // Mesh groups
    this.conveyorGroup = null;
    this.interactiveObjects = [];
    this.defectMarkers = [];
    this.beltMaterials = [];
    this.scannerLight = null;
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
    const height = this.container.clientHeight || 550;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x060913); // Deep cyber-industrial slate
    this.scene.fog = new THREE.FogExp2(0x060913, 0.015);

    // Camera positioned with optimal isometric perspective
    this.camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 1000);
    this.camera.position.set(13.5, 7.5, 12.5);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance"
    });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Clear previous elements
    this.container.innerHTML = "";
    this.container.appendChild(this.renderer.domElement);

    // OrbitControls centered precisely on conveyor physical center
    if (typeof THREE.OrbitControls !== "undefined") {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.06;
      this.controls.maxPolarAngle = Math.PI / 2 - 0.02; // Prevent camera going below floor
      this.controls.minDistance = 3;
      this.controls.maxDistance = 45;
      this.controls.target.set(0, 1.8, 0); // Center of conveyor elevation
      this.controls.update();
    }

    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    // High-tech floor grid
    const grid = new THREE.GridHelper(36, 36, 0x00f2fe, 0x152238);
    grid.position.y = 0.0;
    this.scene.add(grid);

    // Safety demarcation boundary line on floor
    const boundaryGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-10, 0.01, -2.5),
      new THREE.Vector3(10, 0.01, -2.5),
      new THREE.Vector3(10, 0.01, 2.5),
      new THREE.Vector3(-10, 0.01, 2.5),
      new THREE.Vector3(-10, 0.01, -2.5),
    ]);
    const boundaryMat = new THREE.LineDashedMaterial({
      color: 0xf59e0b,
      dashSize: 0.6,
      gapSize: 0.3,
      linewidth: 2
    });
    const boundaryLine = new THREE.Line(boundaryGeo, boundaryMat);
    boundaryLine.computeLineDistances();
    this.scene.add(boundaryLine);
  }

  setupLighting() {
    // Ambient light
    const ambientLight = new THREE.AmbientLight(0x1a2639, 1.4);
    this.scene.add(ambientLight);

    // Main Key Light
    const keyLight = new THREE.DirectionalLight(0xf0f9ff, 1.9);
    keyLight.position.set(12, 18, 10);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 0.5;
    keyLight.shadow.camera.far = 40;
    keyLight.shadow.bias = -0.0005;
    this.scene.add(keyLight);

    // Cyan Industrial Rim Accent Light (opposite side)
    const cyanLight = new THREE.DirectionalLight(0x00f2fe, 1.4);
    cyanLight.position.set(-14, 10, -12);
    this.scene.add(cyanLight);

    // Subtle blue fill light from underneath
    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.6);
    fillLight.position.set(0, -5, 0);
    this.scene.add(fillLight);
  }

  buildConveyorModel() {
    this.conveyorGroup = new THREE.Group();
    this.interactiveObjects = [];
    this.beltMaterials = [];

    // Core Geometry Dimensions
    const L = 16.0;         // Conveyor length (m)
    const W = 2.2;          // Belt width (m)
    const R = 0.55;         // Pulley radius (m)
    const H = 1.8;          // Centerline elevation (m)
    const topY = H + R;     // 2.35m
    const botY = H - R;     // 1.25m
    const halfL = L / 2;    // 8.0m

    // Shared Materials
    const metalDark = new THREE.MeshStandardMaterial({
      color: 0x1e2638,
      metalness: 0.75,
      roughness: 0.3
    });

    const steelBeamMat = new THREE.MeshStandardMaterial({
      color: 0x2b3952,
      metalness: 0.65,
      roughness: 0.35
    });

    const chromeMat = new THREE.MeshStandardMaterial({
      color: 0xcfd8dc,
      metalness: 0.95,
      roughness: 0.15
    });

    const motorPaintMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7, // Vivid electric cyan-blue industrial motor
      metalness: 0.45,
      roughness: 0.3
    });

    // ─────────────────────────────────────────────────────────────
    // 1. Structural Steel Frame & Trestles (Floor-Mounted)
    // ─────────────────────────────────────────────────────────────
    // Longitudinal side C-channels
    const channelGeo = new THREE.BoxGeometry(L + 1.2, 0.28, 0.12);
    const channelLeft = new THREE.Mesh(channelGeo, steelBeamMat);
    channelLeft.position.set(0, H, -(W / 2 + 0.18));
    channelLeft.castShadow = true;
    channelLeft.receiveShadow = true;
    this.conveyorGroup.add(channelLeft);

    const channelRight = new THREE.Mesh(channelGeo, steelBeamMat);
    channelRight.position.set(0, H, W / 2 + 0.18);
    channelRight.castShadow = true;
    channelRight.receiveShadow = true;
    this.conveyorGroup.add(channelRight);

    // Cross beams connecting channels
    const crossBeamGeo = new THREE.BoxGeometry(0.12, 0.2, W + 0.45);
    [-7.0, -4.5, -2.0, 0.5, 3.0, 5.5, 7.5].forEach((x) => {
      const cross = new THREE.Mesh(crossBeamGeo, steelBeamMat);
      cross.position.set(x, H - 0.14, 0);
      cross.castShadow = true;
      this.conveyorGroup.add(cross);
    });

    // Structural A-Frame Support Legs with Anchor Baseplates
    const legGeo = new THREE.BoxGeometry(0.2, H - 0.14, 0.2);
    const baseplateGeo = new THREE.BoxGeometry(0.5, 0.05, 0.5);
    const legXPositions = [-6.5, -2.0, 2.5, 7.0];

    legXPositions.forEach((x) => {
      // Left leg & baseplate
      const legL = new THREE.Mesh(legGeo, steelBeamMat);
      legL.position.set(x, (H - 0.14) / 2, -(W / 2 + 0.18));
      legL.castShadow = true;
      this.conveyorGroup.add(legL);

      const baseL = new THREE.Mesh(baseplateGeo, metalDark);
      baseL.position.set(x, 0.025, -(W / 2 + 0.18));
      this.conveyorGroup.add(baseL);

      // Right leg & baseplate
      const legR = new THREE.Mesh(legGeo, steelBeamMat);
      legR.position.set(x, (H - 0.14) / 2, W / 2 + 0.18);
      legR.castShadow = true;
      this.conveyorGroup.add(legR);

      const baseR = new THREE.Mesh(baseplateGeo, metalDark);
      baseR.position.set(x, 0.025, W / 2 + 0.18);
      this.conveyorGroup.add(baseR);
    });

    // Tag entire frame for component selection
    const frameData = {
      componentId: `${this.currentAssetId}-FRAME`,
      name: "Modular Steel Truss Frame",
      type: "frame",
      health: 96,
      status: "Rigid & Anchored"
    };
    channelLeft.userData = frameData;
    channelRight.userData = frameData;
    this.interactiveObjects.push(channelLeft, channelRight);

    // ─────────────────────────────────────────────────────────────
    // 2. Head Drive Pulley (x = +8.0)
    // ─────────────────────────────────────────────────────────────
    const headPulleyGeo = new THREE.CylinderGeometry(R, R, W + 0.1, 36);
    headPulleyGeo.rotateX(Math.PI / 2);
    const headPulleyMesh = new THREE.Mesh(headPulleyGeo, chromeMat);
    headPulleyMesh.position.set(halfL, H, 0);
    headPulleyMesh.castShadow = true;
    headPulleyMesh.userData = {
      componentId: `${this.currentAssetId}-ROLLER-01`,
      name: "Head Drive Drum Pulley",
      type: "roller",
      health: 98,
      status: "Optimal"
    };
    this.conveyorGroup.add(headPulleyMesh);
    this.interactiveObjects.push(headPulleyMesh);

    // Pillow block bearings on both sides
    const bearingGeo = new THREE.BoxGeometry(0.35, 0.4, 0.2);
    const bearingL = new THREE.Mesh(bearingGeo, metalDark);
    bearingL.position.set(halfL, H, -(W / 2 + 0.22));
    this.conveyorGroup.add(bearingL);

    const bearingR = new THREE.Mesh(bearingGeo, metalDark);
    bearingR.position.set(halfL, H, W / 2 + 0.22);
    this.conveyorGroup.add(bearingR);

    // Drive shaft extending to motor side
    const shaftGeo = new THREE.CylinderGeometry(0.1, 0.1, 1.2, 24);
    shaftGeo.rotateX(Math.PI / 2);
    const shaft = new THREE.Mesh(shaftGeo, chromeMat);
    shaft.position.set(halfL, H, W / 2 + 0.6);
    this.conveyorGroup.add(shaft);

    // ─────────────────────────────────────────────────────────────
    // 3. Tail Tension Pulley (x = -8.0)
    // ─────────────────────────────────────────────────────────────
    const tailPulleyMesh = new THREE.Mesh(headPulleyGeo.clone(), chromeMat);
    tailPulleyMesh.position.set(-halfL, H, 0);
    tailPulleyMesh.castShadow = true;
    tailPulleyMesh.userData = {
      componentId: `${this.currentAssetId}-ROLLER-02`,
      name: "Tail Tension Drum Pulley",
      type: "roller",
      health: 94,
      status: "Optimal"
    };
    this.conveyorGroup.add(tailPulleyMesh);
    this.interactiveObjects.push(tailPulleyMesh);

    const tailBearingL = new THREE.Mesh(bearingGeo, metalDark);
    tailBearingL.position.set(-halfL, H, -(W / 2 + 0.22));
    this.conveyorGroup.add(tailBearingL);

    const tailBearingR = new THREE.Mesh(bearingGeo, metalDark);
    tailBearingR.position.set(-halfL, H, W / 2 + 0.22);
    this.conveyorGroup.add(tailBearingR);

    // ─────────────────────────────────────────────────────────────
    // 4. Electric Drive Motor & Helical-Bevel Gearbox Assembly
    // ─────────────────────────────────────────────────────────────
    const motorGroup = new THREE.Group();

    // Shaft-mounted Gearbox Reducer
    const gearboxGeo = new THREE.BoxGeometry(0.85, 1.1, 0.75);
    const gearbox = new THREE.Mesh(gearboxGeo, metalDark);
    gearbox.position.set(halfL, H, W / 2 + 0.95);
    gearbox.castShadow = true;
    motorGroup.add(gearbox);

    // Electric Motor Stator Housing with Cooling Fins
    const motorStatorGeo = new THREE.CylinderGeometry(0.48, 0.48, 1.25, 24);
    motorStatorGeo.rotateZ(Math.PI / 2);
    const motorStator = new THREE.Mesh(motorStatorGeo, motorPaintMat);
    motorStator.position.set(halfL - 0.9, H + 0.1, W / 2 + 0.95);
    motorStator.castShadow = true;
    motorGroup.add(motorStator);

    // Motor Terminal Box (top)
    const termBoxGeo = new THREE.BoxGeometry(0.3, 0.22, 0.26);
    const termBox = new THREE.Mesh(termBoxGeo, metalDark);
    termBox.position.set(halfL - 0.9, H + 0.65, W / 2 + 0.95);
    motorGroup.add(termBox);

    // Motor Rear Fan Cowl
    const fanCowlGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.35, 24);
    fanCowlGeo.rotateZ(Math.PI / 2);
    const fanCowl = new THREE.Mesh(fanCowlGeo, metalDark);
    fanCowl.position.set(halfL - 1.6, H + 0.1, W / 2 + 0.95);
    motorGroup.add(fanCowl);

    // Torque Reaction Arm anchoring gearbox to conveyor stringer
    const torqueArmGeo = new THREE.BoxGeometry(0.12, 0.7, 0.25);
    const torqueArm = new THREE.Mesh(torqueArmGeo, steelBeamMat);
    torqueArm.position.set(halfL, H - 0.55, W / 2 + 0.55);
    motorGroup.add(torqueArm);

    motorGroup.userData = {
      componentId: `${this.currentAssetId}-MOTOR-01`,
      name: "High-Torque Induction Drive Motor (45kW)",
      type: "motor",
      health: 88,
      status: "Running Smoothly"
    };

    this.conveyorGroup.add(motorGroup);
    motorGroup.traverse((child) => {
      if (child.isMesh) {
        child.userData = motorGroup.userData;
        this.interactiveObjects.push(child);
      }
    });

    // ─────────────────────────────────────────────────────────────
    // 5. 3-Roll Troughing Idlers & Return Idlers
    // ─────────────────────────────────────────────────────────────
    const idlerRadius = 0.12;
    const centerRollLen = W * 0.44; // Center roller
    const wingRollLen = W * 0.34;   // Angled wing rollers

    const idlerCenterGeo = new THREE.CylinderGeometry(idlerRadius, idlerRadius, centerRollLen, 16);
    idlerCenterGeo.rotateX(Math.PI / 2);

    const idlerWingGeo = new THREE.CylinderGeometry(idlerRadius, idlerRadius, wingRollLen, 16);
    idlerWingGeo.rotateX(Math.PI / 2);

    const troughStations = [-5.5, -3.0, -0.5, 2.0, 4.5];
    troughStations.forEach((x, idx) => {
      const stationGroup = new THREE.Group();

      // Center horizontal roll
      const centerRoll = new THREE.Mesh(idlerCenterGeo, chromeMat);
      centerRoll.position.set(x, topY - idlerRadius - 0.05, 0);
      stationGroup.add(centerRoll);

      // Left wing roll (tilted 22 degrees upwards)
      const leftWing = new THREE.Mesh(idlerWingGeo, chromeMat);
      leftWing.position.set(x, topY - idlerRadius + 0.04, -(centerRollLen / 2 + wingRollLen / 2 * 0.9));
      leftWing.rotation.x = -Math.PI / 8;
      stationGroup.add(leftWing);

      // Right wing roll (tilted 22 degrees upwards)
      const rightWing = new THREE.Mesh(idlerWingGeo, chromeMat);
      rightWing.position.set(x, topY - idlerRadius + 0.04, centerRollLen / 2 + wingRollLen / 2 * 0.9);
      rightWing.rotation.x = Math.PI / 8;
      stationGroup.add(rightWing);

      // Bracket base
      const bracketGeo = new THREE.BoxGeometry(0.1, 0.12, W + 0.2);
      const bracket = new THREE.Mesh(bracketGeo, metalDark);
      bracket.position.set(x, topY - idlerRadius - 0.15, 0);
      stationGroup.add(bracket);

      stationGroup.userData = {
        componentId: `${this.currentAssetId}-ROLLER-03`,
        name: `Carry Idler Trough Set #${idx + 1}`,
        type: "idler",
        health: 91,
        status: "Free Rotating"
      };

      this.conveyorGroup.add(stationGroup);
      stationGroup.traverse((c) => {
        if (c.isMesh) {
          c.userData = stationGroup.userData;
          this.interactiveObjects.push(c);
        }
      });
    });

    // V-Return Idlers on the return strand underneath
    const returnRollGeo = new THREE.CylinderGeometry(0.1, 0.1, W * 0.9, 16);
    returnRollGeo.rotateX(Math.PI / 2);
    [-4.0, 0, 4.0].forEach((x) => {
      const returnRoll = new THREE.Mesh(returnRollGeo, chromeMat);
      returnRoll.position.set(x, botY + 0.14, 0);
      this.conveyorGroup.add(returnRoll);
    });

    // ─────────────────────────────────────────────────────────────
    // 6. Seamless Continuous Closed-Loop Conveyor Belt
    // ─────────────────────────────────────────────────────────────
    const beltTex = this.createBeltTexture();
    const beltMat = new THREE.MeshStandardMaterial({
      map: beltTex,
      roughness: 0.8,
      metalness: 0.1,
      side: THREE.DoubleSide
    });
    this.beltMaterials.push(beltMat);

    // Top carrying strand (from -halfL to +halfL)
    const topStrandGeo = new THREE.PlaneGeometry(L, W, 32, 1);
    topStrandGeo.rotateX(-Math.PI / 2);
    const topStrand = new THREE.Mesh(topStrandGeo, beltMat);
    topStrand.position.set(0, topY, 0);
    topStrand.receiveShadow = true;
    this.conveyorGroup.add(topStrand);

    // Bottom return strand (from +halfL back to -halfL)
    const botStrandGeo = new THREE.PlaneGeometry(L, W, 32, 1);
    botStrandGeo.rotateX(Math.PI / 2);
    const botStrand = new THREE.Mesh(botStrandGeo, beltMat);
    botStrand.position.set(0, botY, 0);
    botStrand.receiveShadow = true;
    this.conveyorGroup.add(botStrand);

    // Head Pulley Wrap: Curved half-cylinder connecting topY into botY at x = +halfL
    const headWrapGeo = new THREE.CylinderGeometry(R, R, W, 32, 1, true, -Math.PI / 2, Math.PI);
    headWrapGeo.rotateX(Math.PI / 2);
    const headWrap = new THREE.Mesh(headWrapGeo, beltMat);
    headWrap.position.set(halfL, H, 0);
    headWrap.castShadow = true;
    this.conveyorGroup.add(headWrap);

    // Tail Pulley Wrap: Curved half-cylinder connecting botY back to topY at x = -halfL
    const tailWrapGeo = new THREE.CylinderGeometry(R, R, W, 32, 1, true, Math.PI / 2, Math.PI);
    tailWrapGeo.rotateX(Math.PI / 2);
    const tailWrap = new THREE.Mesh(tailWrapGeo, beltMat);
    tailWrap.position.set(-halfL, H, 0);
    tailWrap.castShadow = true;
    this.conveyorGroup.add(tailWrap);

    // Tag all belt segments
    const beltData = {
      componentId: `${this.currentAssetId}-BELT`,
      name: "Heavy-Duty Steel Cord Conveyor Belt (EP-400)",
      type: "belt",
      health: 82,
      status: "Surface Wear Detected"
    };
    [topStrand, botStrand, headWrap, tailWrap].forEach((m) => {
      m.userData = beltData;
      this.interactiveObjects.push(m);
    });

    // ─────────────────────────────────────────────────────────────
    // 7. Material Feed Hopper (Tail end) & Discharge Chute (Head end)
    // ─────────────────────────────────────────────────────────────
    // Feed Hopper at x = -7.0
    const hopperMat = new THREE.MeshStandardMaterial({
      color: 0x182236,
      metalness: 0.7,
      roughness: 0.35,
      side: THREE.DoubleSide
    });
    const hopperGeo = new THREE.CylinderGeometry(1.6, 1.05, 1.8, 4, 1, true);
    hopperGeo.rotateY(Math.PI / 4);
    const hopper = new THREE.Mesh(hopperGeo, hopperMat);
    hopper.position.set(-halfL + 1.2, topY + 1.4, 0);
    this.conveyorGroup.add(hopper);

    // Rubber Skirtboards along the loading zone
    const skirtGeo = new THREE.BoxGeometry(2.8, 0.45, 0.05);
    const skirtL = new THREE.Mesh(skirtGeo, metalDark);
    skirtL.position.set(-halfL + 1.4, topY + 0.25, -(W / 2 - 0.1));
    this.conveyorGroup.add(skirtL);

    const skirtR = new THREE.Mesh(skirtGeo, metalDark);
    skirtR.position.set(-halfL + 1.4, topY + 0.25, W / 2 - 0.1);
    this.conveyorGroup.add(skirtR);

    // Head Discharge Chute Hood at x = +8.2
    const hoodGeo = new THREE.BoxGeometry(1.4, 1.8, W + 0.3);
    const hood = new THREE.Mesh(hoodGeo, hopperMat);
    hood.position.set(halfL + 0.5, H - 0.2, 0);
    this.conveyorGroup.add(hood);

    // ─────────────────────────────────────────────────────────────
    // 8. VisionGuard AI Optical Inspection Arch (x = 1.0)
    // ─────────────────────────────────────────────────────────────
    const gantryGroup = new THREE.Group();

    // Dual-column gantry arch spanning conveyor
    const gantryArchGeo = new THREE.TorusGeometry(W / 2 + 0.45, 0.07, 12, 32, Math.PI);
    gantryArchGeo.rotateY(Math.PI / 2);
    const gantryArchMat = new THREE.MeshStandardMaterial({
      color: 0x00f2fe,
      metalness: 0.85,
      roughness: 0.2,
      emissive: 0x00f2fe,
      emissiveIntensity: 0.2
    });
    const gantryArch = new THREE.Mesh(gantryArchGeo, gantryArchMat);
    gantryArch.position.set(1.0, topY + 0.5, 0);
    gantryGroup.add(gantryArch);

    // Central Vision AI Camera Pod
    const camPodGeo = new THREE.BoxGeometry(0.5, 0.35, 0.45);
    const camPodMat = new THREE.MeshStandardMaterial({
      color: 0x070c18,
      metalness: 0.9,
      roughness: 0.2
    });
    const camPod = new THREE.Mesh(camPodGeo, camPodMat);
    camPod.position.set(1.0, topY + 1.6, 0);
    gantryGroup.add(camPod);

    // Glowing Optical Lens
    const lensGeo = new THREE.SphereGeometry(0.12, 24, 24);
    const lensMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe });
    const lens = new THREE.Mesh(lensGeo, lensMat);
    lens.position.set(1.0, topY + 1.4, 0);
    gantryGroup.add(lens);

    // Dual Line-Laser Triangulation Projectors
    const laserMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    const laserGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.2, 16);
    laserGeo.rotateX(Math.PI / 2);

    const laser1 = new THREE.Mesh(laserGeo, laserMat);
    laser1.position.set(0.9, topY + 1.5, -0.35);
    gantryGroup.add(laser1);

    const laser2 = new THREE.Mesh(laserGeo, laserMat);
    laser2.position.set(0.9, topY + 1.5, 0.35);
    gantryGroup.add(laser2);

    // Red Laser Scan Line across the belt
    const laserLineGeo = new THREE.PlaneGeometry(0.04, W);
    laserLineGeo.rotateX(-Math.PI / 2);
    const laserLineMat = new THREE.MeshBasicMaterial({
      color: 0xef4444,
      transparent: true,
      opacity: 0.85
    });
    const laserLine = new THREE.Mesh(laserLineGeo, laserLineMat);
    laserLine.position.set(1.0, topY + 0.01, 0);
    gantryGroup.add(laserLine);

    // Subtle Cyan Light Pyramid (Visual Inspection Scan Volume)
    const coneGeo = new THREE.ConeGeometry(W * 0.55, 1.4, 4, 1, true);
    coneGeo.rotateX(Math.PI);
    const coneMat = new THREE.MeshBasicMaterial({
      color: 0x00f2fe,
      transparent: true,
      opacity: 0.12,
      side: THREE.DoubleSide
    });
    const scanCone = new THREE.Mesh(coneGeo, coneMat);
    scanCone.position.set(1.0, topY + 0.7, 0);
    gantryGroup.add(scanCone);

    gantryGroup.userData = {
      componentId: `${this.currentAssetId}-AI-GANTRY`,
      name: "VisionGuard AI High-Speed Optical Gantry",
      type: "sensor",
      health: 99,
      status: "Active Scanning (120 FPS)"
    };
    this.conveyorGroup.add(gantryGroup);
    gantryGroup.traverse((c) => {
      if (c.isMesh) {
        c.userData = gantryGroup.userData;
        this.interactiveObjects.push(c);
      }
    });

    // Build 3D Defect Overlay Beacons
    this.createDefectOverlays(topY);

    this.scene.add(this.conveyorGroup);
  }

  createBeltTexture() {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");

    // Base rubber color
    ctx.fillStyle = "#141c2c";
    ctx.fillRect(0, 0, 512, 512);

    // Rubber vulcanized texture grain lines
    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 3;
    for (let y = 0; y < 512; y += 16) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(512, y);
      ctx.stroke();
    }

    // Heavy lateral grip ridges
    ctx.strokeStyle = "#25334c";
    ctx.lineWidth = 4;
    for (let y = 0; y < 512; y += 64) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(512, y);
      ctx.stroke();
    }

    // High-tech center alignment tracking line
    ctx.strokeStyle = "rgba(0, 242, 254, 0.4)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, 256);
    ctx.lineTo(512, 256);
    ctx.stroke();

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(8, 1);
    return texture;
  }

  createDefectOverlays(topY) {
    this.defectMarkers.forEach((m) => this.conveyorGroup.remove(m));
    this.defectMarkers = [];

    // Defect 1: Longitudinal Crack (Critical)
    const crackMarker = this.buildDefectMarker(
      "Cracking Defect #1",
      "Critical",
      0xef4444,
      new THREE.Vector3(2.8, topY, 0.2)
    );
    this.defectMarkers.push(crackMarker);
    this.conveyorGroup.add(crackMarker);

    // Defect 2: Edge Tear (High)
    const tearMarker = this.buildDefectMarker(
      "Edge Tear #2",
      "High",
      0xf97316,
      new THREE.Vector3(-2.8, topY, -0.9)
    );
    this.defectMarkers.push(tearMarker);
    this.conveyorGroup.add(tearMarker);

    // Defect 3: Roller Misalignment (Medium)
    const misalignMarker = this.buildDefectMarker(
      "Tracking Misalignment #3",
      "Medium",
      0xf59e0b,
      new THREE.Vector3(-6.2, topY, 0.7)
    );
    this.defectMarkers.push(misalignMarker);
    this.conveyorGroup.add(misalignMarker);
  }

  buildDefectMarker(title, severity, hexColor, position) {
    const group = new THREE.Group();
    group.position.copy(position);

    // Ground target ring on belt surface
    const ringGeo = new THREE.RingGeometry(0.25, 0.34, 24);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({
      color: hexColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.95
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    group.add(ring);

    // Vertical beacon pointer stem
    const stemGeo = new THREE.CylinderGeometry(0.025, 0.025, 0.8, 16);
    const stemMat = new THREE.MeshBasicMaterial({ color: hexColor });
    const stem = new THREE.Mesh(stemGeo, stemMat);
    stem.position.y = 0.4;
    group.add(stem);

    // Pulsing diamond beacon
    const beaconGeo = new THREE.OctahedronGeometry(0.2);
    const beacon = new THREE.Mesh(beaconGeo, stemMat);
    beacon.position.y = 0.8;
    group.add(beacon);

    group.userData = {
      isDefectMarker: true,
      title: title,
      severity: severity
    };

    return group;
  }

  toggleOverlays(enabled) {
    this.overlaysEnabled = enabled;
    this.defectMarkers.forEach((m) => {
      m.visible = enabled;
    });
  }

  // Camera Presets with Smooth Gliding Transition
  setCameraView(viewName) {
    const H = 1.8;
    let targetCam = new THREE.Vector3();
    let targetFocus = new THREE.Vector3(0, H, 0);

    switch (viewName) {
      case "iso":
        targetCam.set(13.5, 7.5, 12.5);
        targetFocus.set(0, H, 0);
        break;
      case "side":
        targetCam.set(0.0, 2.5, 16.5);
        targetFocus.set(0, H, 0);
        break;
      case "top":
        targetCam.set(0.01, 16.5, 0.01);
        targetFocus.set(0, H, 0);
        break;
      case "motor":
        targetCam.set(10.5, 3.4, 4.6);
        targetFocus.set(8.0, H + 0.1, 1.2);
        break;
      case "scanner":
        targetCam.set(3.2, 3.8, 3.2);
        targetFocus.set(1.0, 2.2, 0);
        break;
      default:
        targetCam.set(13.5, 7.5, 12.5);
        targetFocus.set(0, H, 0);
    }

    this.animateCameraTo(targetCam, targetFocus);
  }

  animateCameraTo(pos, focus) {
    this.camTargetPos.copy(pos);
    this.controlsTargetPos.copy(focus);
    this.isCameraAnimating = true;
  }

  resetCamera() {
    this.setCameraView("iso");
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
        healthEl.innerText = `${Math.round(data.health_score)}% Health`;
        healthEl.className = `badge ${data.health_score > 85 ? "bg-success" : data.health_score > 70 ? "bg-warning" : "bg-danger"}`;
      }

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

    // Glide camera directly to selected component
    if (comp.component_type === "motor") {
      this.setCameraView("motor");
    } else if (comp.component_type === "roller") {
      this.animateCameraTo(new THREE.Vector3(10, 3.2, 4), new THREE.Vector3(8, 1.8, 0));
    } else if (comp.component_type === "sensor") {
      this.setCameraView("scanner");
    } else {
      this.animateCameraTo(new THREE.Vector3(0, 4.5, 5.5), new THREE.Vector3(0, 2.0, 0));
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
              <strong class="text-info">1.8 mm/s</strong>
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
    if (window.vgCopilot) {
      window.vgCopilot.openWithPrompt(`Give me an operational summary and health assessment for component ${name} (${compId}).`);
    }
  }

  createMaintenanceTask(compId, name) {
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
      this.isRunning = this.speed > 0.05;
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

    // Smooth camera gliding interpolation
    if (this.isCameraAnimating) {
      this.camera.position.lerp(this.camTargetPos, this.camAnimSpeed);
      if (this.controls) {
        this.controls.target.lerp(this.controlsTargetPos, this.camAnimSpeed);
        this.controls.update();
      }
      if (
        this.camera.position.distanceTo(this.camTargetPos) < 0.05 &&
        this.controls.target.distanceTo(this.controlsTargetPos) < 0.05
      ) {
        this.camera.position.copy(this.camTargetPos);
        this.controls.target.copy(this.controlsTargetPos);
        this.isCameraAnimating = false;
      }
    } else if (this.controls) {
      this.controls.update();
    }

    // Belt scroll motion
    if (this.isRunning && this.beltMaterials.length > 0) {
      this.beltOffset += this.speed * 0.0035;
      this.beltMaterials.forEach((m) => {
        if (m.map) m.map.offset.x = this.beltOffset;
      });
    }

    // Pulse defect markers
    if (this.overlaysEnabled && this.defectMarkers.length > 0) {
      const time = performance.now() * 0.003;
      this.defectMarkers.forEach((m) => {
        const beacon = m.children[2];
        if (beacon) {
          beacon.rotation.y = time * 2;
          beacon.scale.setScalar(1.0 + 0.2 * Math.sin(time * 3));
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
