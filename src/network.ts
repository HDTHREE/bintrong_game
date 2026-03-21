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
};

export type InitPayload = {
	id: string;
	modelFile: string;
	players: Record<string, RemotePlayerData>;
};

export type AttackData = {
	id: string;
	x: number;
	z: number;
	rotationY: number;
};

export type NetworkCallbacks = {
	onInit: (payload: InitPayload) => void;
	onPlayerJoined: (player: RemotePlayerData) => void;
	onPlayerMoved: (player: RemotePlayerData) => void;
	onPlayerLeft: (id: string) => void;
	onPlayerAttacked: (data: AttackData) => void;
	onKnockback: (data: {x: number; z: number}) => void;
};

let socket: Socket | undefined;

export function connect(callbacks: NetworkCallbacks) {
	// Connect to wherever the page was served from
	socket = io();

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
