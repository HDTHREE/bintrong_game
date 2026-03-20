import * as THREE from 'three';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x11_11_11);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 12, 14);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({antialias: true});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
document.body.append(renderer.domElement);

const dirLight = new THREE.DirectionalLight(0xFF_FF_FF, 1.2);
dirLight.position.set(8, 15, 10);
dirLight.castShadow = true;
scene.add(dirLight);
scene.add(new THREE.AmbientLight(0x60_60_60));

const platformSize = 16;
const platform = new THREE.Mesh(
	new THREE.BoxGeometry(platformSize, 0.4, platformSize),
	new THREE.MeshStandardMaterial({color: 0x33_66_99}),
);
platform.position.y = -0.2;
platform.receiveShadow = true;
scene.add(platform);

const player = new THREE.Mesh(
	new THREE.BoxGeometry(1, 1, 1),
	new THREE.MeshStandardMaterial({color: 0xFF_AA_00}),
);
player.position.y = 0.5;
player.castShadow = true;
scene.add(player);

const velocity = new THREE.Vector3();
const gravity = -25;
const jumpSpeed = 10;
const moveSpeed = 8;
const halfBound = platformSize / 2 - 0.5; 
let onGround = true;

const keys: Record<string, boolean> = {};
window.addEventListener('keydown', (e) => {
	keys[e.code] = true;
});
window.addEventListener('keyup', (e) => {
	keys[e.code] = false;
});

window.addEventListener('resize', () => {
	camera.aspect = window.innerWidth / window.innerHeight;
	camera.updateProjectionMatrix();
	renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();

function animate() {
	requestAnimationFrame(animate);
	const dt = Math.min(clock.getDelta(), 0.05);

	const dir = new THREE.Vector3();
	if (keys.KeyW) dir.z -= 1;
	if (keys.KeyS) dir.z += 1;
	if (keys.KeyA) dir.x -= 1;
	if (keys.KeyD) dir.x += 1;
	if (dir.length() > 0) dir.normalize();

	player.position.x += dir.x * moveSpeed * dt;
	player.position.z += dir.z * moveSpeed * dt;

	if (keys.Space && onGround) {
		velocity.y = jumpSpeed;
		onGround = false;
	}

	velocity.y += gravity * dt;
	player.position.y += velocity.y * dt;

	if (player.position.y <= 0.5) {
		player.position.y = 0.5;
		velocity.y = 0;
		onGround = true;
	}

	player.position.x = Math.max(-halfBound, Math.min(halfBound, player.position.x));
	player.position.z = Math.max(-halfBound, Math.min(halfBound, player.position.z));

	renderer.render(scene, camera);
}

animate();

