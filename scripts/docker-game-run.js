#!/usr/bin/env node
/* eslint unicorn/no-process-exit: "off" */
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import process from 'node:process';

const questionsPath = path.resolve('questions.apkg').replaceAll('\\', '/');

spawnSync('docker', ['rm', '-f', 'livetrivia-game'], {stdio: 'inherit'});

const args = [
	'run',
	'--rm',
	'--name',
	'livetrivia-game',
	'-p',
	'3000:3000',
	'-v',
	`${questionsPath}:/app/questions.apkg:ro`,
	'livetrivia-game:latest',
];

const result = spawnSync('docker', args, {stdio: 'inherit'});

if (result.error) {
	console.error(result.error.message);
	process.exit(1);
}

process.exit(result.status ?? 0);
