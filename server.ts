import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import path from 'node:path';
import express from 'express';
import {Server} from 'socket.io';

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
	cors: {
		origin: '*',
	},
});

app.use(express.static(path.join(__dirname, '..', 'dist')));
app.use(express.json());

type PlayerState = {
	id: string;
	x: number;
	y: number;
	z: number;
	rotationY: number;
	velocityY: number;
	animation: string;
	modelFile: string;
	dead: boolean;
	host: boolean;
	gamePlayerId?: string;
};

type TriviaCard = {
	question: string;
	answer: string;
};

type AnswerZone = {
	id: number;
	x: number;
	z: number;
	radius: number;
	answer: string;
	revealed: boolean;
};

type RoundState = {
	phase: 'waiting' | 'question' | 'break' | 'hostPrompt';
	round: number;
	question: string;
	timeLeftMs: number;
	revealedAnswerCount: number;
	zones: AnswerZone[];
};

type ObstacleKind = 'cone' | 'box' | 'barrel';

type ObstacleState = {
	id: string;
	kind: ObstacleKind;
	modelFile: string;
	x: number;
	y: number;
	z: number;
	rotationY: number;
	radius: number;
	height: number;
	dynamic: boolean;
	velocityY: number;
	velocityX: number;
	velocityZ: number;
};

type AnkiCollectionLike = {
	getDecks: () => Record<string, {
		getCards: () => Record<string, {
			getFront: () => string;
			getBack: () => string;
		}>;
	}>;
};

const players = new Map<string, PlayerState>();

const modelFiles = [
	'Colobus_Animations.glb',
	'Gecko_Animations.glb',
	'Herring_Animations.glb',
	'Inkfish_Animations.glb',
	'Muskrat_Animations.glb',
	'Pudu_Animations.glb',
	'Sparrow_Animations.glb',
	'Taipan_Animations.glb',
];

const spawnRange = 6;
const roundDurationMs = 10_000;
const breakDurationMs = 1000;
const answerRevealStepMs = 2000;
const roundTickMs = 100;
const broadcastIntervalMs = 200;

const zoneRadius = 1.9;
const platformHalfBound = 7.5;
const answerZoneSpawnBound = 6.8;
const playerRadius = 0.35;
const maxPermanentObstacles = 5;
const obstacleSpawnBound = 6.6;
const barrelSpeed = 3.6;
const barrelDespawnPadding = 1.2;
const obstacleSpawnHeight = 10;
const obstacleFallGravity = -28;

const obstacleModelFiles: Record<ObstacleKind, string> = {
	cone: 'traffic_cone.glb',
	box: 'free_low_poly_crate.glb',
	barrel: 'simple_oil_barrel.glb',
};

const obstacleRadii: Record<ObstacleKind, number> = {
	cone: 0.45,
	box: 0.8,
	barrel: 0.75,
};

const obstacleHeights: Record<ObstacleKind, number> = {
	cone: 1.1,
	box: 0.88,
	barrel: 1.25,
};

let triviaCards: TriviaCard[] = [];
let triviaCursor = 0;
let currentCorrectAnswer = '';
let phaseEndsAt = 0;
let lastStateBroadcastAt = 0;
let awaitingHostDecision = false;
let hostDecisionKind: 'initial' | 'replay' = 'initial';
let nextObstacleId = 1;
const obstacles = new Map<string, ObstacleState>();

const apiUrl = process.env.BEARCAT_API_URL ?? '';
const gameId = process.env.BEARCAT_GAME_ID ?? '';
let currentRoundId: string | undefined = null;

let roundState: RoundState = {
	phase: 'waiting',
	round: 0,
	question: 'Loading questions...',
	timeLeftMs: 0,
	revealedAnswerCount: 0,
	zones: [],
};

function pickModel(): string {
	return modelFiles[Math.floor(Math.random() * modelFiles.length)];
}

function sanitizeCardText(text: string): string {
	return text
		.replaceAll(/\[sound:[^\]]+]/gi, ' ')
		.replaceAll(/<[^>]*>/g, ' ')
		.replaceAll(/&nbsp;/gi, ' ')
		.replaceAll(/&amp;/gi, '&')
		.replaceAll(/&lt;/gi, '<')
		.replaceAll(/&gt;/gi, '>')
		.replaceAll(/\s+/g, ' ')
		.trim();
}

function shuffle<T>(values: T[]): T[] {
	const next = [...values];
	for (let index = next.length - 1; index > 0; index--) {
		const swapIndex = Math.floor(Math.random() * (index + 1));
		const temporary = next[index];
		next[index] = next[swapIndex];
		next[swapIndex] = temporary;
	}

	return next;
}

function uniqueNonEmpty(values: string[]): string[] {
	const seen = new Set<string>();
	const next: string[] = [];
	for (const value of values) {
		const normalized = value.trim();
		if (!normalized || seen.has(normalized)) {
			continue;
		}

		seen.add(normalized);
		next.push(normalized);
	}

	return next;
}

async function loadTriviaCardsFromApkg(): Promise<TriviaCard[]> {
	const apkgPath = path.join(process.cwd(), 'questions.apkg');
	const packageBytes = await readFile(apkgPath);

	type ReadAnkiPackage = (ankiPackage: Blob) => Promise<{
		collection: AnkiCollectionLike;
		media: Record<string, Blob>;
	}>;

	// eslint-disable-next-line no-eval -- anki-reader is ESM-only; this keeps dynamic import working from CJS output.
	const importModule = (0, eval)('(specifier) => import(specifier)') as (specifier: string) => Promise<{
		readAnkiPackage: ReadAnkiPackage;
	}>;
	const {readAnkiPackage} = await importModule('anki-reader');
	const extractedPackage = await readAnkiPackage(new Blob([packageBytes]));

	const loadedCards: TriviaCard[] = [];
	for (const deck of Object.values(extractedPackage.collection.getDecks())) {
		for (const card of Object.values(deck.getCards())) {
			const question = sanitizeCardText(card.getFront());
			const answer = sanitizeCardText(card.getBack());
			if (!question || !answer) {
				continue;
			}

			loadedCards.push({question, answer});
		}
	}

	if (loadedCards.length === 0) {
		throw new Error('questions.apkg was loaded but contained no usable cards.');
	}

	return loadedCards;
}

function setWaitingState(message: string) {
	roundState = {
		phase: 'waiting',
		round: roundState.round,
		question: message,
		timeLeftMs: 0,
		revealedAnswerCount: 0,
		zones: [],
	};
}

function serializeObstacles(): ObstacleState[] {
	return [...obstacles.values()];
}

function broadcastObstaclesState() {
	io.emit('obstaclesState', serializeObstacles());
}

function broadcastRoundState(force = false) {
	const now = Date.now();
	if (!force && now - lastStateBroadcastAt < broadcastIntervalMs) {
		return;
	}

	lastStateBroadcastAt = now;
	io.emit('roundState', roundState);
}

function getWrongAnswers(correctAnswer: string, count: number): string[] {
	const answerPool = uniqueNonEmpty(triviaCards.map(card => card.answer));
	const candidates = shuffle(answerPool.filter(answer => answer !== correctAnswer));
	const wrongAnswers = candidates.slice(0, count);

	while (wrongAnswers.length < count) {
		wrongAnswers.push(`Wrong answer ${wrongAnswers.length + 1}`);
	}

	return wrongAnswers;
}

function randomAnswerZones(answers: string[]): AnswerZone[] {
	const zones: AnswerZone[] = [];
	const minCenterDistance = zoneRadius * 2;
	const maxAttemptsPerZone = 200;

	for (const [index, answer] of answers.entries()) {
		let placed = false;
		for (let attempt = 0; attempt < maxAttemptsPerZone; attempt++) {
			const candidateX = (Math.random() * 2 - 1) * answerZoneSpawnBound;
			const candidateZ = (Math.random() * 2 - 1) * answerZoneSpawnBound;

			const overlapsExisting = zones.some(existing => {
				const dx = candidateX - existing.x;
				const dz = candidateZ - existing.z;
				const distance = Math.hypot(dx, dz);
				return distance < minCenterDistance;
			});

			if (overlapsExisting) {
				continue;
			}

			zones.push({
				id: index,
				x: candidateX,
				z: candidateZ,
				radius: zoneRadius,
				answer,
				revealed: index === 0,
			});
			placed = true;
			break;
		}

		if (placed) {
			continue;
		}

		// Fallback deterministic placement if random sampling fails repeatedly.
		const fallbackPoints = [
			{x: -5.2, z: -5.2},
			{x: 5.2, z: -5.2},
			{x: -5.2, z: 5.2},
			{x: 5.2, z: 5.2},
		];
		const fallback = fallbackPoints[index % fallbackPoints.length];
		zones.push({
			id: index,
			x: fallback.x,
			z: fallback.z,
			radius: zoneRadius,
			answer,
			revealed: index === 0,
		});
	}

	return zones;
}

function alivePlayerCount(): number {
	let count = 0;
	for (const player of players.values()) {
		if (!player.dead) {
			count++;
		}
	}

	return count;
}

function getHostPlayer(): PlayerState | undefined {
	for (const player of players.values()) {
		if (player.host) {
			return player;
		}
	}

	return undefined;
}

function ensureHostAssigned() {
	const host = getHostPlayer();
	if (host || players.size === 0) {
		return;
	}

	const nextHost = players.values().next().value as PlayerState | undefined;
	if (!nextHost) {
		return;
	}

	nextHost.host = true;
	io.emit('playerMoved', nextHost);
}

function clampToPlatform(value: number): number {
	return Math.max(-platformHalfBound, Math.min(platformHalfBound, value));
}

function countPermanentObstacles(): number {
	let count = 0;
	for (const obstacle of obstacles.values()) {
		if (!obstacle.dynamic) {
			count++;
		}
	}

	return count;
}

function findObstacleSpawnPosition(radius: number): {x: number; z: number} {
	const maxAttempts = 180;
	for (let attempt = 0; attempt < maxAttempts; attempt++) {
		const candidateX = (Math.random() * 2 - 1) * obstacleSpawnBound;
		const candidateZ = (Math.random() * 2 - 1) * obstacleSpawnBound;

		const overlapsObstacle = [...obstacles.values()].some(obstacle => {
			const dx = candidateX - obstacle.x;
			const dz = candidateZ - obstacle.z;
			return Math.hypot(dx, dz) < radius + obstacle.radius + 0.35;
		});
		if (overlapsObstacle) {
			continue;
		}

		const overlapsPlayer = [...players.values()].some(player => {
			const dx = candidateX - player.x;
			const dz = candidateZ - player.z;
			return Math.hypot(dx, dz) < radius + playerRadius + 0.55;
		});
		if (overlapsPlayer) {
			continue;
		}

		return {x: candidateX, z: candidateZ};
	}

	return {
		x: (Math.random() * 2 - 1) * (obstacleSpawnBound * 0.7),
		z: (Math.random() * 2 - 1) * (obstacleSpawnBound * 0.7),
	};
}

function spawnPermanentObstacle(kind: 'cone' | 'box') {
	if (countPermanentObstacles() >= maxPermanentObstacles) {
		return;
	}

	const radius = obstacleRadii[kind];
	const spawn = findObstacleSpawnPosition(radius);
	const obstacle: ObstacleState = {
		id: `obs-${nextObstacleId++}`,
		kind,
		modelFile: obstacleModelFiles[kind],
		x: spawn.x,
		y: obstacleSpawnHeight,
		z: spawn.z,
		rotationY: Math.random() * Math.PI * 2,
		radius,
		height: obstacleHeights[kind],
		dynamic: false,
		velocityY: 0,
		velocityX: 0,
		velocityZ: 0,
	};
	obstacles.set(obstacle.id, obstacle);
	broadcastObstaclesState();
}

function spawnRollingBarrel() {
	const kind: ObstacleKind = 'barrel';
	const radius = obstacleRadii[kind];
	const spawn = findObstacleSpawnPosition(radius);
	const directionAngle = Math.random() * Math.PI * 2;
	const velocityX = Math.sin(directionAngle) * barrelSpeed;
	const velocityZ = Math.cos(directionAngle) * barrelSpeed;
	const obstacle: ObstacleState = {
		id: `obs-${nextObstacleId++}`,
		kind,
		modelFile: obstacleModelFiles[kind],
		x: spawn.x,
		y: obstacleSpawnHeight,
		z: spawn.z,
		rotationY: directionAngle,
		radius,
		height: obstacleHeights[kind],
		dynamic: true,
		velocityY: 0,
		velocityX,
		velocityZ,
	};
	obstacles.set(obstacle.id, obstacle);
	broadcastObstaclesState();
}

function spawnObstacleAtRoundEnd(roundNumber: number) {
	if (countPermanentObstacles() >= maxPermanentObstacles) {
		spawnRollingBarrel();
		return;
	}

	if (roundNumber % 5 !== 0) {
		return;
	}

	const pick = Math.floor(Math.random() * 3);
	if (pick === 0) {
		spawnPermanentObstacle('cone');
		return;
	}

	if (pick === 1) {
		spawnPermanentObstacle('box');
		return;
	}

	spawnRollingBarrel();
}

function spawnObstacleByKind(kind: ObstacleKind | 'random'): void {
	if (kind === 'cone' || kind === 'box') {
		spawnPermanentObstacle(kind);
		return;
	}

	if (kind === 'barrel') {
		spawnRollingBarrel();
		return;
	}

	if (countPermanentObstacles() >= maxPermanentObstacles) {
		spawnRollingBarrel();
		return;
	}

	const roll = Math.floor(Math.random() * 3);
	if (roll === 0) {
		spawnPermanentObstacle('cone');
		return;
	}

	if (roll === 1) {
		spawnPermanentObstacle('box');
		return;
	}

	spawnRollingBarrel();
}

function applyObstacleCollisions(player: PlayerState, includeDynamic: boolean): boolean {
	let changed = false;

	for (const obstacle of obstacles.values()) {
		if (!includeDynamic && obstacle.dynamic) {
			continue;
		}

		if (obstacle.y > 0.01) {
			continue;
		}

		if (obstacle.kind === 'box') {
			const topY = obstacle.y + obstacle.height;
			const boxHalf = obstacle.radius;
			const expandedHalf = boxHalf + playerRadius;
			const localX = player.x - obstacle.x;
			const localZ = player.z - obstacle.z;
			const insideExpanded = Math.abs(localX) < expandedHalf && Math.abs(localZ) < expandedHalf;
			if (!insideExpanded) {
				continue;
			}

			const isOnTop
				= player.y >= topY - 0.12
					&& Math.abs(localX) <= boxHalf - 0.02
					&& Math.abs(localZ) <= boxHalf - 0.02;
			if (isOnTop) {
				continue;
			}

			const penetrationX = expandedHalf - Math.abs(localX);
			const penetrationZ = expandedHalf - Math.abs(localZ);
			if (penetrationX <= penetrationZ) {
				const directionX = localX === 0 ? (Math.random() < 0.5 ? -1 : 1) : Math.sign(localX);
				player.x += directionX * penetrationX;
			} else {
				const directionZ = localZ === 0 ? (Math.random() < 0.5 ? -1 : 1) : Math.sign(localZ);
				player.z += directionZ * penetrationZ;
			}

			changed = true;
			continue;
		}

		if (obstacle.kind === 'barrel') {
			const barrelTop = obstacle.y + obstacle.radius * 2;
			const aboveBarrelTop = player.y >= barrelTop - 0.02;
			if (aboveBarrelTop) {
				continue;
			}

			const axisX = Math.cos(obstacle.rotationY);
			const axisZ = -Math.sin(obstacle.rotationY);
			const halfLength = obstacle.height * 0.5;
			const dx = player.x - obstacle.x;
			const dz = player.z - obstacle.z;
			const along = dx * axisX + dz * axisZ;
			const clampedAlong = Math.max(-halfLength, Math.min(halfLength, along));
			const nearestX = obstacle.x + axisX * clampedAlong;
			const nearestZ = obstacle.z + axisZ * clampedAlong;
			const offsetX = player.x - nearestX;
			const offsetZ = player.z - nearestZ;
			const radialDistance = Math.hypot(offsetX, offsetZ);
			const minDistance = playerRadius + obstacle.radius;
			if (radialDistance >= minDistance) {
				continue;
			}

			const overlap = minDistance - Math.max(radialDistance, 0.0001);
			const nx = radialDistance <= 0.0001 ? axisX : offsetX / radialDistance;
			const nz = radialDistance <= 0.0001 ? axisZ : offsetZ / radialDistance;
			player.x += nx * overlap;
			player.z += nz * overlap;
			changed = true;
			continue;
		}

		const minDistance = playerRadius + obstacle.radius;
		const dx = player.x - obstacle.x;
		const dz = player.z - obstacle.z;
		const distance = Math.hypot(dx, dz);
		if (distance >= minDistance) {
			continue;
		}

		const overlap = minDistance - Math.max(distance, 0.0001);
		const nx = distance <= 0.0001 ? Math.cos(Math.random() * Math.PI * 2) : dx / distance;
		const nz = distance <= 0.0001 ? Math.sin(Math.random() * Math.PI * 2) : dz / distance;
		player.x += nx * overlap;
		player.z += nz * overlap;
		changed = true;
	}

	const boundedX = clampToPlatform(player.x);
	const boundedZ = clampToPlatform(player.z);
	if (boundedX !== player.x || boundedZ !== player.z) {
		player.x = boundedX;
		player.z = boundedZ;
		changed = true;
	}

	return changed;
}

function tickObstacles() {
	if (obstacles.size === 0) {
		return;
	}

	const dtSeconds = roundTickMs / 1000;
	let obstaclesChanged = false;
	const movedPlayers: PlayerState[] = [];

	for (const obstacle of obstacles.values()) {
		if (obstacle.y > 0 || obstacle.velocityY !== 0) {
			obstacle.velocityY += obstacleFallGravity * dtSeconds;
			obstacle.y += obstacle.velocityY * dtSeconds;
			if (obstacle.y <= 0) {
				obstacle.y = 0;
				obstacle.velocityY = 0;
			}

			obstaclesChanged = true;
		}

		if (!obstacle.dynamic || obstacle.y > 0) {
			continue;
		}

		obstacle.x += obstacle.velocityX * dtSeconds;
		obstacle.z += obstacle.velocityZ * dtSeconds;
		obstacle.rotationY = Math.atan2(obstacle.velocityX, obstacle.velocityZ);
		obstaclesChanged = true;

		for (const player of players.values()) {
			const beforeX = player.x;
			const beforeZ = player.z;
			const moved = applyObstacleCollisions(player, true);
			if (moved && (Math.abs(player.x - beforeX) > 0.0001 || Math.abs(player.z - beforeZ) > 0.0001)) {
				movedPlayers.push(player);
			}
		}

		const isOffPlatform
			= Math.abs(obstacle.x) > platformHalfBound + barrelDespawnPadding
				|| Math.abs(obstacle.z) > platformHalfBound + barrelDespawnPadding;
		if (isOffPlatform) {
			obstacles.delete(obstacle.id);
			obstaclesChanged = true;
		}
	}

	for (const player of movedPlayers) {
		io.emit('playerMoved', player);
	}

	if (obstaclesChanged) {
		broadcastObstaclesState();
	}
}

function startHostDecisionPrompt(kind: 'initial' | 'replay') {
	awaitingHostDecision = true;
	hostDecisionKind = kind;
	roundState = {
		phase: 'hostPrompt',
		round: roundState.round,
		question: 'Waiting for host',
		timeLeftMs: 0,
		revealedAnswerCount: 0,
		zones: [],
	};
	broadcastRoundState(true);

	const host = getHostPlayer();
	if (!host) {
		return;
	}

	io.to(host.id).emit('hostGamePrompt', {initialStart: kind === 'initial'});
}

function restartGame() {
	awaitingHostDecision = false;
	roundState.round = 0;

	for (const player of players.values()) {
		player.dead = false;
		player.x = (Math.random() * 2 - 1) * spawnRange;
		player.y = 0;
		player.z = (Math.random() * 2 - 1) * spawnRange;
		player.rotationY = 0;
		player.velocityY = 0;
		player.animation = 'idle';
		io.emit('playerMoved', player);
	}

	startQuestionRound();
}

function startQuestionRound() {
	if (players.size === 0) {
		setWaitingState('Waiting for players...');
		broadcastRoundState(true);
		return;
	}

	if (triviaCards.length === 0) {
		setWaitingState('No questions available in questions.apkg');
		broadcastRoundState(true);
		return;
	}

	const card = triviaCards[triviaCursor % triviaCards.length];
	triviaCursor++;
	currentCorrectAnswer = card.answer;

	const answers = shuffle([card.answer, ...getWrongAnswers(card.answer, 3)]);
	const zones = randomAnswerZones(answers);

	roundState = {
		phase: 'question',
		round: roundState.round + 1,
		question: card.question,
		timeLeftMs: roundDurationMs,
		revealedAnswerCount: 1,
		zones,
	};
	phaseEndsAt = Date.now() + roundDurationMs;
	broadcastRoundState(true);
}

function eliminatePlayersOutsideCorrectZone() {
	const correctZone = roundState.zones.find(zone => zone.answer === currentCorrectAnswer);
	if (!correctZone) {
		return;
	}

	for (const player of players.values()) {
		if (player.dead) {
			continue;
		}

		const dx = player.x - correctZone.x;
		const dz = player.z - correctZone.z;
		const inSafeZone = Math.hypot(dx, dz) <= correctZone.radius;
		if (inSafeZone) {
			continue;
		}

		player.dead = true;
		player.animation = 'idle';
		io.emit('playerMoved', player);
	}
}

function startBreakRound() {
	roundState = {
		phase: 'break',
		round: roundState.round,
		question: 'Prepare for the next question',
		timeLeftMs: breakDurationMs,
		revealedAnswerCount: 0,
		zones: [],
	};
	phaseEndsAt = Date.now() + breakDurationMs;
	broadcastRoundState(true);
}

function tickRoundLoop() {
	tickObstacles();

	if (awaitingHostDecision) {
		if (!getHostPlayer()) {
			ensureHostAssigned();
			const reassignedHost = getHostPlayer();
			if (reassignedHost) {
				io.to(reassignedHost.id).emit('hostGamePrompt', {initialStart: hostDecisionKind === 'initial'});
			}
		}

		return;
	}

	if (players.size === 0) {
		if (roundState.phase !== 'waiting') {
			setWaitingState('Waiting for players...');
			broadcastRoundState(true);
		}

		return;
	}

	if (roundState.phase === 'waiting') {
		startHostDecisionPrompt('initial');
		return;
	}

	if (roundState.phase === 'question') {
		const now = Date.now();
		const timeLeftMs = Math.max(0, phaseEndsAt - now);
		const elapsedMs = roundDurationMs - timeLeftMs;
		const revealedAnswerCount = Math.max(1, Math.min(4, Math.floor(elapsedMs / answerRevealStepMs) + 1));

		roundState.timeLeftMs = timeLeftMs;
		roundState.revealedAnswerCount = revealedAnswerCount;
		roundState.zones = roundState.zones.map((zone, index) => ({
			...zone,
			revealed: index < revealedAnswerCount,
		}));

		if (alivePlayerCount() === 0) {
			startHostDecisionPrompt('replay');
			return;
		}

		if (timeLeftMs <= 0) {
			eliminatePlayersOutsideCorrectZone();
			spawnObstacleAtRoundEnd(roundState.round);
			if (gameId && currentRoundId) {
				for (const p of players.values()) {
					if (!p.dead && p.gamePlayerId) {
						void callApi('POST', `/api/games/${gameId}/${p.gamePlayerId}/score`);
					}
				}

				if (alivePlayerCount() === 0) {
					const anyPlayer = [...players.values()][0];
					void callApi('POST', `/api/rounds/${currentRoundId}/server-end`, {
						winner_id: anyPlayer?.gamePlayerId ?? null,
					});
				}
			}

			if (alivePlayerCount() === 0) {
				startHostDecisionPrompt('replay');
				return;
			}

			startBreakRound();
			return;
		}

		broadcastRoundState(false);
		return;
	}

	if (roundState.phase === 'break') {
		if (alivePlayerCount() === 0) {
			startHostDecisionPrompt('replay');
			return;
		}

		roundState.timeLeftMs = Math.max(0, phaseEndsAt - Date.now());
		if (roundState.timeLeftMs <= 0) {
			startQuestionRound();
			return;
		}

		broadcastRoundState(false);
	}
}

if (process.env.BEARCAT_GAME_DEBUG) {
	app.get('/debug', (_request, res) => {
		res.sendFile(path.join(__dirname, '..', 'public', 'debug.html'));
	});

	app.get('/debug/players', (_request, res) => {
		res.json([...players.values()]);
	});

	app.get('/debug/obstacles', (_request, res) => {
		res.json(serializeObstacles());
	});

	app.post('/debug/spawn-obstacle', (request, res) => {
		const rawKind = typeof request.body?.kind === 'string' ? request.body.kind : 'random';
		const kind = rawKind === 'cone' || rawKind === 'box' || rawKind === 'barrel' || rawKind === 'random'
			? rawKind
			: 'random';
		spawnObstacleByKind(kind);
		res.json({
			ok: true,
			kind,
			obstacles: serializeObstacles(),
		});
	});

	app.patch('/debug/players/:id', (request, res) => {
		const p = players.get(request.params.id);
		if (!p) {
			res.status(404).json({error: 'Player not found'});
			return;
		}

		const numericFields: Array<'x' | 'y' | 'z' | 'rotationY' | 'velocityY'> = ['x', 'y', 'z', 'rotationY', 'velocityY'];
		const boolFields: Array<'dead' | 'host'> = ['dead', 'host'];
		const stringFields: Array<'animation' | 'modelFile'> = ['animation', 'modelFile'];

		for (const field of numericFields) {
			if (field in request.body) {
				const n = Number(request.body[field]);
				if (!isFinite(n)) {
					res.status(400).json({error: `Invalid value for ${field}`});
					return;
				}

				p[field] = n;
			}
		}

		for (const field of boolFields) {
			if (field in request.body) {
				p[field] = Boolean(request.body[field]);
			}
		}

		for (const field of stringFields) {
			if (field in request.body) {
				p[field] = String(request.body[field]);
			}
		}

		io.emit('playerMoved', p);

		res.json(p);
	});

	app.post('/debug/restart', (_request, res) => {
		for (const player of players.values()) {
			player.x = (Math.random() * 2 - 1) * spawnRange;
			player.y = 0;
			player.z = (Math.random() * 2 - 1) * spawnRange;
			player.rotationY = 0;
			player.velocityY = 0;
			player.animation = 'idle';
			player.dead = false;
			io.emit('playerMoved', player);
		}

		startQuestionRound();
		res.json({ok: true, players: [...players.values()], roundState});
	});

	app.get('/debug/round', (_request, res) => {
		res.json(roundState);
	});

	console.log('Debug page enabled at /debug');
}

async function callApi(method: string, path: string, body?: unknown): Promise<Response> {
	return fetch(`${apiUrl}${path}`, {
		method,
		headers: {'Content-Type': 'application/json'},
		body: body === undefined ? undefined : JSON.stringify(body),
	});
}

io.on('connection', socket => {
	console.log(`Player connected: ${socket.id}`);
	const isFirstPlayer = players.size === 0;
	const rawGamePlayerId = socket.handshake.auth?.gamePlayerId;
	const newPlayer: PlayerState = {
		id: socket.id,
		x: (Math.random() * 2 - 1) * spawnRange,
		y: 0,
		z: (Math.random() * 2 - 1) * spawnRange,
		rotationY: 0,
		velocityY: 0,
		animation: 'idle',
		modelFile: pickModel(),
		dead: false,
		host: isFirstPlayer,
		gamePlayerId: typeof rawGamePlayerId === 'string' ? rawGamePlayerId : undefined,
	};
	players.set(socket.id, newPlayer);
	ensureHostAssigned();

	socket.emit('init', {
		id: socket.id,
		modelFile: newPlayer.modelFile,
		players: Object.fromEntries(players),
		roundState,
		obstacles: serializeObstacles(),
	});

	socket.broadcast.emit('playerJoined', newPlayer);
	socket.emit('roundState', roundState);
	socket.emit('obstaclesState', serializeObstacles());

	socket.on('playerUpdate', (data: Omit<PlayerState, 'id' | 'modelFile'>) => {
		if (awaitingHostDecision) {
			return;
		}

		const p = players.get(socket.id);
		if (!p || p.dead) {
			return;
		}

		p.x = data.x;
		p.y = data.y;
		p.z = data.z;
		p.rotationY = data.rotationY;
		p.velocityY = data.velocityY;
		p.animation = data.animation;
		applyObstacleCollisions(p, true);

		socket.broadcast.emit('playerMoved', p);
		socket.emit('playerMoved', p);
	});

	socket.on('attack', (data: {x: number; z: number; rotationY: number}) => {
		if (awaitingHostDecision) {
			return;
		}

		const attacker = players.get(socket.id);
		if (!attacker || attacker.dead) {
			return;
		}

		const attackRange = 1;
		const coneHalfAngle = Math.PI / 3;
		const knockbackDist = 1;
		const halfBound = platformHalfBound;
		let didHit = false;

		const forwardX = Math.sin(data.rotationY);
		const forwardZ = Math.cos(data.rotationY);

		for (const [id, target] of players) {
			if (id === socket.id || target.dead) {
				continue;
			}

			const dx = target.x - data.x;
			const dz = target.z - data.z;
			const dist = Math.hypot(dx, dz);

			if (dist <= 0 || dist >= attackRange) {
				continue;
			}

			const toTargetX = dx / dist;
			const toTargetZ = dz / dist;
			const dot = forwardX * toTargetX + forwardZ * toTargetZ;
			const angle = Math.acos(Math.min(1, Math.max(-1, dot)));

			if (angle < coneHalfAngle) {
				didHit = true;
				target.x += toTargetX * knockbackDist;
				target.z += toTargetZ * knockbackDist;
				target.x = Math.max(-halfBound, Math.min(halfBound, target.x));
				target.z = Math.max(-halfBound, Math.min(halfBound, target.z));

				io.to(id).emit('knockback', {x: target.x, z: target.z});
			}
		}

		io.emit('playerAttacked', {
			id: socket.id,
			x: data.x,
			z: data.z,
			rotationY: data.rotationY,
			hit: didHit,
		});
	});

	socket.on('hostGameDecision', async (data: {startGame: boolean}) => {
		const host = getHostPlayer();
		if (!awaitingHostDecision || !host || host.id !== socket.id) {
			return;
		}

		if (data.startGame) {
			if (gameId) {
				try {
					const createResp = await callApi('POST', `/api/rounds/${gameId}/server-create`);
					const createData = await createResp.json() as {id: string};
					currentRoundId = createData.id;
					await callApi('POST', `/api/rounds/${currentRoundId}/server-start`);
				} catch {
					// Continue even if API calls fail
				}
			}

			restartGame();
			return;
		}

		io.emit('roundState', {
			phase: 'waiting',
			round: roundState.round,
			question: 'Host ended the game. Shutting down server...',
			timeLeftMs: 0,
			revealedAnswerCount: 0,
			zones: [],
		} satisfies RoundState);

		io.emit('gameEnded');

		if (gameId) {
			void callApi('POST', `/api/games/${gameId}/server-end`);
		}

		setTimeout(() => {
			process.exit(0);
		}, 200);
	});

	socket.on('disconnect', () => {
		console.log(`Player disconnected: ${socket.id}`);
		players.delete(socket.id);
		io.emit('playerLeft', socket.id);
		ensureHostAssigned();

		if (players.size === 0) {
			awaitingHostDecision = false;
			setWaitingState('Waiting for players...');
			broadcastRoundState(true);
			return;
		}

		if (awaitingHostDecision) {
			const host = getHostPlayer();
			if (host) {
				io.to(host.id).emit('hostGamePrompt', {initialStart: hostDecisionKind === 'initial'});
			}
		}
	});
});

setInterval(tickRoundLoop, roundTickMs);

async function bootstrap() {
	try {
		triviaCards = await loadTriviaCardsFromApkg();
		console.log(`Loaded ${triviaCards.length} trivia cards from questions.apkg`);
		setWaitingState('Waiting for players...');
	} catch (error) {
		console.error('Failed to load questions.apkg:', error);
		setWaitingState('Failed to load questions.apkg');
	}

	const port: number = Number(process.env.PORT) || 3000;
	httpServer.listen(port, () => {
		console.log(`Game server listening on http://localhost:${port}`);
	});
}

void bootstrap();
