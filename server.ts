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

type PlayerState = {
	id: string;
	x: number;
	y: number;
	z: number;
	rotationY: number;
	velocityY: number;
	animation: string;
	modelFile: string;
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

function pickModel(): string {
	return modelFiles[Math.floor(Math.random() * modelFiles.length)];
}

io.on('connection', socket => {
	console.log(`Player connected: ${socket.id}`);
	const spawnRange = 6;
	const newPlayer: PlayerState = {
		id: socket.id,
		x: (Math.random() * 2 - 1) * spawnRange,
		y: 0,
		z: (Math.random() * 2 - 1) * spawnRange,
		rotationY: 0,
		velocityY: 0,
		animation: 'idle',
		modelFile: pickModel(),
	};
	players.set(socket.id, newPlayer);

	socket.emit('init', {
		id: socket.id,
		modelFile: newPlayer.modelFile,
		players: Object.fromEntries(players),
	});

	socket.broadcast.emit('playerJoined', newPlayer);

	socket.on('playerUpdate', (data: Omit<PlayerState, 'id' | 'modelFile'>) => {
		const p = players.get(socket.id);
		if (!p) {
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
		const attackRange = 1;
		const coneHalfAngle = Math.PI / 3;
		const knockbackDist = 1;
		const halfBound = 7.5; // (platformSize / 2) - 0.5

		const forwardX = Math.sin(data.rotationY);
		const forwardZ = Math.cos(data.rotationY);

		for (const [id, target] of players) {
			if (id === socket.id) {
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
				// Clamp to platform bounds
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
	});
});

const port: number = Number(process.env.PORT) || 3000;
httpServer.listen(port, () => {
	console.log(`Game server listening on http://localhost:${port}`);
});
