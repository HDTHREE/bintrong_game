import {io, type Socket} from 'socket.io-client';

export type RemotePlayerData = {
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

export type InitPayload = {
	id: string;
	modelFile: string;
	players: Record<string, RemotePlayerData>;
	roundState?: RoundState;
	obstacles?: ObstacleData[];
};

export type AttackData = {
	id: string;
	x: number;
	z: number;
	rotationY: number;
	hit: boolean;
};

export type AnswerZoneData = {
	id: number;
	x: number;
	z: number;
	radius: number;
	answer: string;
	revealed: boolean;
};

export type RoundState = {
	phase: 'waiting' | 'question' | 'break' | 'hostPrompt';
	round: number;
	question: string;
	timeLeftMs: number;
	revealedAnswerCount: number;
	zones: AnswerZoneData[];
};

export type ObstacleData = {
	id: string;
	kind: 'cone' | 'box' | 'barrel';
	modelFile: string;
	x: number;
	y: number;
	z: number;
	rotationY: number;
	radius: number;
	height: number;
	dynamic: boolean;
	velocityX: number;
	velocityZ: number;
};

export type NetworkCallbacks = {
	onInit: (payload: InitPayload) => void;
	onPlayerJoined: (player: RemotePlayerData) => void;
	onPlayerMoved: (player: RemotePlayerData) => void;
	onPlayerLeft: (id: string) => void;
	onPlayerAttacked: (data: AttackData) => void;
	onKnockback: (data: {x: number; z: number}) => void;
	onRoundState: (state: RoundState) => void;
	onHostGamePrompt: (payload: {initialStart: boolean}) => void;
	onObstaclesState: (obstacles: ObstacleData[]) => void;
	onGameEnded: () => void;
};

let socket: Socket | undefined;

export function connect(callbacks: NetworkCallbacks, gamePlayerId: string) {
	// Connect to wherever the page was served from, resolving the socket.io
	// path relative to the current page so nginx can route it to the correct
	// game server container when accessed via a sub-path proxy.
	const basePath = globalThis.location.pathname.replace(/\/$/, '');
	socket = io({path: `${basePath}/socket.io/`, auth: {gamePlayerId}});

	socket.on('init', (payload: InitPayload) => {
		callbacks.onInit(payload);
	});

	socket.on('playerJoined', (player: RemotePlayerData) => {
		callbacks.onPlayerJoined(player);
	});

	socket.on('playerMoved', (player: RemotePlayerData) => {
		callbacks.onPlayerMoved(player);
	});

	socket.on('playerLeft', (id: string) => {
		callbacks.onPlayerLeft(id);
	});

	socket.on('playerAttacked', (data: AttackData) => {
		callbacks.onPlayerAttacked(data);
	});

	socket.on('knockback', (data: {x: number; z: number}) => {
		callbacks.onKnockback(data);
	});

	socket.on('roundState', (state: RoundState) => {
		callbacks.onRoundState(state);
	});

	socket.on('hostGamePrompt', (payload: {initialStart: boolean}) => {
		callbacks.onHostGamePrompt(payload);
	});

	socket.on('obstaclesState', (obstacles: ObstacleData[]) => {
		callbacks.onObstaclesState(obstacles);
	});

	socket.on('gameEnded', () => {
		callbacks.onGameEnded();
	});
}

export function sendUpdate(data: {
	x: number;
	y: number;
	z: number;
	rotationY: number;
	velocityY: number;
	animation: string;
}) {
	socket?.emit('playerUpdate', data);
}

export function sendAttack(data: {x: number; z: number; rotationY: number}) {
	socket?.emit('attack', data);
}

export function sendHostGameDecision(startGame: boolean) {
	socket?.emit('hostGameDecision', {startGame});
}
