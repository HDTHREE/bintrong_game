#!/usr/bin/env node
/* eslint unicorn/no-process-exit: "off" */
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import process from 'node:process';

const root = process.cwd();
const toUnixPath = relativePath => path.resolve(root, relativePath).replaceAll('\\', '/');

const questionsPath = toUnixPath('questions.apkg');
const srcPath = toUnixPath('src');
const publicPath = toUnixPath('public');
const serverPath = toUnixPath('server.ts');
const webpackConfigPath = toUnixPath('webpack.config.js');
const tsconfigPath = toUnixPath('tsconfig.json');
const tsconfigServerPath = toUnixPath('tsconfig.server.json');

const buildResult = spawnSync(
	'docker',
	['build', '--file', 'game.Dockerfile', '--target', 'development', '-t', 'livetrivia-game-dev:latest', '.'],
	{stdio: 'inherit'},
);

if (buildResult.error) {
	console.error(buildResult.error.message);
	process.exit(1);
}

if ((buildResult.status ?? 1) !== 0) {
	process.exit(buildResult.status ?? 1);
}

spawnSync('docker', ['rm', '-f', 'livetrivia-game-dev'], {stdio: 'inherit'});

const args = [
	'run',
	'--rm',
	'--name',
	'livetrivia-game-dev',
	'-p',
	'3000:3000',
	'-p',
	'8080:8080',
	'-v',
	`${questionsPath}:/app/questions.apkg:ro`,
	'-v',
	`${srcPath}:/app/src`,
	'-v',
	`${publicPath}:/app/public`,
	'-v',
	`${serverPath}:/app/server.ts`,
	'-v',
	`${webpackConfigPath}:/app/webpack.config.js`,
	'-v',
	`${tsconfigPath}:/app/tsconfig.json`,
	'-v',
	`${tsconfigServerPath}:/app/tsconfig.server.json`,
	'livetrivia-game-dev:latest',
	'sh',
	'-c',
	'npx concurrently "webpack serve --host 0.0.0.0 --port 8080 --hot" "npx tsc -p tsconfig.server.json --watch" "sh -c \'until [ -f dist-server/server.js ]; do sleep 1; done; node --watch dist-server/server.js\'"',
];

const result = spawnSync('docker', args, {stdio: 'inherit'});

if (result.error) {
	console.error(result.error.message);
	process.exit(1);
}

process.exit(result.status ?? 0);
