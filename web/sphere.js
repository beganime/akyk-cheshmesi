(function () {
  const host = document.getElementById("heroSphere");
  const canvas = document.getElementById("heroSphereCanvas");
  const desktop = window.matchMedia("(min-width: 981px)");

  if (!host || !canvas || !desktop.matches || !window.THREE) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 0, 6.2);

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
  } catch (_) {
    host.classList.add("sphere-unavailable");
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const group = new THREE.Group();
  scene.add(group);

  const geometry = new THREE.SphereGeometry(1.75, 56, 36);
  const sphere = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({
      color: 0x8d63f6,
      emissive: 0x24123f,
      emissiveIntensity: 0.5,
      roughness: 0.32,
      metalness: 0.14,
    })
  );
  group.add(sphere);

  const grid = new THREE.Mesh(
    geometry,
    new THREE.MeshBasicMaterial({
      color: 0xd8c8ff,
      wireframe: true,
      transparent: true,
      opacity: 0.13,
      depthWrite: false,
    })
  );
  grid.scale.setScalar(1.004);
  group.add(grid);

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(1.28, 28, 20),
    new THREE.MeshBasicMaterial({ color: 0x00f575, transparent: true, opacity: 0.065 })
  );
  group.add(core);

  scene.add(new THREE.HemisphereLight(0xf1f0ec, 0x1c1624, 2.2));
  const violetLight = new THREE.PointLight(0xb997ff, 31, 18);
  violetLight.position.set(3.8, 2.4, 4.2);
  scene.add(violetLight);
  const greenLight = new THREE.PointLight(0x00f575, 20, 16);
  greenLight.position.set(-3.5, -2.2, 3.1);
  scene.add(greenLight);

  let dragging = false;
  let previousX = 0;
  let previousY = 0;
  let velocityX = 0.003;
  let velocityY = 0.006;
  let visible = true;
  let frameId = 0;

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

  function animate(time) {
    frameId = requestAnimationFrame(animate);
    if (!visible || document.hidden) return;
    if (!dragging) {
      velocityX *= 0.965;
      velocityY *= 0.965;
      group.rotation.x += velocityX + 0.00035;
      group.rotation.y += velocityY + 0.0022;
    }
    core.scale.setScalar(1 + Math.sin(time * 0.0015) * 0.025);
    renderer.render(scene, camera);
  }

  canvas.addEventListener("pointerdown", pointerDown);
  canvas.addEventListener("pointermove", pointerMove);
  canvas.addEventListener("pointerup", pointerUp);
  canvas.addEventListener("pointercancel", pointerUp);
  window.addEventListener("resize", resize, { passive: true });
  new IntersectionObserver((entries) => {
    visible = entries[0]?.isIntersecting !== false;
  }, { threshold: 0.01 }).observe(host);
  window.addEventListener("pagehide", () => cancelAnimationFrame(frameId), { once: true });

  resize();
  renderer.render(scene, camera);
  animate(0);
})();
