import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {
	connect, sendUpdate, sendAttack, type RemotePlayerData, type RoundState,
} from './network';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x11_11_11);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 12, 14);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({antialias: true});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.append(renderer.domElement);

const deadOverlay = document.createElement('div');
deadOverlay.textContent = 'YOU ARE DEAD';
deadOverlay.style.position = 'fixed';
deadOverlay.style.inset = '0';
deadOverlay.style.display = 'none';
deadOverlay.style.alignItems = 'center';
deadOverlay.style.justifyContent = 'center';
deadOverlay.style.color = '#ff2020';
deadOverlay.style.fontFamily = 'Impact, Haettenschweiler, "Arial Black", sans-serif';
deadOverlay.style.fontSize = 'clamp(2rem, 8vw, 5rem)';
deadOverlay.style.letterSpacing = '0.12em';
deadOverlay.style.textShadow = '0 0 16px rgba(255, 0, 0, 0.9)';
deadOverlay.style.background = 'rgba(0, 0, 0, 0.28)';
deadOverlay.style.pointerEvents = 'none';
deadOverlay.style.zIndex = '9999';
document.body.append(deadOverlay);

const roundHud = document.createElement('div');
roundHud.style.position = 'fixed';
roundHud.style.left = '50%';
roundHud.style.top = '18px';
roundHud.style.transform = 'translateX(-50%)';
roundHud.style.padding = '12px 16px';
roundHud.style.background = 'rgba(0, 0, 0, 0.45)';
roundHud.style.border = '1px solid rgba(255, 255, 255, 0.2)';
roundHud.style.borderRadius = '10px';
roundHud.style.color = '#ffffff';
roundHud.style.fontFamily = '"Trebuchet MS", Verdana, sans-serif';
roundHud.style.minWidth = 'min(92vw, 840px)';
roundHud.style.textAlign = 'center';
roundHud.style.backdropFilter = 'blur(2px)';
roundHud.style.pointerEvents = 'none';
roundHud.style.zIndex = '1000';

const roundTimer = document.createElement('div');
roundTimer.style.fontSize = '1.1rem';
roundTimer.style.fontWeight = '700';
roundTimer.style.letterSpacing = '0.04em';
roundTimer.textContent = 'Waiting...';

const roundQuestion = document.createElement('div');
roundQuestion.style.marginTop = '6px';
roundQuestion.style.fontSize = '1.05rem';
roundQuestion.style.fontWeight = '600';
roundQuestion.textContent = 'Waiting for first question';

roundHud.append(roundTimer, roundQuestion);
document.body.append(roundHud);

const dirLight = new THREE.DirectionalLight(0xFF_FF_FF, 1.2);
dirLight.position.set(8, 15, 10);
dirLight.castShadow = true;
dirLight.shadow.mapSize.set(2048, 2048);
dirLight.shadow.camera.left = -12;
dirLight.shadow.camera.right = 12;
dirLight.shadow.camera.top = 12;
dirLight.shadow.camera.bottom = -12;
dirLight.shadow.camera.near = 1;
dirLight.shadow.camera.far = 40;
dirLight.shadow.bias = -0.0004;
dirLight.shadow.normalBias = 0.03;
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

const player = new THREE.Group();
player.position.y = 0;
scene.add(player);

const velocity = new THREE.Vector3();
const gravity = -25;
const jumpSpeed = 10;
const moveSpeed = 8;
const halfBound = (platformSize / 2) - 0.5;
const playerRadius = 0.35;
let onGround = true;

let mixer: THREE.AnimationMixer | undefined;
const actions: Record<string, THREE.AnimationAction> = {};
let idleActions: THREE.AnimationAction[] = [];
let currentAction: THREE.AnimationAction | undefined;
let currentIdleIndex = -1;
let currentAnimName = 'idle';

const attackCooldown = 0.6;
let attackTimer = 0;
let isAttacking = false;

const stunDuration = 0.1;
let stunTimer = 0;
let isStunned = false;

let localModelFile = 'Colobus_Animations.glb';
let isLocalDead = false;
let socketId = '';

function setLocalDead(nextDead: boolean) {
	isLocalDead = nextDead;
	player.visible = !nextDead;
	deadOverlay.style.display = nextDead ? 'flex' : 'none';
}

function fadeToAction(next: THREE.AnimationAction, duration = 0.2) {
	if (next === currentAction) {
		return;
	}

	if (currentAction) {
		currentAction.fadeOut(duration);
	}

	next.reset().fadeIn(duration).play();
	currentAction = next;
}

function pickRandomIdle() {
	if (idleActions.length === 0) {
		return;
	}

	let idx = Math.floor(Math.random() * idleActions.length);
	if (idleActions.length > 1 && idx === currentIdleIndex) {
		idx = (idx + 1) % idleActions.length;
	}

	currentIdleIndex = idx;
	fadeToAction(idleActions[idx]);
	currentAnimName = 'idle';
}

const modelsDir = 'assets/models/players/';
const loader = new GLTFLoader();

function disposeGroupContents(group: THREE.Group) {
	for (const child of group.children) {
		child.traverse(node => {
			if ((node as THREE.Mesh).isMesh) {
				const mesh = node as THREE.Mesh;
				mesh.geometry.dispose();
				if (Array.isArray(mesh.material)) {
					for (const mat of mesh.material) {
						mat.dispose();
					}
				} else {
					mesh.material.dispose();
				}
			}
		});
		group.remove(child);
	}
}

function loadLocalModel(file: string) {
	localModelFile = file;
	disposeGroupContents(player);
	mixer?.stopAllAction();
	mixer = undefined;
	idleActions = [];
	currentAction = undefined;
	currentIdleIndex = -1;
	for (const key of Object.keys(actions)) {
		delete actions[key];
	}

	loader.load(modelsDir + file, gltf => {
		const model = gltf.scene;
		model.traverse(child => {
			if ((child as THREE.Mesh).isMesh) {
				child.castShadow = true;
			}
		});
		player.add(model);

		mixer = new THREE.AnimationMixer(model);

		for (const clip of gltf.animations) {
			actions[clip.name] = mixer.clipAction(clip);
		}

		const walkKey = Object.keys(actions).find(n => /walk/i.test(n));
		const jumpKey = Object.keys(actions).find(n => /jump/i.test(n));
		const idleKeys = Object.keys(actions).filter(n => /idle/i.test(n));
		const reservedKeys = new Set([walkKey, jumpKey, ...idleKeys].filter(Boolean));
		const attackKey = Object.keys(actions).find(n => /attack|bite|hit|punch|swipe|scratch|strike|claw|snap|headbutt/i.test(n))
			?? Object.keys(actions).find(n => !reservedKeys.has(n));

		if (walkKey) {
			actions._walk = actions[walkKey];
		}

		if (jumpKey) {
			actions._jump = actions[jumpKey];
		}

		if (attackKey) {
			actions._attack = actions[attackKey];
			actions._attack.setLoop(THREE.LoopOnce, 1);
			actions._attack.clampWhenFinished = true;
			console.log('Attack animation mapped to:', attackKey);
		} else {
			console.warn('No attack animation found in clips:', Object.keys(actions));
		}

		const hitKey = Object.keys(actions).find(n => /hurt|damage|pain|flinch|stagger|react|gethit|hit/i.test(n))
			?? attackKey;
		if (hitKey) {
			actions._hit = actions[hitKey];
			actions._hit.setLoop(THREE.LoopOnce, 1);
			actions._hit.clampWhenFinished = true;
		}

		idleActions = idleKeys.map(k => actions[k]);
		pickRandomIdle();

		console.log('Loaded local model:', file, '| Animations:', gltf.animations.map(c => c.name));
	});
}

type RemotePlayer = {
	group: THREE.Group;
	mixer: THREE.AnimationMixer | undefined;
	actions: Record<string, THREE.AnimationAction>;
	currentAction: THREE.AnimationAction | undefined;
	targetPos: THREE.Vector3;
	targetRotY: number;
	animation: string;
	modelFile: string;
	dead: boolean;
};

type ZoneVisual = {
	shadow: THREE.Mesh;
	label: THREE.Sprite;
	labelText: string;
};

const remotePlayers = new Map<string, RemotePlayer>();
const zoneVisuals = new Map<number, ZoneVisual>();

function createTextSprite(text: string): THREE.Sprite {
	const canvas = document.createElement('canvas');
	canvas.width = 512;
	canvas.height = 256;
	const context = canvas.getContext('2d');
	if (!context) {
		const fallback = new THREE.Sprite(new THREE.SpriteMaterial({color: 0xFF_FF_FF}));
		fallback.scale.set(3.2, 1.6, 1);
		return fallback;
	}

	context.clearRect(0, 0, canvas.width, canvas.height);
	context.fillStyle = 'rgba(0, 0, 0, 0.62)';
	context.fillRect(6, 16, canvas.width - 12, canvas.height - 32);
	context.strokeStyle = 'rgba(255, 255, 255, 0.75)';
	context.lineWidth = 3;
	context.strokeRect(6, 16, canvas.width - 12, canvas.height - 32);
	context.fillStyle = '#ffffff';
	context.font = '700 30px Trebuchet MS';
	context.textAlign = 'center';
	context.textBaseline = 'top';

	const maxTextWidth = canvas.width - 34;
	const words = text.split(/\s+/).filter(Boolean);
	const lines: string[] = [];
	let currentLine = '';
	for (const word of words) {
		const trial = currentLine ? `${currentLine} ${word}` : word;
		if (context.measureText(trial).width <= maxTextWidth) {
			currentLine = trial;
			continue;
		}

		if (currentLine) {
			lines.push(currentLine);
		}

		currentLine = word;
	}

	if (currentLine) {
		lines.push(currentLine);
	}

	const maxLines = 5;
	const visibleLines = lines.slice(0, maxLines);
	if (lines.length > maxLines) {
		visibleLines[maxLines - 1] = `${visibleLines[maxLines - 1]}...`;
	}

	const lineHeight = 38;
	const contentHeight = visibleLines.length * lineHeight;
	let y = Math.max(28, (canvas.height - contentHeight) / 2);
	for (const line of visibleLines) {
		context.fillText(line, canvas.width / 2, y);
		y += lineHeight;
	}

	const texture = new THREE.CanvasTexture(canvas);
	texture.needsUpdate = true;
	const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
		map: texture,
		transparent: true,
		depthTest: false,
		depthWrite: false,
	}));
	sprite.scale.set(4.2, 2.1, 1);
	return sprite;
}

function clearZoneVisuals() {
	for (const visual of zoneVisuals.values()) {
		scene.remove(visual.shadow);
		scene.remove(visual.label);
		visual.shadow.geometry.dispose();
		(visual.shadow.material as THREE.Material).dispose();
		const {material} = visual.label;
		material.map?.dispose();
		material.dispose();
	}

	zoneVisuals.clear();
}

function updateZoneVisuals(roundState: RoundState) {
	if (roundState.phase !== 'question') {
		clearZoneVisuals();
		return;
	}

	const liveZoneIds = new Set<number>();
	for (const zone of roundState.zones) {
		liveZoneIds.add(zone.id);
		let visual = zoneVisuals.get(zone.id);
		if (!visual) {
			const shadow = new THREE.Mesh(
				new THREE.CircleGeometry(1, 32),
				new THREE.MeshBasicMaterial({
					color: 0x00_00_00,
					transparent: true,
					opacity: 0.32,
				}),
			);
			shadow.rotation.x = -Math.PI / 2;
			shadow.position.y = 0.005;
			shadow.visible = zone.revealed;

			const label = createTextSprite(zone.answer);
			label.position.y = 1.25;
			label.visible = zone.revealed;

			scene.add(shadow);
			scene.add(label);
			visual = {
				shadow,
				label,
				labelText: zone.answer,
			};
			zoneVisuals.set(zone.id, visual);
		}

		visual.shadow.position.set(zone.x, 0.005, zone.z);
		visual.shadow.scale.set(zone.radius, zone.radius, 1);
		visual.shadow.visible = zone.revealed;
		visual.label.position.set(zone.x, 1.25, zone.z);

		if (zone.answer !== visual.labelText) {
			const {material} = visual.label;
			material.map?.dispose();
			material.dispose();
			scene.remove(visual.label);
			visual.label = createTextSprite(zone.answer);
			visual.label.position.set(zone.x, 1.25, zone.z);
			visual.label.visible = zone.revealed;
			scene.add(visual.label);
			visual.labelText = zone.answer;
		}

		visual.label.visible = zone.revealed;
		if (zone.revealed) {
			const revealRank = roundState.zones
				.filter(candidate => candidate.revealed)
				.findIndex(candidate => candidate.id === zone.id);
			visual.label.renderOrder = 100 + revealRank;
			visual.shadow.renderOrder = 50 + revealRank;
		}
	}

	for (const [id, visual] of zoneVisuals) {
		if (liveZoneIds.has(id)) {
			continue;
		}

		scene.remove(visual.shadow);
		scene.remove(visual.label);
		visual.shadow.geometry.dispose();
		(visual.shadow.material as THREE.Material).dispose();
		const {material} = visual.label;
		material.map?.dispose();
		material.dispose();
		zoneVisuals.delete(id);
	}
}

function applyRoundState(roundState: RoundState) {
	const secondsLeft = Math.ceil(roundState.timeLeftMs / 1000);
	if (roundState.phase === 'question') {
		roundTimer.textContent = `Round ${roundState.round} | ${secondsLeft}s`;
		roundQuestion.textContent = roundState.question;
	} else if (roundState.phase === 'break') {
		roundTimer.textContent = `Break | ${secondsLeft}s`;
		roundQuestion.textContent = 'Next question incoming...';
	} else {
		roundTimer.textContent = 'Waiting';
		roundQuestion.textContent = roundState.question || 'Waiting for players';
	}

	updateZoneVisuals(roundState);
}

function loadRemoteModel(remote: RemotePlayer, modelFile: string) {
	remote.modelFile = modelFile;
	disposeGroupContents(remote.group);
	remote.mixer?.stopAllAction();
	remote.mixer = undefined;
	remote.currentAction = undefined;
	for (const key of Object.keys(remote.actions)) {
		delete remote.actions[key];
	}

	loader.load(modelsDir + modelFile, gltf => {
		const model = gltf.scene;
		model.traverse(child => {
			if ((child as THREE.Mesh).isMesh) {
				child.castShadow = true;
			}
		});
		remote.group.add(model);

		remote.mixer = new THREE.AnimationMixer(model);
		for (const clip of gltf.animations) {
			remote.actions[clip.name] = remote.mixer.clipAction(clip);
		}

		const walkKey = Object.keys(remote.actions).find(n => /walk/i.test(n));
		const jumpKey = Object.keys(remote.actions).find(n => /jump/i.test(n));
		const idleKeys = Object.keys(remote.actions).filter(n => /idle/i.test(n));
		const rReserved = new Set([walkKey, jumpKey, ...idleKeys].filter(Boolean));
		const attackKey = Object.keys(remote.actions).find(n => /attack|bite|hit|punch|swipe|scratch|strike|claw|snap|headbutt/i.test(n))
			?? Object.keys(remote.actions).find(n => !rReserved.has(n));

		if (walkKey) {
			remote.actions._walk = remote.actions[walkKey];
		}

		if (jumpKey) {
			remote.actions._jump = remote.actions[jumpKey];
		}

		if (attackKey) {
			remote.actions._attack = remote.actions[attackKey];
			remote.actions._attack.setLoop(THREE.LoopOnce, 1);
			remote.actions._attack.clampWhenFinished = true;
		}

		const rHitKey = Object.keys(remote.actions).find(n => /hurt|damage|pain|flinch|stagger|react|gethit|hit/i.test(n))
			?? attackKey;
		if (rHitKey) {
			remote.actions._hit = remote.actions[rHitKey];
			remote.actions._hit.setLoop(THREE.LoopOnce, 1);
			remote.actions._hit.clampWhenFinished = true;
		}

		if (idleKeys.length > 0) {
			const firstIdle = remote.actions[idleKeys[0]];
			firstIdle.play();
			remote.currentAction = firstIdle;
		}
	});
}

function addRemotePlayer(data: RemotePlayerData) {
	if (remotePlayers.has(data.id)) {
		return;
	}

	const group = new THREE.Group();
	group.position.set(data.x, data.y, data.z);
	group.rotation.y = data.rotationY;
	scene.add(group);

	const remote: RemotePlayer = {
		group,
		mixer: undefined,
		actions: {},
		currentAction: undefined,
		targetPos: new THREE.Vector3(data.x, data.y, data.z),
		targetRotY: data.rotationY,
		animation: data.animation,
		modelFile: data.modelFile,
		dead: data.dead,
	};
	group.visible = !data.dead;
	remotePlayers.set(data.id, remote);

	loadRemoteModel(remote, data.modelFile);
}

function removeRemotePlayer(id: string) {
	const remote = remotePlayers.get(id);
	if (!remote) {
		return;
	}

	scene.remove(remote.group);
	remote.group.traverse(child => {
		if ((child as THREE.Mesh).isMesh) {
			const mesh = child as THREE.Mesh;
			mesh.geometry.dispose();
			if (Array.isArray(mesh.material)) {
				for (const mat of mesh.material) {
					mat.dispose();
				}
			} else {
				mesh.material.dispose();
			}
		}
	});
	remotePlayers.delete(id);
}

function updateRemotePlayer(data: RemotePlayerData) {
	const remote = remotePlayers.get(data.id);
	if (!remote) {
		return;
	}

	remote.targetPos.set(data.x, data.y, data.z);
	remote.targetRotY = data.rotationY;
	remote.animation = data.animation;
	remote.dead = data.dead;
	remote.group.visible = !data.dead;

	if (data.modelFile !== remote.modelFile) {
		loadRemoteModel(remote, data.modelFile);
	}

	if (data.dead) {
		return;
	}

	if (remote.mixer) {
		let nextAction: THREE.AnimationAction | undefined;
		if (data.animation === 'jump' && remote.actions._jump) {
			nextAction = remote.actions._jump;
		} else if (data.animation === 'attack' && remote.actions._attack) {
			nextAction = remote.actions._attack;
		} else if (data.animation === 'hit' && remote.actions._hit) {
			nextAction = remote.actions._hit;
		} else if (data.animation === 'walk' && remote.actions._walk) {
			nextAction = remote.actions._walk;
		} else {
			const idleKey = Object.keys(remote.actions).find(n => /idle/i.test(n));
			if (idleKey) {
				nextAction = remote.actions[idleKey];
			}
		}

		if (nextAction && nextAction !== remote.currentAction) {
			if (remote.currentAction) {
				remote.currentAction.fadeOut(0.2);
			}

			nextAction.reset().fadeIn(0.2).play();
			remote.currentAction = nextAction;
		}
	}
}

connect({
	onInit(payload) {
		socketId = payload.id;
		localModelFile = payload.modelFile;
		loadLocalModel(localModelFile);
		if (payload.roundState) {
			applyRoundState(payload.roundState);
		}

		// Apply server-assigned spawn position
		const me = payload.players[payload.id];
		if (me) {
			player.position.set(me.x, me.y, me.z);
			setLocalDead(me.dead);
		}

		for (const [id, pdata] of Object.entries(payload.players)) {
			if (id !== payload.id) {
				addRemotePlayer(pdata);
			}
		}

		console.log(`Connected as ${payload.id} with model ${payload.modelFile}`);
	},
	onPlayerJoined(playerData) {
		addRemotePlayer(playerData);
		console.log(`Player joined: ${playerData.id}`);
	},
	onPlayerMoved(playerData) {
		if (playerData.id === socketId) {
			if (playerData.modelFile !== localModelFile) {
				loadLocalModel(playerData.modelFile);
			}

			setLocalDead(playerData.dead);
			player.position.set(playerData.x, playerData.y, playerData.z);
			player.rotation.y = playerData.rotationY;
			velocity.y = playerData.velocityY;
			onGround = player.position.y <= 0;
			currentAnimName = playerData.animation;
			return;
		}

		updateRemotePlayer(playerData);
	},
	onPlayerLeft(id) {
		removeRemotePlayer(id);
		console.log(`Player left: ${id}`);
	},
	onPlayerAttacked(data) {
		// Show attack animation on remote player
		const remote = remotePlayers.get(data.id);
		if (remote?.mixer && remote.actions._attack) {
			if (remote.currentAction) {
				remote.currentAction.fadeOut(0.15);
			}

			remote.actions._attack.reset().fadeIn(0.15).play();
			remote.currentAction = remote.actions._attack;
		}
	},
	onKnockback(data) {
		// Server says we got hit — snap to knockback position and apply stun
		player.position.x = data.x;
		player.position.z = data.z;

		isStunned = true;
		stunTimer = stunDuration;
		isAttacking = false;
		attackTimer = 0;

		// Play hit animation once
		if (mixer && actions._hit) {
			mixer.stopAllAction();
			actions._hit.reset();
			actions._hit.setEffectiveWeight(1);
			actions._hit.setEffectiveTimeScale(1);
			actions._hit.play();
			currentAction = actions._hit;
			currentAnimName = 'hit';
		}
	},
	onRoundState(state) {
		applyRoundState(state);
	},
});

const keys: Record<string, boolean> = {};
globalThis.addEventListener('keydown', event => {
	keys[event.code] = true;
	// Also map by event.key for Enter (covers NumpadEnter, etc.)
	// Fuck chrome this is stupid why is there so many standards
	if (event.key === 'Enter') {
		keys.Enter = true;
	}
});
globalThis.addEventListener('keyup', event => {
	keys[event.code] = false;
	if (event.key === 'Enter') {
		keys.Enter = false;
	}
});

window.addEventListener('resize', () => {
	camera.aspect = window.innerWidth / window.innerHeight;
	camera.updateProjectionMatrix();
	renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
let wasMoving = false;
let wasOnGround = true;
const sendRate = 1 / 20;
let sendTimer = 0;

function animate() {
	requestAnimationFrame(animate);
	const dt = Math.min(clock.getDelta(), 0.05);

	// Tick stun timer
	if (!isLocalDead && stunTimer > 0) {
		stunTimer -= dt;
		if (stunTimer <= 0) {
			isStunned = false;
		}
	}

	const dir = new THREE.Vector3();
	if (!isLocalDead && !isStunned && keys.KeyW) {
		dir.z -= 1;
	}

	if (!isLocalDead && !isStunned && keys.KeyS) {
		dir.z += 1;
	}

	if (!isLocalDead && !isStunned && keys.KeyA) {
		dir.x -= 1;
	}

	if (!isLocalDead && !isStunned && keys.KeyD) {
		dir.x += 1;
	}

	const isMoving = dir.length() > 0;
	if (isMoving) {
		dir.normalize();
	}

	player.position.x += dir.x * moveSpeed * dt;
	player.position.z += dir.z * moveSpeed * dt;

	if (isMoving) {
		player.rotation.y = Math.atan2(dir.x, dir.z);
	}

	if (!isLocalDead && !isStunned && keys.Space && onGround) {
		velocity.y = jumpSpeed;
		onGround = false;
	}

	// Attack on Enter
	if (attackTimer > 0) {
		attackTimer -= dt;
		if (attackTimer <= 0) {
			isAttacking = false;
		}
	}

	if (!isLocalDead && keys.Enter && !isAttacking && !isStunned) {
		isAttacking = true;
		attackTimer = attackCooldown;
		currentAnimName = 'attack';

		if (mixer && actions._attack) {
			// Stop all current animations and play attack
			mixer.stopAllAction();
			actions._attack.reset();
			actions._attack.setEffectiveWeight(1);
			actions._attack.setEffectiveTimeScale(1);
			actions._attack.play();
			currentAction = actions._attack;
		}

		sendAttack({
			x: player.position.x,
			z: player.position.z,
			rotationY: player.rotation.y,
		});
	}

	velocity.y += gravity * dt;
	player.position.y += velocity.y * dt;

	if (player.position.y <= 0) {
		player.position.y = 0;
		velocity.y = 0;
		onGround = true;
	}

	if (!isLocalDead) {
		for (const remote of remotePlayers.values()) {
			if (remote.dead) {
				continue;
			}

			const dx = player.position.x - remote.group.position.x;
			const dz = player.position.z - remote.group.position.z;
			const dist = Math.hypot(dx, dz);
			const minDist = playerRadius * 2;

			if (dist < minDist && dist > 0) {
				const overlap = minDist - dist;
				const nx = dx / dist;
				const nz = dz / dist;
				const half = overlap * 0.5;
				player.position.x += nx * half;
				player.position.z += nz * half;
				remote.group.position.x -= nx * half;
				remote.group.position.z -= nz * half;
				remote.targetPos.x -= nx * half;
				remote.targetPos.z -= nz * half;
			}
		}
	}

	player.position.x = Math.max(-halfBound, Math.min(halfBound, player.position.x));
	player.position.z = Math.max(-halfBound, Math.min(halfBound, player.position.z));

	if (mixer && !isLocalDead) {
		if (isStunned) {
			// Keep playing hit animation during stun
		} else if (isAttacking) {
			// Keep playing attack animation
		} else if (!onGround) {
			if (actions._jump && (wasOnGround || currentAction !== actions._jump)) {
				fadeToAction(actions._jump);
				currentAnimName = 'jump';
			}
		} else if (isMoving) {
			if (actions._walk && (currentAction !== actions._walk)) {
				fadeToAction(actions._walk);
				currentAnimName = 'walk';
			}
		} else if (currentAction !== undefined && !idleActions.includes(currentAction)) {
			pickRandomIdle();
		} else if (wasMoving || !wasOnGround) {
			pickRandomIdle();
		}

		mixer.update(dt);
	}

	wasMoving = isMoving;
	wasOnGround = onGround;

	sendTimer += dt;
	if (sendTimer >= sendRate) {
		sendTimer = 0;
		sendUpdate({
			x: player.position.x,
			y: player.position.y,
			z: player.position.z,
			rotationY: player.rotation.y,
			velocityY: velocity.y,
			animation: currentAnimName,
		});
	}

	for (const remote of remotePlayers.values()) {
		if (remote.dead) {
			continue;
		}

		remote.group.position.lerp(remote.targetPos, 0.2);
		const angleDiff = remote.targetRotY - remote.group.rotation.y;
		remote.group.rotation.y += angleDiff * 0.2;

		remote.mixer?.update(dt);
	}

	renderer.render(scene, camera);
}

animate();

