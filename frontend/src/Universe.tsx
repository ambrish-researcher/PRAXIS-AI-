import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Node } from "./types";

export default function Universe({
  nodes,
  onSelect,
  hero = false,
}: {
  nodes: Node[];
  onSelect?: (n: Node) => void;
  hero?: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;
  const [fallback, setFallback] = useState(false);
  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: window.devicePixelRatio < 2,
        alpha: true,
        powerPreference: "low-power",
      });
    } catch {
      setFallback(true);
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    element.appendChild(renderer.domElement);
    renderer.domElement.setAttribute(
      "aria-label",
      hero
        ? "Interactive sculptural intelligence core"
        : "Interactive mission evidence graph. Use the node list for keyboard access.",
    );
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.set(0, 1, hero ? 9 : 13);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.enablePan = !hero;
    controls.minDistance = 4;
    controls.maxDistance = 24;
    controls.autoRotate = hero;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    controls.autoRotateSpeed = 0.45;
    const group = new THREE.Group();
    scene.add(group);
    scene.add(new THREE.AmbientLight(0xb7d7d5, 2));
    const light = new THREE.DirectionalLight(0xe8ffd1, 4);
    light.position.set(3, 4, 4);
    scene.add(light);
    const blue = new THREE.PointLight(0x5f9ca2, 20);
    blue.position.set(-4, -2, 2);
    scene.add(blue);
    const pickables: THREE.Mesh[] = [];
    const owned: (THREE.BufferGeometry | THREE.Material)[] = [];
    const add = (geo: THREE.BufferGeometry, mat: THREE.Material) => {
      owned.push(geo, mat);
      const mesh = new THREE.Mesh(geo, mat);
      group.add(mesh);
      return mesh;
    };
    if (hero) {
      const core = add(
        new THREE.TorusKnotGeometry(1.55, 0.43, 180, 24, 2, 3),
        new THREE.MeshStandardMaterial({
          color: 0xa8b9a5,
          metalness: 0.85,
          roughness: 0.24,
        }),
      );
      core.rotation.x = 0.5;
      const ring = add(
        new THREE.TorusGeometry(2.5, 0.007, 8, 160),
        new THREE.MeshBasicMaterial({ color: 0xa0bd9c }),
      );
      ring.rotation.x = 1.05;
      ring.rotation.z = 0.3;
      const ring2 = add(
        new THREE.TorusGeometry(2.85, 0.004, 8, 160),
        new THREE.MeshBasicMaterial({ color: 0x536e6a }),
      );
      ring2.rotation.x = 1.3;
      ring2.rotation.y = 0.6;
      for (let i = 0; i < 12; i++) {
        const m = add(
          new THREE.BoxGeometry(0.05, 0.05, 0.05),
          new THREE.MeshBasicMaterial({ color: 0xc9f590 }),
        );
        m.position.set(
          Math.cos((i / 12) * Math.PI * 2) * 2.5,
          Math.sin((i / 12) * Math.PI * 2) * 0.9,
          Math.sin((i / 12) * Math.PI * 2) * 2.2,
        );
      }
    } else {
      const positions = new Map<string, THREE.Vector3>();
      nodes.forEach((n, i) => {
        const angle = i * 2.39996;
        const r = i === 0 ? 0 : 2 + Math.sqrt(i) * 0.48;
        const p = new THREE.Vector3(
          Math.cos(angle) * r,
          Math.sin(angle) * r * 0.65,
          Math.sin(i * 1.7) * 1.1,
        );
        positions.set(n.id, p);
        const colors: Record<string, number> = {
          mission: 0xc9f590,
          task: 0x8fb5b2,
          evidence: 0x768fe8,
          decision: 0xeac58d,
          experiment: 0xc39dd4,
          skill: 0xc9f590,
          artifact: 0xffffff,
          tool: 0x5a9e99,
        };
        const m = add(
          new THREE.IcosahedronGeometry(i === 0 ? 0.34 : 0.16, 1),
          new THREE.MeshStandardMaterial({
            color: colors[n.kind] || 0xffffff,
            metalness: 0.3,
            roughness: 0.4,
          }),
        );
        m.position.copy(p);
        m.userData.node = n;
        pickables.push(m);
      });
      nodes.forEach((n) => {
        const a = positions.get(n.id),
          b = positions.get(n.parent || nodes[0]?.id);
        if (a && b && a !== b) {
          const geo = new THREE.BufferGeometry().setFromPoints([a, b]);
          const mat = new THREE.LineBasicMaterial({
            color: 0x405b57,
            transparent: true,
            opacity: 0.65,
          });
          owned.push(geo, mat);
          group.add(new THREE.Line(geo, mat));
        }
      });
    }
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let down = { x: 0, y: 0 };
    const pointerDown = (e: PointerEvent) => {
      down = { x: e.clientX, y: e.clientY };
    };
    const click = (e: PointerEvent) => {
      if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.set(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(pickables)[0];
      if (hit) selectRef.current?.(hit.object.userData.node);
    };
    renderer.domElement.addEventListener("pointerdown", pointerDown);
    renderer.domElement.addEventListener("pointerup", click);
    const resize = new ResizeObserver(() => {
      const w = element.clientWidth,
        h = element.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    resize.observe(element);
    let frame = 0;
    let visible = true;
    let last = 0;
    const observer = new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
    });
    observer.observe(element);
    const animate = (t: number) => {
      frame = requestAnimationFrame(animate);
      if (!visible || document.hidden || t - last < 33) return;
      last = t;
      controls.autoRotate = hero && !reduced.matches;
      controls.update();
      renderer.render(scene, camera);
    };
    frame = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      resize.disconnect();
      controls.dispose();
      owned.forEach((x) => x.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [hero, nodes]);
  return (
    <div className={"universe " + (hero ? "hero-universe" : "")} ref={host}>
      {fallback && (
        <div className="fallback">
          3D is unavailable on this device. All mission data remains accessible
          in the node list.
        </div>
      )}
    </div>
  );
}
