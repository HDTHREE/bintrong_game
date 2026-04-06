import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {
	connect,
	sendUpdate,
	sendAttack,
	sendHostGameDecision,
	type RemotePlayerData,
	type RoundState,
	type ObstacleData,
	type ScoreboardRow,
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

const scoreboardElement = document.createElement('div');
scoreboardElement.style.position = 'fixed';
scoreboardElement.style.top = '18px';
scoreboardElement.style.right = '14px';
scoreboardElement.style.padding = '8px 12px';
scoreboardElement.style.background = 'rgba(0, 0, 0, 0.45)';
scoreboardElement.style.border = '1px solid rgba(255, 255, 255, 0.2)';
scoreboardElement.style.borderRadius = '10px';
scoreboardElement.style.color = '#ffffff';
scoreboardElement.style.fontFamily = '"Trebuchet MS", Verdana, sans-serif';
scoreboardElement.style.fontSize = '0.88rem';
scoreboardElement.style.backdropFilter = 'blur(2px)';
scoreboardElement.style.pointerEvents = 'none';
scoreboardElement.style.zIndex = '1000';
scoreboardElement.style.minWidth = '140px';
document.body.append(scoreboardElement);

function renderScoreboard(rows: ScoreboardRow[]) {
	const statusIcon: Record<ScoreboardRow['status'], string> = {
		alive: '❤️',
		dead: '💀',
		left: '❓',
	};

	scoreboardElement.innerHTML = rows
		.map(row =>
			'<div style="display:flex;justify-content:space-between;gap:12px;padding:2px 0">'
			+ `<span>Player ${row.playerNumber}</span>`
			+ `<span>${statusIcon[row.status]} ${row.score}</span>`
			+ '</div>')
		.join('');
}

const hostDecisionOverlay = document.createElement('div');
hostDecisionOverlay.textContent = 'Waiting for host';
hostDecisionOverlay.style.position = 'fixed';
hostDecisionOverlay.style.inset = '0';
hostDecisionOverlay.style.display = 'none';
hostDecisionOverlay.style.alignItems = 'center';
hostDecisionOverlay.style.justifyContent = 'center';
hostDecisionOverlay.style.color = '#ffffff';
hostDecisionOverlay.style.fontFamily = 'Impact, Haettenschweiler, "Arial Black", sans-serif';
hostDecisionOverlay.style.fontSize = 'clamp(2rem, 7vw, 4.5rem)';
hostDecisionOverlay.style.letterSpacing = '0.08em';
hostDecisionOverlay.style.textShadow = '0 0 18px rgba(0, 0, 0, 0.9)';
hostDecisionOverlay.style.background = 'rgba(0, 0, 0, 0.42)';
hostDecisionOverlay.style.pointerEvents = 'none';
hostDecisionOverlay.style.zIndex = '9998';
document.body.append(hostDecisionOverlay);

const hostDecisionDialog = document.createElement('dialog');
hostDecisionDialog.style.padding = '0';
hostDecisionDialog.style.border = '1px solid rgba(255, 255, 255, 0.35)';
hostDecisionDialog.style.borderRadius = '14px';
hostDecisionDialog.style.background = 'rgba(12, 16, 22, 0.95)';
hostDecisionDialog.style.color = '#ffffff';
hostDecisionDialog.style.minWidth = 'min(92vw, 460px)';
hostDecisionDialog.style.boxShadow = '0 18px 42px rgba(0, 0, 0, 0.55)';
hostDecisionDialog.style.zIndex = '10000';

const hostDecisionPanel = document.createElement('div');
hostDecisionPanel.style.padding = '20px';
hostDecisionPanel.style.display = 'grid';
hostDecisionPanel.style.gap = '14px';

const hostDecisionTitle = document.createElement('h2');
hostDecisionTitle.textContent = 'Start Game?';
hostDecisionTitle.style.margin = '0';
hostDecisionTitle.style.fontFamily = '"Trebuchet MS", Verdana, sans-serif';
hostDecisionTitle.style.fontSize = '1.7rem';
hostDecisionTitle.style.letterSpacing = '0.04em';

const hostDecisionText = document.createElement('p');
hostDecisionText.textContent = 'Click once all players have joined';
hostDecisionText.style.margin = '0';
hostDecisionText.style.opacity = '0.92';
hostDecisionText.style.fontFamily = '"Trebuchet MS", Verdana, sans-serif';
hostDecisionText.style.fontSize = '1rem';

const hostDecisionButtons = document.createElement('div');
hostDecisionButtons.style.display = 'grid';
hostDecisionButtons.style.gridTemplateColumns = 'repeat(2, minmax(0, 1fr))';
hostDecisionButtons.style.gap = '10px';

const hostDecisionStartButton = document.createElement('button');
hostDecisionStartButton.type = 'button';
hostDecisionStartButton.textContent = 'Start';
hostDecisionStartButton.style.padding = '11px 14px';
hostDecisionStartButton.style.border = '1px solid rgba(125, 255, 174, 0.85)';
hostDecisionStartButton.style.borderRadius = '8px';
hostDecisionStartButton.style.background = '#18a957';
hostDecisionStartButton.style.color = '#f4fff8';
hostDecisionStartButton.style.fontWeight = '700';
hostDecisionStartButton.style.cursor = 'pointer';

const hostDecisionBackButton = document.createElement('button');
hostDecisionBackButton.type = 'button';
hostDecisionBackButton.textContent = 'Back';
hostDecisionBackButton.style.padding = '11px 14px';
hostDecisionBackButton.style.border = '1px solid rgba(255, 141, 141, 0.9)';
hostDecisionBackButton.style.borderRadius = '8px';
hostDecisionBackButton.style.background = '#bd2b2b';
hostDecisionBackButton.style.color = '#fff5f5';
hostDecisionBackButton.style.fontWeight = '700';
hostDecisionBackButton.style.cursor = 'pointer';

hostDecisionButtons.append(hostDecisionStartButton, hostDecisionBackButton);
hostDecisionPanel.append(hostDecisionTitle, hostDecisionText, hostDecisionButtons);
hostDecisionDialog.append(hostDecisionPanel);
document.body.append(hostDecisionDialog);

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
let isLocalHost = false;
let isAwaitingHostDecision = false;
let currentHostPromptIsInitialStart = false;
let currentRoundPhase: RoundState['phase'] = 'waiting';
let localDeathSequenceToken = 0;

const lightningSoundFiles = [
	'assets/sounds/lightning/dragon-studio-electric-discharge-386160.mp3',
	'assets/sounds/lightning/dragon-studio-lightning-spell-386163.mp3',
	'assets/sounds/lightning/dragon-studio-lightning-strike-386161.mp3',
	'assets/sounds/lightning/patricksilvey-weather-lightning-2-464187.mp3',
];

const punchSoundFiles = [
	'assets/sounds/punch/freesound_community-punch-2-37333.mp3',
	'assets/sounds/punch/soraatwod-punch-416719.mp3',
];

const missSoundFiles = [
	'assets/sounds/miss/musicholder-woosh-260275.mp3',
	'assets/sounds/miss/ribhavagrawal-woosh-230554.mp3',
];

function playRandomSound(files: string[], volume = 0.5) {
	const file = files[Math.floor(Math.random() * files.length)];
	const audio = new Audio(file);
	audio.volume = volume;
	void audio.play().catch(() => {
		// Ignore autoplay failures in browsers that require user interaction.
	});
}

function playRandomLightningSound() {
	playRandomSound(lightningSoundFiles, 0.5);
}

function playRandomPunchSound() {
	playRandomSound(punchSoundFiles, 0.6);
}

function playRandomMissSound() {
	playRandomSound(missSoundFiles, 0.5);
}

function spawnLightningBolt(targetWorldPosition: THREE.Vector3) {
	const boltTopY = 10;
	const boltBottomY = Math.max(0.7, targetWorldPosition.y + 0.7);
	const pointCount = 10;
	const points: THREE.Vector3[] = [];

	for (let i = 0; i < pointCount; i++) {
		const t = i / (pointCount - 1);
		const y = THREE.MathUtils.lerp(boltTopY, boltBottomY, t);
		const jitterScale = (1 - t) * 0.28;
		const x = targetWorldPosition.x + (Math.random() * 2 - 1) * jitterScale;
		const z = targetWorldPosition.z + (Math.random() * 2 - 1) * jitterScale;
		points.push(new THREE.Vector3(x, y, z));
	}

	const boltGeometry = new THREE.BufferGeometry().setFromPoints(points);
	const boltMaterial = new THREE.LineBasicMaterial({
		color: 0xC8_EE_FF,
		transparent: true,
		opacity: 0.95,
	});
	const boltLine = new THREE.Line(boltGeometry, boltMaterial);
	scene.add(boltLine);

	const flash = new THREE.Mesh(
		new THREE.SphereGeometry(0.45, 12, 12),
		new THREE.MeshBasicMaterial({
			color: 0xE9_FB_FF,
			transparent: true,
			opacity: 0.88,
		}),
	);
	flash.position.set(targetWorldPosition.x, boltBottomY, targetWorldPosition.z);
	scene.add(flash);

	setTimeout(() => {
		scene.remove(boltLine);
		scene.remove(flash);
		boltGeometry.dispose();
		boltMaterial.dispose();
		flash.geometry.dispose();
		(flash.material as THREE.Material).dispose();
	}, 130);
}

function showHostDecisionDialog() {
	hostDecisionTitle.textContent = currentHostPromptIsInitialStart ? 'Start Game?' : 'Play Again?';
	hostDecisionText.textContent = currentHostPromptIsInitialStart
		? 'Click once all players have joined'
		: 'The game has ended. Start another round?';
	if (!hostDecisionDialog.open) {
		hostDecisionDialog.showModal();
	}
}

function hideHostDecisionDialog() {
	if (hostDecisionDialog.open) {
		hostDecisionDialog.close();
	}
}

hostDecisionDialog.addEventListener('cancel', event => {
	event.preventDefault();
});

hostDecisionStartButton.addEventListener('click', () => {
	if (!isAwaitingHostDecision) {
		return;
	}

	hideHostDecisionDialog();
	sendHostGameDecision(true);
});

hostDecisionBackButton.addEventListener('click', () => {
	if (!isAwaitingHostDecision) {
		return;
	}

	hideHostDecisionDialog();
	sendHostGameDecision(false);
});

function updateHostDecisionOverlay(roundState: RoundState) {
	const showWaitingForHost = roundState.phase === 'hostPrompt' && !isLocalHost;
	hostDecisionOverlay.style.display = showWaitingForHost ? 'flex' : 'none';
	deadOverlay.style.display = isLocalDead && !showWaitingForHost ? 'flex' : 'none';
}

function refreshStatusOverlays() {
	const showWaitingForHost = currentRoundPhase === 'hostPrompt' && !isLocalHost;
	hostDecisionOverlay.style.display = showWaitingForHost ? 'flex' : 'none';
	deadOverlay.style.display = isLocalDead && !showWaitingForHost ? 'flex' : 'none';
}

function setLocalDead(nextDead: boolean) {
	if (!nextDead) {
		localDeathSequenceToken++;
	}

	isLocalDead = nextDead;
	player.visible = !nextDead;
	refreshStatusOverlays();
}

function playDeathAnimation(
	targetMixer: THREE.AnimationMixer | undefined,
	targetActions: Record<string, THREE.AnimationAction>,
	currentPlayingAction: THREE.AnimationAction | undefined,
	assignCurrentAction: (action: THREE.AnimationAction) => void,
) {
	if (!targetMixer || !targetActions._death) {
		return;
	}

	if (currentPlayingAction && currentPlayingAction !== targetActions._death) {
		currentPlayingAction.fadeOut(0.03);
	}

	targetActions._death.reset();
	targetActions._death.setLoop(THREE.LoopOnce, 1);
	targetActions._death.clampWhenFinished = true;
	targetActions._death.play();
	assignCurrentAction(targetActions._death);
}

function runDeathSequence(parameters: {
	worldPosition: THREE.Vector3;
	playDeath: () => void;
	finalizeDeath: () => void;
	isStale: () => boolean;
}) {
	parameters.playDeath();

	setTimeout(() => {
		if (parameters.isStale()) {
			return;
		}

		spawnLightningBolt(parameters.worldPosition);
		playRandomLightningSound();
	}, 10);

	setTimeout(() => {
		if (parameters.isStale()) {
			return;
		}

		parameters.finalizeDeath();
	}, 40);
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
const obstacleModelsDir = 'assets/models/obstacles/';
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

		// Pretty sure most of these are not needed since I got new assets but not worth the time making cleaner.
		const walkKey = Object.keys(actions).find(n => /walk/i.test(n));
		const jumpKey = Object.keys(actions).find(n => /jump/i.test(n));
		const idleKeys = Object.keys(actions).filter(n => /idle/i.test(n));
		const reservedKeys = new Set([walkKey, jumpKey, ...idleKeys].filter(Boolean));
		const attackKey = Object.keys(actions).find(n => /attack|bite|hit|punch|swipe|scratch|strike|claw|snap|headbutt/i.test(n))
			?? Object.keys(actions).find(n => !reservedKeys.has(n));
		const deathKey = Object.keys(actions).find(n => /death|die|dead|ko|defeat/i.test(n));

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

		if (deathKey) {
			actions._death = actions[deathKey];
			actions._death.setLoop(THREE.LoopOnce, 1);
			actions._death.clampWhenFinished = true;
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
	deathSequenceToken: number;
};

type ZoneVisual = {
	shadow: THREE.Mesh;
	label: THREE.Sprite;
	labelText: string;
};

type ObstacleRuntime = {
	group: THREE.Group;
	visualRoot: THREE.Group;
	data: ObstacleData;
	loadToken: number;
	lastModelFile: string;
	barrelRoll: number;
	lastPosition: THREE.Vector3;
};

const remotePlayers = new Map<string, RemotePlayer>();
const zoneVisuals = new Map<number, ZoneVisual>();
const obstacleRuntimes = new Map<string, ObstacleRuntime>();

const obstacleVisualYOffset: Record<ObstacleData['kind'], number> = {
	cone: 0,
	box: -1.22,
	barrel: 0,
};

function createObstacleFallbackMesh(data: ObstacleData): THREE.Object3D {
	if (data.kind === 'cone') {
		const cone = new THREE.Mesh(
			new THREE.ConeGeometry(Math.max(0.25, data.radius), 1.1, 18),
			new THREE.MeshStandardMaterial({color: 0xEC_7B_28}),
		);
		cone.position.y = 0.55;
		cone.castShadow = true;
		cone.receiveShadow = true;
		return cone;
	}

	if (data.kind === 'box') {
		const box = new THREE.Mesh(
			new THREE.BoxGeometry(data.radius * 1.8, 1.1, data.radius * 1.8),
			new THREE.MeshStandardMaterial({color: 0x86_6A_44}),
		);
		box.position.y = 0.55;
		box.castShadow = true;
		box.receiveShadow = true;
		return box;
	}

	const barrel = new THREE.Mesh(
		new THREE.CylinderGeometry(data.radius, data.radius, 1.25, 20),
		new THREE.MeshStandardMaterial({color: 0x6E_88_97}),
	);
	barrel.position.y = 0.62;
	barrel.castShadow = true;
	barrel.receiveShadow = true;
	return barrel;
}

function loadObstacleModel(runtime: ObstacleRuntime) {
	runtime.loadToken++;
	const {loadToken} = runtime;
	runtime.lastModelFile = runtime.data.modelFile;
	disposeGroupContents(runtime.visualRoot);
	runtime.visualRoot.add(createObstacleFallbackMesh(runtime.data));

	loader.load(obstacleModelsDir + runtime.data.modelFile, gltf => {
		if (runtime.loadToken !== loadToken) {
			return;
		}

		disposeGroupContents(runtime.visualRoot);
		const modelRoot = gltf.scene;
		if (runtime.data.kind === 'box') {
			modelRoot.scale.setScalar(0.8);
		}

		modelRoot.traverse(node => {
			if ((node as THREE.Mesh).isMesh) {
				node.castShadow = true;
				node.receiveShadow = true;
			}
		});

		// Align imported mesh pivot to gameplay collision center on XZ and rest on platform Y=0.
		const bounds = new THREE.Box3().setFromObject(modelRoot);
		if (isFinite(bounds.min.x) && isFinite(bounds.min.y) && isFinite(bounds.min.z)) {
			const center = new THREE.Vector3();
			bounds.getCenter(center);
			modelRoot.position.x -= center.x;
			modelRoot.position.z -= center.z;
			modelRoot.position.y -= bounds.min.y;
			modelRoot.position.y += obstacleVisualYOffset[runtime.data.kind];
		}

		runtime.visualRoot.add(modelRoot);
	});
}

function removeObstacleRuntime(id: string) {
	const runtime = obstacleRuntimes.get(id);
	if (!runtime) {
		return;
	}

	disposeGroupContents(runtime.visualRoot);
	scene.remove(runtime.group);
	obstacleRuntimes.delete(id);
}

function syncObstacles(obstacles: ObstacleData[]) {
	const liveIds = new Set<string>();
	for (const data of obstacles) {
		liveIds.add(data.id);
		let runtime = obstacleRuntimes.get(data.id);
		if (runtime) {
			runtime.data = data;
		} else {
			const group = new THREE.Group();
			const visualRoot = new THREE.Group();
			group.add(visualRoot);
			group.position.set(data.x, data.y, data.z);
			group.rotation.y = data.rotationY;
			scene.add(group);
			runtime = {
				group,
				visualRoot,
				data,
				loadToken: 0,
				lastModelFile: '',
				barrelRoll: 0,
				lastPosition: new THREE.Vector3(data.x, data.y, data.z),
			};
			obstacleRuntimes.set(data.id, runtime);
			loadObstacleModel(runtime);
		}

		if (runtime.lastModelFile !== data.modelFile) {
			loadObstacleModel(runtime);
		}
	}

	for (const id of obstacleRuntimes.keys()) {
		if (liveIds.has(id)) {
			continue;
		}

		removeObstacleRuntime(id);
	}
}

function resolveLocalPlayerObstacleCollisions() {
	if (isLocalDead) {
		return;
	}

	for (const runtime of obstacleRuntimes.values()) {
		const obstacle = runtime.data;
		if (obstacle.y > 0.01) {
			continue;
		}

		if (obstacle.kind === 'box') {
			const topY = obstacle.y + obstacle.height;
			const boxHalf = obstacle.radius;
			const expandedHalf = boxHalf + playerRadius;
			const localX = player.position.x - obstacle.x;
			const localZ = player.position.z - obstacle.z;
			const insideExpanded = Math.abs(localX) < expandedHalf && Math.abs(localZ) < expandedHalf;
			if (!insideExpanded) {
				continue;
			}

			const isOnTop
				= player.position.y >= topY - 0.12
					&& Math.abs(localX) <= boxHalf - 0.02
					&& Math.abs(localZ) <= boxHalf - 0.02;
			if (isOnTop) {
				continue;
			}

			const penetrationX = expandedHalf - Math.abs(localX);
			const penetrationZ = expandedHalf - Math.abs(localZ);
			if (penetrationX <= penetrationZ) {
				const directionX = localX === 0 ? (Math.random() < 0.5 ? -1 : 1) : Math.sign(localX);
				player.position.x += directionX * penetrationX;
			} else {
				const directionZ = localZ === 0 ? (Math.random() < 0.5 ? -1 : 1) : Math.sign(localZ);
				player.position.z += directionZ * penetrationZ;
			}

			continue;
		}

		if (obstacle.kind === 'barrel') {
			const barrelTop = obstacle.y + obstacle.radius * 2;
			const aboveBarrelTop = player.position.y >= barrelTop - 0.02;
			if (aboveBarrelTop) {
				continue;
			}

			const axisX = Math.cos(obstacle.rotationY);
			const axisZ = -Math.sin(obstacle.rotationY);
			const halfLength = obstacle.height * 0.5;
			const dx = player.position.x - obstacle.x;
			const dz = player.position.z - obstacle.z;
			const along = dx * axisX + dz * axisZ;
			const clampedAlong = Math.max(-halfLength, Math.min(halfLength, along));
			const nearestX = obstacle.x + axisX * clampedAlong;
			const nearestZ = obstacle.z + axisZ * clampedAlong;
			const offsetX = player.position.x - nearestX;
			const offsetZ = player.position.z - nearestZ;
			const radialDistance = Math.hypot(offsetX, offsetZ);
			const minDistance = playerRadius + obstacle.radius;
			if (radialDistance >= minDistance) {
				continue;
			}

			const overlap = minDistance - Math.max(radialDistance, 0.0001);
			const nx = radialDistance <= 0.0001 ? axisX : offsetX / radialDistance;
			const nz = radialDistance <= 0.0001 ? axisZ : offsetZ / radialDistance;
			player.position.x += nx * overlap;
			player.position.z += nz * overlap;
			continue;
		}

		const dx = player.position.x - obstacle.x;
		const dz = player.position.z - obstacle.z;
		const distance = Math.hypot(dx, dz);
		const minDistance = playerRadius + obstacle.radius;
		if (distance >= minDistance) {
			continue;
		}

		const overlap = minDistance - Math.max(distance, 0.0001);
		const nx = distance <= 0.0001 ? Math.cos(Math.random() * Math.PI * 2) : dx / distance;
		const nz = distance <= 0.0001 ? Math.sin(Math.random() * Math.PI * 2) : dz / distance;
		player.position.x += nx * overlap;
		player.position.z += nz * overlap;
	}
}

function getSupportHeightAtPosition(x: number, z: number, y: number, velocityY: number): number {
	let supportHeight = 0;
	for (const runtime of obstacleRuntimes.values()) {
		const obstacle = runtime.data;
		if (obstacle.y > 0.01) {
			continue;
		}

		if (obstacle.kind !== 'box' && obstacle.kind !== 'barrel') {
			continue;
		}

		if (obstacle.kind === 'barrel') {
			const axisX = Math.cos(obstacle.rotationY);
			const axisZ = -Math.sin(obstacle.rotationY);
			const halfLength = obstacle.height * 0.5;
			const dx = x - obstacle.x;
			const dz = z - obstacle.z;
			const along = dx * axisX + dz * axisZ;
			const clampedAlong = Math.max(-halfLength, Math.min(halfLength, along));
			const nearestX = obstacle.x + axisX * clampedAlong;
			const nearestZ = obstacle.z + axisZ * clampedAlong;
			const radialDistance = Math.hypot(x - nearestX, z - nearestZ);
			if (radialDistance > obstacle.radius - 0.03) {
				continue;
			}

			const topY = obstacle.y + obstacle.radius * 2;
			const canLandOnTop = velocityY <= 0 && y <= topY + 0.28 && y >= topY - 0.22;
			if (!canLandOnTop) {
				continue;
			}

			supportHeight = Math.max(supportHeight, topY);
			continue;
		}

		const dx = x - obstacle.x;
		const dz = z - obstacle.z;
		const boxHalf = obstacle.radius;
		const insideTopArea = Math.abs(dx) <= boxHalf - 0.03 && Math.abs(dz) <= boxHalf - 0.03;
		if (!insideTopArea) {
			continue;
		}

		const topY = obstacle.y + obstacle.height;
		const canLandOnTop = velocityY <= 0 && y <= topY + 0.28 && y >= topY - 0.22;
		if (!canLandOnTop) {
			continue;
		}

		supportHeight = Math.max(supportHeight, topY);
	}

	return supportHeight;
}

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
	currentRoundPhase = roundState.phase;
	const secondsLeft = Math.ceil(roundState.timeLeftMs / 1000);
	switch (roundState.phase) {
		case 'question': {
			roundTimer.textContent = `Round ${roundState.round} | ${secondsLeft}s`;
			roundQuestion.textContent = roundState.question;

			break;
		}

		case 'break': {
			roundTimer.textContent = `Break | ${secondsLeft}s`;
			roundQuestion.textContent = 'Next question incoming...';

			break;
		}

		case 'hostPrompt': {
			roundTimer.textContent = currentHostPromptIsInitialStart ? 'Ready' : 'Game Over';
			roundQuestion.textContent = isLocalHost
				? (currentHostPromptIsInitialStart
					? 'Click Start when everyone has joined.'
					: 'Choose if you want to play again.')
				: 'Waiting for host';

			break;
		}

		default: {
			roundTimer.textContent = 'Waiting';
			roundQuestion.textContent = roundState.question || 'Waiting for players';
		}
	}

	updateHostDecisionOverlay(roundState);
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
		const rDeathKey = Object.keys(remote.actions).find(n => /death|die|dead|ko|defeat/i.test(n));

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

		if (rDeathKey) {
			remote.actions._death = remote.actions[rDeathKey];
			remote.actions._death.setLoop(THREE.LoopOnce, 1);
			remote.actions._death.clampWhenFinished = true;
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
		deathSequenceToken: 0,
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
	const justDied = !remote.dead && data.dead;
	remote.dead = data.dead;
	if (!data.dead) {
		remote.deathSequenceToken++;
		remote.group.visible = true;
	}

	if (data.modelFile && data.modelFile !== remote.modelFile) {
		loadRemoteModel(remote, data.modelFile);
	}

	if (justDied) {
		const token = ++remote.deathSequenceToken;
		remote.group.visible = true;
		const worldPosition = new THREE.Vector3();
		remote.group.getWorldPosition(worldPosition);

		runDeathSequence({
			worldPosition,
			playDeath() {
				playDeathAnimation(remote.mixer, remote.actions, remote.currentAction, action => {
					remote.currentAction = action;
				});
			},
			finalizeDeath() {
				remote.group.visible = false;
			},
			isStale: () => token !== remote.deathSequenceToken || !remote.dead,
		});
		return;
	}

	if (data.dead) {
		remote.group.visible = false;
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

const gamePlayerId = new URLSearchParams(globalThis.location.search).get('gamePlayerId') ?? '';
connect({
	onInit(payload) {
		socketId = payload.id;
		localModelFile = payload.modelFile;
		loadLocalModel(localModelFile);
		if (payload.roundState) {
			applyRoundState(payload.roundState);
		}

		if (payload.obstacles) {
			syncObstacles(payload.obstacles);
		}

		// Apply server-assigned spawn position
		const me = payload.players[payload.id];
		if (me) {
			player.position.set(me.x, me.y, me.z);
			setLocalDead(me.dead);
			isLocalHost = me.host;
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

			const justDied = !isLocalDead && playerData.dead;
			if (justDied) {
				const token = ++localDeathSequenceToken;
				isLocalDead = true;
				player.visible = true;
				runDeathSequence({
					worldPosition: player.getWorldPosition(new THREE.Vector3()),
					playDeath() {
						playDeathAnimation(mixer, actions, currentAction, action => {
							currentAction = action;
							currentAnimName = 'death';
						});
					},
					finalizeDeath() {
						setLocalDead(true);
					},
					isStale: () => token !== localDeathSequenceToken || !isLocalDead,
				});
			} else {
				setLocalDead(playerData.dead);
			}

			isLocalHost = playerData.host;
			refreshStatusOverlays();
			if (!isLocalHost) {
				isAwaitingHostDecision = false;
				hideHostDecisionDialog();
			}

			player.position.set(playerData.x, playerData.y, playerData.z);
			player.rotation.y = playerData.rotationY;
			velocity.y = playerData.velocityY;
			onGround = player.position.y <= getSupportHeightAtPosition(player.position.x, player.position.z, player.position.y, velocity.y) + 0.0001;
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
		if (data.hit) {
			playRandomPunchSound();
		} else {
			playRandomMissSound();
		}

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
		if (state.phase !== 'hostPrompt') {
			isAwaitingHostDecision = false;
			hideHostDecisionDialog();
		}
	},
	onHostGamePrompt(payload) {
		if (!isLocalHost || isAwaitingHostDecision) {
			return;
		}

		currentHostPromptIsInitialStart = payload.initialStart;
		isAwaitingHostDecision = true;
		showHostDecisionDialog();
	},
	onObstaclesState(obstacles) {
		syncObstacles(obstacles);
	},
	onScoreboard(rows) {
		renderScoreboard(rows);
	},
	onGameEnded() {
		window.parent?.postMessage({type: 'gameEnded'}, '*');
	},
}, gamePlayerId);

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

	const controlsLocked = currentRoundPhase === 'hostPrompt';
	if (controlsLocked) {
		velocity.y = 0;
		onGround = true;
		isAttacking = false;
		attackTimer = 0;
	}

	const dir = new THREE.Vector3();
	if (!isLocalDead && !isStunned && !controlsLocked && keys.KeyW) {
		dir.z -= 1;
	}

	if (!isLocalDead && !isStunned && !controlsLocked && keys.KeyS) {
		dir.z += 1;
	}

	if (!isLocalDead && !isStunned && !controlsLocked && keys.KeyA) {
		dir.x -= 1;
	}

	if (!isLocalDead && !isStunned && !controlsLocked && keys.KeyD) {
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

	if (!isLocalDead && !isStunned && !controlsLocked && keys.Space && onGround) {
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

	if (!isLocalDead && !controlsLocked && keys.Enter && !isAttacking && !isStunned) {
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

	if (!controlsLocked) {
		velocity.y += gravity * dt;
		player.position.y += velocity.y * dt;
	}

	const supportHeight = getSupportHeightAtPosition(player.position.x, player.position.z, player.position.y, velocity.y);
	if (player.position.y <= supportHeight) {
		player.position.y = supportHeight;
		velocity.y = 0;
		onGround = true;
	} else {
		onGround = false;
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

	resolveLocalPlayerObstacleCollisions();

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

	for (const runtime of obstacleRuntimes.values()) {
		const isAirborne = runtime.data.y > 0.001;
		if (runtime.data.dynamic || isAirborne) {
			runtime.group.position.lerp(
				new THREE.Vector3(runtime.data.x, runtime.data.y, runtime.data.z),
				0.35,
			);
		} else {
			runtime.group.position.set(runtime.data.x, runtime.data.y, runtime.data.z);
		}

		const angleDiff = runtime.data.rotationY - runtime.group.rotation.y;
		runtime.group.rotation.y += angleDiff * 0.25;

		if (runtime.data.kind === 'barrel') {
			const deltaX = runtime.group.position.x - runtime.lastPosition.x;
			const deltaZ = runtime.group.position.z - runtime.lastPosition.z;
			const travelDistance = Math.hypot(deltaX, deltaZ);
			runtime.barrelRoll += travelDistance / Math.max(runtime.data.radius, 0.001);
			runtime.visualRoot.position.y = runtime.data.radius;
			runtime.visualRoot.rotation.x = runtime.barrelRoll;
			runtime.visualRoot.rotation.z = Math.PI / 2;
		} else {
			runtime.visualRoot.position.y = 0;
			runtime.visualRoot.rotation.set(0, 0, 0);
		}

		runtime.lastPosition.copy(runtime.group.position);
	}

	renderer.render(scene, camera);
}

animate();

