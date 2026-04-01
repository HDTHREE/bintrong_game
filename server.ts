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
	phase: 'waiting' | 'question' | 'break';
	round: number;
	question: string;
	timeLeftMs: number;
	revealedAnswerCount: number;
	zones: AnswerZone[];
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

let triviaCards: TriviaCard[] = [];
let triviaCursor = 0;
let currentCorrectAnswer = '';
let phaseEndsAt = 0;
let lastStateBroadcastAt = 0;

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

	for (let index = 0; index < answers.length; index++) {
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
				answer: answers[index],
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
			answer: answers[index],
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

function restartGame() {
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
	if (players.size === 0) {
		if (roundState.phase !== 'waiting') {
			setWaitingState('Waiting for players...');
			broadcastRoundState(true);
		}

		return;
	}

	if (roundState.phase === 'waiting') {
		startQuestionRound();
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
			restartGame();
			return;
		}

		if (timeLeftMs <= 0) {
			eliminatePlayersOutsideCorrectZone();
			if (alivePlayerCount() === 0) {
				restartGame();
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
			restartGame();
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

io.on('connection', socket => {
	console.log(`Player connected: ${socket.id}`);
	const isFirstPlayer = players.size === 0;
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
	};
	players.set(socket.id, newPlayer);

	socket.emit('init', {
		id: socket.id,
		modelFile: newPlayer.modelFile,
		players: Object.fromEntries(players),
		roundState,
	});

	socket.broadcast.emit('playerJoined', newPlayer);
	socket.emit('roundState', roundState);

	socket.on('playerUpdate', (data: Omit<PlayerState, 'id' | 'modelFile'>) => {
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

		socket.broadcast.emit('playerMoved', {
			id: socket.id,
			...data,
		});
	});

	socket.on('attack', (data: {x: number; z: number; rotationY: number}) => {
		const attacker = players.get(socket.id);
		if (!attacker || attacker.dead) {
			return;
		}

		const attackRange = 1;
		const coneHalfAngle = Math.PI / 3;
		const knockbackDist = 1;
		const halfBound = platformHalfBound;

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
				target.x += toTargetX * knockbackDist;
				target.z += toTargetZ * knockbackDist;
				target.x = Math.max(-halfBound, Math.min(halfBound, target.x));
				target.z = Math.max(-halfBound, Math.min(halfBound, target.z));

				io.to(id).emit('knockback', {x: target.x, z: target.z});
			}
		}

		socket.broadcast.emit('playerAttacked', {
			id: socket.id,
			x: data.x,
			z: data.z,
			rotationY: data.rotationY,
		});
	});

	socket.on('disconnect', () => {
		console.log(`Player disconnected: ${socket.id}`);
		players.delete(socket.id);
		io.emit('playerLeft', socket.id);

		if (players.size === 0) {
			setWaitingState('Waiting for players...');
			broadcastRoundState(true);
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
