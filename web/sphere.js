(function () {
  const host = document.getElementById("heroSphere");
  const canvas = document.getElementById("heroSphereCanvas");
  const desktop = window.matchMedia("(min-width: 981px) and (pointer: fine)");

  if (!host || !canvas || !desktop.matches || !window.THREE) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 0, 6.2);

  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    preserveDrawingBuffer: true,
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const group = new THREE.Group();
  scene.add(group);

  const geometry = new THREE.SphereGeometry(1.75, 96, 64);
  const sphere = new THREE.Mesh(
    geometry,
    new THREE.MeshPhysicalMaterial({
      color: 0x8d63f6,
      emissive: 0x24123f,
      emissiveIntensity: 0.55,
      roughness: 0.28,
      metalness: 0.18,
      clearcoat: 0.72,
      clearcoatRoughness: 0.22,
    })
  );
  group.add(sphere);

  const grid = new THREE.Mesh(
    geometry,
    new THREE.MeshBasicMaterial({
      color: 0xd8c8ff,
      wireframe: true,
      transparent: true,
      opacity: 0.12,
      depthWrite: false,
    })
  );
  grid.scale.setScalar(1.004);
  group.add(grid);

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(1.28, 48, 32),
    new THREE.MeshBasicMaterial({ color: 0x00f575, transparent: true, opacity: 0.07 })
  );
  group.add(core);

  scene.add(new THREE.HemisphereLight(0xf1f0ec, 0x1c1624, 2.3));
  const violetLight = new THREE.PointLight(0xb997ff, 35, 18);
  violetLight.position.set(3.8, 2.4, 4.2);
  scene.add(violetLight);
  const greenLight = new THREE.PointLight(0x00f575, 24, 16);
  greenLight.position.set(-3.5, -2.2, 3.1);
  scene.add(greenLight);

  let dragging = false;
  let previousX = 0;
  let previousY = 0;
  let velocityX = 0.003;
  let velocityY = 0.006;

  function resize() {
    const width = Math.max(host.clientWidth, 1);
    const height = Math.max(host.clientHeight, 1);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function pointerDown(event) {
    dragging = true;
    previousX = event.clientX;
    previousY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
    canvas.classList.add("is-dragging");
  }

  function pointerMove(event) {
    if (!dragging) return;
    const dx = event.clientX - previousX;
    const dy = event.clientY - previousY;
    velocityY = dx * 0.008;
    velocityX = dy * 0.008;
    group.rotation.y += velocityY;
    group.rotation.x += velocityX;
    previousX = event.clientX;
    previousY = event.clientY;
  }

  function pointerUp(event) {
    dragging = false;
    if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
    canvas.classList.remove("is-dragging");
  }

  canvas.addEventListener("pointerdown", pointerDown);
  canvas.addEventListener("pointermove", pointerMove);
  canvas.addEventListener("pointerup", pointerUp);
  canvas.addEventListener("pointercancel", pointerUp);
  window.addEventListener("resize", resize);

  function animate() {
    requestAnimationFrame(animate);
    if (!dragging) {
      velocityX *= 0.965;
      velocityY *= 0.965;
      group.rotation.x += velocityX + 0.0004;
      group.rotation.y += velocityY + 0.0026;
    }
    core.scale.setScalar(1 + Math.sin(performance.now() * 0.0015) * 0.025);
    renderer.render(scene, camera);
  }

  resize();
  animate();
})();
