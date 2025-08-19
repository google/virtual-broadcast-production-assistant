import { readFileSync } from 'fs'
import { join } from 'path'

export const version: string = JSON.parse(readFileSync(join(import.meta.dirname, '../', '../', 'package.json'), 'utf8')).version
