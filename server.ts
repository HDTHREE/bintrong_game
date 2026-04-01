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

function pickModel(): string {
	return modelFiles[Math.floor(Math.random() * modelFiles.length)];
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
			// Host flag intentionally unchanged.

			io.emit('playerMoved', player);
		}

		res.json({ok: true, players: [...players.values()]});
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
	});

	socket.broadcast.emit('playerJoined', newPlayer);

	socket.on('playerUpdate', (data: Omit<PlayerState, 'id' | 'modelFile'>) => {
		const p = players.get(socket.id);
		if (!p) {
			return;
		}

		if (p.dead) {
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
		const halfBound = 7.5; // (platformSize / 2) - 0.5

		const forwardX = Math.sin(data.rotationY);
		const forwardZ = Math.cos(data.rotationY);

		for (const [id, target] of players) {
			if (id === socket.id) {
				continue;
			}

			if (target.dead) {
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
