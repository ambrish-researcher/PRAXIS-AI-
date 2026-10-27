import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import type { Node } from "./types";
export default function Universe({
  nodes,
  onSelect,
  hero = false,
  selectedId,
}: {
  nodes: Node[];
  onSelect?: (n: Node) => void;
  hero?: boolean;
  selectedId?: string;
}) {
  const host = useRef<HTMLDivElement>(null),
    nodesRef = useRef(nodes),
    select = useRef(onSelect);
  nodesRef.current = nodes;
  select.current = onSelect;
  const rebuild = useRef<((nodes: Node[]) => void) | null>(null),
    focus = useRef<((id: string) => void) | null>(null);
  const [fallback, setFallback] = useState(false),
    [hover, setHover] = useState("");
  useEffect(() => {
    rebuild.current?.(nodes);
  }, [nodes]);
  useEffect(() => {
    if (selectedId) focus.current?.(selectedId);
  }, [selectedId]);
  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: devicePixelRatio < 2,
        powerPreference: "low-power",
      });
    } catch {
      setFallback(true);
      return;
    }
    renderer.setPixelRatio(
      Math.min(devicePixelRatio, element.clientWidth < 500 ? 1.2 : 1.5),
    );
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    renderer.domElement.setAttribute(
      "aria-label",
      hero
        ? "Interactive sculptural intelligence core"
        : "Interactive mission evidence graph. Use the node list for keyboard access.",
    );
    element.appendChild(renderer.domElement);
    const scene = new THREE.Scene(),
      camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.set(0, 1, hero ? 9 : 13);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.enablePan = !hero;
    controls.minDistance = 4;
    controls.maxDistance = 28;
    controls.autoRotateSpeed = 0.45;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    scene.add(new THREE.AmbientLight(0xb7d7d5, 2));
    const key = new THREE.DirectionalLight(0xe8ffd1, 4);
    key.position.set(3, 4, 4);
    scene.add(key);
    const rim = new THREE.PointLight(0x5f9ca2, 20);
    rim.position.set(-4, -2, 2);
    scene.add(rim);
    let environment: THREE.WebGLRenderTarget | null = null;
    if (hero) {
      const pmrem = new THREE.PMREMGenerator(renderer),
        room = new RoomEnvironment();
      environment = pmrem.fromScene(room, 0.04);
      scene.environment = environment.texture;
      room.dispose();
      pmrem.dispose();
    }
    const group = new THREE.Group();
    scene.add(group);
    let owned: (THREE.BufferGeometry | THREE.Material)[] = [],
      pickables: THREE.Mesh[] = [];
    const clear = () => {
      group.clear();
      owned.forEach((o) => o.dispose());
      owned = [];
      pickables = [];
    };
    const add = (geometry: THREE.BufferGeometry, material: THREE.Material) => {
      owned.push(geometry, material);
      const mesh = new THREE.Mesh(geometry, material);
      group.add(mesh);
      return mesh;
    };
    if (hero) {
      const core = add(
        new THREE.TorusKnotGeometry(1.55, 0.43, 180, 24, 2, 3),
        new THREE.MeshPhysicalMaterial({
          color: 0x748f79,
          metalness: 0.96,
          roughness: 0.19,
          clearcoat: 1,
          clearcoatRoughness: 0.12,
          envMapIntensity: 1.1,
        }),
      );
      core.rotation.x = 0.5;
      const ring = add(
        new THREE.TorusGeometry(2.5, 0.007, 8, 160),
        new THREE.MeshBasicMaterial({ color: 0xa0bd9c }),
      );
      ring.rotation.set(1.05, 0, 0.3);
      const second = add(
        new THREE.TorusGeometry(2.85, 0.004, 8, 160),
        new THREE.MeshBasicMaterial({ color: 0x536e6a }),
      );
      second.rotation.set(1.3, 0.6, 0);
      for (let i = 0; i < 12; i++) {
        const marker = add(
          new THREE.BoxGeometry(0.05, 0.05, 0.05),
          new THREE.MeshBasicMaterial({ color: 0xc9f590 }),
        );
        marker.position.set(
          Math.cos((i / 12) * Math.PI * 2) * 2.5,
          Math.sin((i / 12) * Math.PI * 2) * 0.9,
          Math.sin((i / 12) * Math.PI * 2) * 2.2,
        );
      }
    } else {
      // Update graph data without recreating the WebGL context, camera or controls on every event.
      rebuild.current = (data: Node[]) => {
        clear();
        const positions = new Map<string, THREE.Vector3>();
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
        data.forEach((node, i) => {
          const angle = i * 2.39996,
            r = i === 0 ? 0 : 2 + Math.sqrt(i) * 0.48,
            p = new THREE.Vector3(
              Math.cos(angle) * r,
              Math.sin(angle) * r * 0.65,
              Math.sin(i * 1.7) * 1.1,
            );
          positions.set(node.id, p);
          const mesh = add(
            new THREE.IcosahedronGeometry(i === 0 ? 0.34 : 0.16, 1),
            new THREE.MeshStandardMaterial({
              color:
                node.status === "failed"
                  ? 0xe28f74
                  : colors[node.kind] || 0xffffff,
              metalness: 0.4,
              roughness: 0.3,
              emissive: node.status === "running" ? 0x608c33 : 0,
              emissiveIntensity: 0.3,
            }),
          );
          mesh.position.copy(p);
          mesh.userData.node = node;
          pickables.push(mesh);
        });
        data.forEach((node) => {
          const a = positions.get(node.id),
            b = positions.get(node.parent || data[0]?.id);
          if (a && b && a !== b) {
            const geometry = new THREE.BufferGeometry().setFromPoints([a, b]),
              material = new THREE.LineBasicMaterial({
                color: 0x405b57,
                transparent: true,
                opacity: 0.65,
              });
            owned.push(geometry, material);
            group.add(new THREE.Line(geometry, material));
          }
        });
      };
      rebuild.current(nodesRef.current);
    }
    let focusTarget: THREE.Vector3 | null = null;
    focus.current = (id) => {
      const mesh = pickables.find((m) => m.userData.node.id === id);
      if (mesh) focusTarget = mesh.position.clone();
    };
    const raycaster = new THREE.Raycaster(),
      pointer = new THREE.Vector2();
    const hit = (event: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointer, camera);
      return raycaster.intersectObjects(pickables)[0];
    };
    let down = { x: 0, y: 0 },
      currentHover = "";
    const pointerDown = (event: PointerEvent) => {
      down = { x: event.clientX, y: event.clientY };
    };
    const pointerUp = (event: PointerEvent) => {
      if (Math.hypot(event.clientX - down.x, event.clientY - down.y) > 5)
        return;
      const selected = hit(event);
      if (selected) select.current?.(selected.object.userData.node);
    };
    const pointerMove = (event: PointerEvent) => {
      if (hero) return;
      const label = hit(event)?.object.userData.node.label || "";
      if (label !== currentHover) {
        currentHover = label;
        setHover(label);
        renderer.domElement.style.cursor = label ? "pointer" : "grab";
      }
    };
    const leave = () => {
      currentHover = "";
      setHover("");
    };
    renderer.domElement.addEventListener("pointerdown", pointerDown);
    renderer.domElement.addEventListener("pointerup", pointerUp);
    renderer.domElement.addEventListener("pointermove", pointerMove);
    renderer.domElement.addEventListener("pointerleave", leave);
    const resize = new ResizeObserver(() => {
      const w = element.clientWidth,
        h = element.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    resize.observe(element);
    let visible = true,
      frame = 0,
      last = 0;
    const observer = new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
    });
    observer.observe(element);
    let lastVisibilityCheck = 0;
    const wake = () => {
      visible = true;
    };
    controls.addEventListener("start", wake);
    const animate = (t: number) => {
      frame = requestAnimationFrame(animate);
      // Programmatic scroll/viewport restoration can leave a stale intersection result.
      // Recheck cheaply while paused, and wake immediately for actual user interaction.
      if (!visible && t - lastVisibilityCheck > 250) {
        lastVisibilityCheck = t;
        const rect = element.getBoundingClientRect();
        visible =
          rect.bottom > 0 &&
          rect.top < innerHeight &&
          rect.right > 0 &&
          rect.left < innerWidth;
      }
      if (!visible || document.hidden || t - last < 33) return;
      last = t;
      controls.autoRotate = hero && !reduced.matches;
      if (focusTarget) {
        const delta = focusTarget
          .clone()
          .sub(controls.target)
          .multiplyScalar(reduced.matches ? 1 : 0.13);
        controls.target.add(delta);
        camera.position.add(delta);
        if (delta.length() < 0.002) focusTarget = null;
      }
      for (const mesh of pickables)
        if (mesh.userData.node.status === "running" && !reduced.matches) {
          (mesh.material as THREE.MeshStandardMaterial).emissiveIntensity =
            0.35 + Math.sin(t * 0.004) * 0.2;
          mesh.scale.setScalar(1 + Math.sin(t * 0.004) * 0.09);
        }
      controls.update();
      renderer.render(scene, camera);
    };
    frame = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      resize.disconnect();
      controls.removeEventListener("start", wake);
      controls.dispose();
      clear();
      environment?.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      rebuild.current = null;
      focus.current = null;
    };
  }, [hero]);
  return (
    <div className={"universe " + (hero ? "hero-universe" : "")} ref={host}>
      {hover && (
        <div className="scene-tooltip" role="status">
          {hover}
        </div>
      )}
      {fallback && (
        <div className="fallback">
          3D is unavailable on this device. All mission data remains accessible
          in the node list.
        </div>
      )}
    </div>
  );
}
